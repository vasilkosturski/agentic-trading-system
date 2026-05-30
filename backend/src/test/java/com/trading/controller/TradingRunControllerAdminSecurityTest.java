package com.trading.controller;

import com.trading.config.SecurityConfig;
import com.trading.config.TradingPublicProperties;
import com.trading.dto.response.RunListResponseDto;
import com.trading.security.JwtAuthenticationFilter;
import com.trading.security.JwtTokenProvider;
import com.trading.service.TradingRunService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Collections;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Security tests for the admin endpoint in TradingRunController.
 * Tests @PreAuthorize("hasRole('ADMIN')") enforcement.
 * Security filters are ENABLED (no @AutoConfigureMockMvc(addFilters = false)).
 *
 * <p>Encodes the admin-only contract for /api/runs/admin per
 * tasks/jwt-auth-fixes/notes/research/02-admin-endpoint-policy.md (E1 legal vulnerability):
 * <ul>
 *   <li>ADMIN role -> 200 OK with showAll=true (no 7-day filter)</li>
 *   <li>USER role -> 403 Forbidden</li>
 *   <li>Unauthenticated / expired token -> 401 or 403 (NOT 200)</li>
 * </ul>
 *
 * <p>This test cannot use the shared TestSecurityConfig because that config
 * mocks JwtAuthenticationFilter via @MockBean — and a Mockito mock of a Filter
 * does NOT propagate the chain (it returns void without calling chain.doFilter),
 * which short-circuits MockMvc and produces phantom 200s with Handler=null.
 * Instead we provide a real JwtAuthenticationFilter wired to mocked dependencies,
 * so the chain propagates and @WithMockUser-supplied SecurityContext drives
 * @PreAuthorize evaluation.
 */
@WebMvcTest(TradingRunController.class)
@Import({SecurityConfig.class, TradingRunControllerAdminSecurityTest.JwtFilterTestConfig.class})
@DisplayName("TradingRunController Admin Security Tests")
class TradingRunControllerAdminSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private TradingRunService tradingRunService;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    @MockBean
    private TradingPublicProperties tradingPublicProperties;

    /**
     * Provides a real JwtAuthenticationFilter bean wired to mocked collaborators.
     * Required because the filter must call chain.doFilter() to let requests
     * reach the controller — a Mockito mock of the filter would not do that.
     */
    @TestConfiguration
    static class JwtFilterTestConfig {
        @Bean
        JwtAuthenticationFilter jwtAuthenticationFilter(
                JwtTokenProvider jwtTokenProvider,
                UserDetailsService userDetailsService) {
            return new JwtAuthenticationFilter(jwtTokenProvider, userDetailsService);
        }
    }

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("Admin user can access /api/runs/admin and receives 200 OK")
    void listAllRuns_WithAdminRole_Returns200() throws Exception {
        RunListResponseDto response = new RunListResponseDto(
            Collections.emptyList(),
            0L,
            0,
            20
        );
        when(tradingRunService.listRuns(isNull(), isNull(), any())).thenReturn(response);

        mockMvc.perform(get("/api/runs/admin"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.runs").isArray())
            .andExpect(jsonPath("$.total").value(0));

        // Verify service called with null cutoffDate (admin bypasses display delay)
        verify(tradingRunService).listRuns(isNull(), isNull(), any());
    }

    @Test
    @WithMockUser(roles = "USER")
    @DisplayName("Non-admin user gets 403 Forbidden")
    void listAllRuns_WithoutAdminRole_Returns403() throws Exception {
        mockMvc.perform(get("/api/runs/admin"))
            .andExpect(status().isForbidden());

        // Service should never be called - authorization fails first
        verify(tradingRunService, never()).listRuns(any(), any(), any());
    }

    @Test
    @DisplayName("Unauthenticated request is denied (401 or 403, NOT 200)")
    void listAllRuns_Unauthenticated_IsDenied() throws Exception {
        // Spring's default for anonymous against @PreAuthorize is 403 Forbidden
        // (AccessDeniedException -> ExceptionTranslationFilter -> 403).
        // The contract is that the request MUST be denied — accept either 401 or 403.
        mockMvc.perform(get("/api/runs/admin"))
            .andExpect(result -> {
                int status = result.getResponse().getStatus();
                if (status != 401 && status != 403) {
                    throw new AssertionError(
                        "Expected 401 or 403 for unauthenticated request, got " + status);
                }
            });

        // Service should never be called - authorization fails first
        verify(tradingRunService, never()).listRuns(any(), any(), any());
    }

    @Test
    @DisplayName("Expired token is denied (401 or 403, NOT 200)")
    void listAllRuns_ExpiredToken_IsDenied() throws Exception {
        // Simulate the production behavior of an expired JWT: JwtAuthenticationFilter
        // catches the exception broadly and lets the request through with no
        // authentication set, so the request reaches @PreAuthorize as anonymous.
        when(jwtTokenProvider.getUsernameFromToken(anyString()))
            .thenThrow(new io.jsonwebtoken.ExpiredJwtException(null, null, "expired"));

        mockMvc.perform(get("/api/runs/admin")
                .header("Authorization", "Bearer expired.jwt.token"))
            .andExpect(result -> {
                int status = result.getResponse().getStatus();
                if (status != 401 && status != 403) {
                    throw new AssertionError(
                        "Expected 401 or 403 for expired token, got " + status);
                }
            });

        // Service should never be called - authorization fails first
        verify(tradingRunService, never()).listRuns(any(), any(), any());
    }

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("Admin endpoint always passes null cutoffDate to service (no display delay)")
    void listAllRuns_AlwaysPassesNullCutoff() throws Exception {
        RunListResponseDto response = new RunListResponseDto(
            Collections.emptyList(),
            0L,
            0,
            20
        );
        when(tradingRunService.listRuns(isNull(), isNull(), any())).thenReturn(response);

        mockMvc.perform(get("/api/runs/admin"))
            .andExpect(status().isOk());

        // Verify null cutoffDate is always passed (no public display delay for admin)
        verify(tradingRunService).listRuns(isNull(), isNull(), any());
    }

    /**
     * Helper to build a UserDetails fixture for any role-based test extensions.
     */
    @SuppressWarnings("unused")
    private static UserDetails adminUser() {
        return User.builder().username("admin").password("x").roles("ADMIN").build();
    }
}
