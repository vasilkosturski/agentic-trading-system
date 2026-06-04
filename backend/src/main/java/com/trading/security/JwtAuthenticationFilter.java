package com.trading.security;

import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * JWT authentication filter for validating JWT tokens on each request.
 * Extends OncePerRequestFilter to guarantee single execution per request.
 *
 * <p>Filter logic:
 * <ol>
 *   <li>Extract JWT token from Authorization header (Bearer scheme)</li>
 *   <li>Extract username from token</li>
 *   <li>Load user details from UserDetailsService</li>
 *   <li>Validate token against user details</li>
 *   <li>Set authentication in SecurityContext if valid (and not already set)</li>
 * </ol>
 *
 * <p>If no token, expired token, or otherwise invalid token, the filter passes through
 * without setting authentication. Spring Security and method-level authorization will
 * then decide whether to allow or deny the request. This deliberately makes
 * expired/malformed/missing tokens behave identically for downstream authorization.
 *
 * <p>Exception handling policy:
 * <ul>
 *   <li>{@link ExpiredJwtException} - logged at DEBUG (expected client state, e.g.
 *       stale browser session), chain continues anonymous.</li>
 *   <li>{@link JwtException} / {@link IllegalArgumentException} - malformed, bad
 *       signature, unsupported algorithm, or null/empty token - logged at WARN,
 *       chain continues anonymous.</li>
 *   <li>{@link UsernameNotFoundException} - subject in token does not match a known
 *       user - logged at WARN, chain continues anonymous.</li>
 *   <li>Any other unexpected exception (e.g., DB outage in UserDetailsService) is
 *       deliberately NOT caught - it propagates so the global handler returns 500.</li>
 * </ul>
 */
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtTokenProvider jwtTokenProvider;
    private final UserDetailsService userDetailsService;

    public JwtAuthenticationFilter(JwtTokenProvider jwtTokenProvider, UserDetailsService userDetailsService) {
        this.jwtTokenProvider = jwtTokenProvider;
        this.userDetailsService = userDetailsService;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {

        String jwt = extractJwtFromRequest(request);

        if (jwt != null && SecurityContextHolder.getContext().getAuthentication() == null) {
            try {
                String username = jwtTokenProvider.getUsernameFromToken(jwt);

                if (username != null) {
                    UserDetails userDetails = userDetailsService.loadUserByUsername(username);

                    if (jwtTokenProvider.validateToken(jwt, userDetails)) {
                        UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(
                                userDetails, null, userDetails.getAuthorities());
                        authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                        SecurityContextHolder.getContext().setAuthentication(authentication);
                    }
                }
            } catch (ExpiredJwtException e) {
                // Expected client state (e.g., stale browser session). Treat as anonymous.
                logger.debug("JWT expired; treating request as anonymous: " + e.getMessage());
            } catch (JwtException | IllegalArgumentException e) {
                // Malformed / invalid signature / unsupported algorithm / null-empty.
                // Treat as anonymous; surface at WARN since this could indicate tampering or misconfiguration.
                logger.warn("JWT invalid; treating request as anonymous: " + e.getMessage());
            } catch (UsernameNotFoundException e) {
                // Token subject doesn't match a known user. Treat as anonymous.
                logger.warn("JWT subject not found; treating request as anonymous: " + e.getMessage());
            }
            // NOTE: deliberately NOT catching generic Exception. If something truly
            // unexpected happens (e.g., DB outage in UserDetailsService), let it
            // propagate so GlobalExceptionHandler returns 500 instead of silently
            // downgrading the request to anonymous.
        }

        filterChain.doFilter(request, response);
    }

    /**
     * Extract JWT token from Authorization header.
     * Expected format: "Bearer {token}"
     *
     * @param request HTTP request
     * @return JWT token or null if not present or invalid format
     */
    private String extractJwtFromRequest(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }
}
