package com.trading.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Emits one structured access-log line per {@code /api/**} request after the
 * chain completes, carrying the request path, method, and response status.
 *
 * <p>The three fields are placed on the MDC before logging. With Spring Boot's
 * ECS structured logging ({@code logging.structured.format.console: ecs}), MDC
 * entries are promoted to top-level JSON properties, so the log line carries a
 * stable {@code req_path} key the log-shipping pipeline reads directly into a
 * label (no message-text regex). Path + method + status only — no body, no
 * headers, no PII.
 *
 * <p>Scoped to {@code /api/**}; actuator/health/probe traffic is skipped so the
 * per-endpoint traffic view is not drowned by liveness polling. Runs early
 * (before security) so the line is emitted even for rejected requests, and MDC
 * is always cleared in a finally block to avoid leaking onto pooled threads.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class RequestLoggingFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(RequestLoggingFilter.class);

    private static final String MDC_PATH = "req_path";
    private static final String MDC_METHOD = "req_method";
    private static final String MDC_STATUS = "req_status";

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        // Only log application API traffic; skip actuator/health/probe noise.
        return !request.getRequestURI().startsWith("/api/");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        try {
            chain.doFilter(request, response);
        } finally {
            MDC.put(MDC_PATH, request.getRequestURI());
            MDC.put(MDC_METHOD, request.getMethod());
            MDC.put(MDC_STATUS, Integer.toString(response.getStatus()));
            try {
                log.info("api_request");
            } finally {
                MDC.remove(MDC_PATH);
                MDC.remove(MDC_METHOD);
                MDC.remove(MDC_STATUS);
            }
        }
    }
}
