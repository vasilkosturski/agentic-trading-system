package com.trading.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.trading.config.SecurityConfig;
import com.trading.security.JwtAuthenticationFilter;
import com.trading.security.JwtTokenProvider;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Security tests for the state-heartbeat endpoint on {@link AgentStatusController}:
 * {@code POST /api/agents/status}. Mirrors the pattern in
 * {@link TradingRunControllerAdminSecurityTest}.
 */
@WebMvcTest(AgentStatusController.class)
@Import({SecurityConfig.class, AgentStatusControllerSecurityTest.JwtFilterTestConfig.class})
@DisplayName("AgentStatusController Security Tests")
class AgentStatusControllerSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private JwtTokenProvider jwtTokenProvider;

    @TestConfiguration
    static class JwtFilterTestConfig {
        @Bean("agentStatusControllerSecurityJwtAuthenticationFilter")
        JwtAuthenticationFilter jwtAuthenticationFilter(
                JwtTokenProvider jwtTokenProvider, UserDetailsService userDetailsService) {
            return new JwtAuthenticationFilter(jwtTokenProvider, userDetailsService);
        }
    }

    private String statusJson() {
        return "{\"agentName\":\"Warren\",\"phase\":\"RESEARCHING\",\"message\":\"running\",\"progress\":50}";
    }

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("ADMIN: POST /api/agents/status returns 204")
    void updateStatus_WithAdminRole_Returns204() throws Exception {
        mockMvc.perform(post("/api/agents/status")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(statusJson()))
                .andExpect(status().isNoContent());
    }

    @Test
    @WithMockUser(roles = "USER")
    @DisplayName("USER: POST /api/agents/status returns 403")
    void updateStatus_WithUserRole_Returns403() throws Exception {
        mockMvc.perform(post("/api/agents/status")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(statusJson()))
                .andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("Anonymous: POST /api/agents/status is denied")
    void updateStatus_Unauthenticated_IsDenied() throws Exception {
        mockMvc.perform(post("/api/agents/status")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(statusJson()))
                .andExpect(result -> {
                    int status = result.getResponse().getStatus();
                    if (status != 401 && status != 403) {
                        throw new AssertionError("Expected 401 or 403 for anonymous, got " + status);
                    }
                });
    }
}
