package com.trading.config;

import io.github.bucket4j.Bandwidth;
import io.github.bucket4j.Bucket;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Per-IP rate limit filter sitting in front of the Spring Security chain.
 *
 * <p>Two endpoints are throttled:
 * <ul>
 *   <li>{@code POST /api/auth/login} → 5/min/IP (brute-force window)</li>
 *   <li>{@code GET /api/runs} → 60/min/IP (heaviest public DB query)</li>
 * </ul>
 *
 * <p>Defense-in-depth alongside the Traefik {@code ratelimit-global} ingress
 * middleware (30 req/s burst 60). The Traefik limit is a blanket DoS guard; these
 * per-endpoint limits target the two abusable paths with stricter, semantics-aware
 * bounds.
 *
 * <p>State: an in-process {@link ConcurrentHashMap} of bucket4j buckets keyed by
 * resolved client IP. Single-pod single-replica deployment makes this sufficient;
 * scaling beyond one backend replica requires moving bucket state to a shared
 * cache (Redis/Hazelcast) so limits are cluster-wide.
 *
 * <p>Client IP resolution: {@code X-Forwarded-For} first hop (Traefik forwards the
 * real client IP); fallback to {@link HttpServletRequest#getRemoteAddr()} for
 * direct connections in dev / tests.
 */
@Component
public class RateLimitFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(RateLimitFilter.class);

    private static final String LOGIN_PATH = "/api/auth/login";
    private static final String RUNS_LIST_PATH = "/api/runs";

    private final Bandwidth loginBandwidth;
    private final Bandwidth runsListBandwidth;
    private final Map<String, Bucket> loginBuckets = new ConcurrentHashMap<>();
    private final Map<String, Bucket> runsListBuckets = new ConcurrentHashMap<>();

    public RateLimitFilter(
            @Value("${ratelimit.login.capacity:5}") long loginCapacity,
            @Value("${ratelimit.login.refill-period-minutes:1}") long loginRefillMinutes,
            @Value("${ratelimit.runs-list.capacity:60}") long runsListCapacity,
            @Value("${ratelimit.runs-list.refill-period-minutes:1}") long runsListRefillMinutes) {
        this.loginBandwidth = Bandwidth.builder()
                .capacity(loginCapacity)
                .refillIntervally(loginCapacity, Duration.ofMinutes(loginRefillMinutes))
                .build();
        this.runsListBandwidth = Bandwidth.builder()
                .capacity(runsListCapacity)
                .refillIntervally(runsListCapacity, Duration.ofMinutes(runsListRefillMinutes))
                .build();
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        // CORS preflight (OPTIONS) does not count toward the per-IP limit — otherwise
        // a browser's preflight burst starves the real POST request.
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            chain.doFilter(request, response);
            return;
        }
        Bucket bucket = bucketFor(request);
        if (bucket == null) {
            chain.doFilter(request, response);
            return;
        }
        if (bucket.tryConsume(1)) {
            chain.doFilter(request, response);
            return;
        }
        // 429 with a short JSON body. Clients see the throttle without needing to
        // parse a Spring error page.
        log.warn("rate_limit_exceeded path={} ip={}", request.getRequestURI(), clientIp(request));
        response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write(bodyFor(request.getRequestURI()));
    }

    private Bucket bucketFor(HttpServletRequest request) {
        String path = request.getRequestURI();
        String ip = clientIp(request);
        if (LOGIN_PATH.equals(path)) {
            return loginBuckets.computeIfAbsent(
                    ip, k -> Bucket.builder().addLimit(loginBandwidth).build());
        }
        // /api/runs (exact list endpoint, not /api/runs/{id}).
        if (RUNS_LIST_PATH.equals(path)) {
            return runsListBuckets.computeIfAbsent(
                    ip, k -> Bucket.builder().addLimit(runsListBandwidth).build());
        }
        return null;
    }

    private static String clientIp(HttpServletRequest request) {
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            int comma = xff.indexOf(',');
            return (comma > 0 ? xff.substring(0, comma) : xff).trim();
        }
        return request.getRemoteAddr();
    }

    private static String bodyFor(String path) {
        return LOGIN_PATH.equals(path)
                ? "{\"error\":\"Too many login attempts. Try again later.\"}"
                : "{\"error\":\"Rate limit exceeded. Slow down.\"}";
    }

    /**
     * Test seam: clear buckets between integration tests so each test starts from a
     * fresh limit. Not invoked at runtime.
     */
    void resetForTest() {
        loginBuckets.clear();
        runsListBuckets.clear();
    }
}
