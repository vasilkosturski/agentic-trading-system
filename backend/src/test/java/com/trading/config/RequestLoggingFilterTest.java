package com.trading.config;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.verify;

import jakarta.servlet.FilterChain;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.MDC;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

/**
 * Unit tests for {@link RequestLoggingFilter}.
 *
 * <p>Contract: log one access line for {@code /api/**} requests (carrying path,
 * method, status via MDC → ECS top-level fields), skip actuator/health/probe
 * traffic, and never leak MDC onto the calling thread.
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("RequestLoggingFilter Tests")
class RequestLoggingFilterTest {

    private final RequestLoggingFilter filter = new RequestLoggingFilter();

    @Mock
    private FilterChain chain;

    @Test
    @DisplayName("filters /api/* requests")
    void filtersApiPaths() {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/runs");
        assertFalse(filter.shouldNotFilter(request), "/api/* must be logged");
    }

    @Test
    @DisplayName("skips /actuator and non-api paths")
    void skipsActuatorAndNonApi() {
        assertTrue(
                filter.shouldNotFilter(new MockHttpServletRequest("GET", "/actuator/health")),
                "actuator must be skipped");
        assertTrue(filter.shouldNotFilter(new MockHttpServletRequest("GET", "/")), "root/probe must be skipped");
    }

    @Test
    @DisplayName("continues the chain and clears MDC after logging")
    void continuesChainAndClearsMdc() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/runs/1/complete");
        MockHttpServletResponse response = new MockHttpServletResponse();
        response.setStatus(200);

        filter.doFilterInternal(request, response, chain);

        verify(chain).doFilter(request, response);
        // MDC must not leak onto the (pooled) request thread after the filter returns.
        assertNull(MDC.get("req_path"));
        assertNull(MDC.get("req_method"));
        assertNull(MDC.get("req_status"));
    }
}
