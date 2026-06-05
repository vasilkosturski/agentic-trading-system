package com.trading.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.trading.config.SecurityConfig;
import com.trading.config.TradingPublicProperties;
import com.trading.dto.request.CreateRunRequest;
import com.trading.dto.request.UpdatePhaseRequest;
import com.trading.dto.response.TradingRunDto;
import com.trading.enums.RunPhase;
import com.trading.enums.RunStatus;
import com.trading.security.JwtAuthenticationFilter;
import com.trading.security.JwtTokenProvider;
import com.trading.service.TradingRunService;
import java.time.Instant;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Security tests for state-changing endpoints on TradingRunController:
 * createRun (POST), updatePhase (PATCH), completeRun (PUT).
 *
 * <p>Mirrors the pattern in {@link TradingRunControllerAdminSecurityTest} —
 * real {@link SecurityConfig} import plus a real {@link JwtAuthenticationFilter}
 * wired to mocked collaborators so the filter chain propagates and method-level
 * {@code @PreAuthorize} can drive the authorization decision against the
 * {@code @WithMockUser} security context.
 */
@WebMvcTest(TradingRunController.class)
@Import({SecurityConfig.class, TradingRunControllerWriteSecurityTest.JwtFilterTestConfig.class})
@DisplayName("TradingRunController Write Security Tests")
class TradingRunControllerWriteSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private TradingRunService tradingRunService;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    @MockBean
    private TradingPublicProperties tradingPublicProperties;

    @TestConfiguration
    static class JwtFilterTestConfig {
        @Bean("tradingRunWriteSecurityJwtAuthenticationFilter")
        JwtAuthenticationFilter jwtAuthenticationFilter(
                JwtTokenProvider jwtTokenProvider, UserDetailsService userDetailsService) {
            return new JwtAuthenticationFilter(jwtTokenProvider, userDetailsService);
        }
    }

    private CreateRunRequest createRunRequest() {
        CreateRunRequest req = new CreateRunRequest();
        req.setAgentId(1L);
        return req;
    }

    private UpdatePhaseRequest updatePhaseRequest() {
        UpdatePhaseRequest req = new UpdatePhaseRequest();
        req.setPhase(RunPhase.RESEARCHING);
        return req;
    }

    private String completeRunJson() {
        return "{\"decision\":{\"decision\":\"HOLD\"}}";
    }

    private TradingRunDto runDto() {
        TradingRunDto dto = new TradingRunDto();
        dto.setRunId(1L);
        dto.setAgentId(1L);
        dto.setStatus(RunStatus.IN_PROGRESS);
        dto.setPhase(RunPhase.INITIALIZING);
        dto.setStartedAt(Instant.now());
        return dto;
    }

    // ===== createRun =====

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("ADMIN: POST /api/runs returns 201")
    void createRun_WithAdminRole_Returns201() throws Exception {
        when(tradingRunService.createRun(anyLong())).thenReturn(runDto());

        mockMvc.perform(post("/api/runs")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(createRunRequest())))
                .andExpect(status().isCreated());
    }

    @Test
    @WithMockUser(roles = "USER")
    @DisplayName("USER: POST /api/runs returns 403 and service not called")
    void createRun_WithUserRole_Returns403() throws Exception {
        mockMvc.perform(post("/api/runs")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(createRunRequest())))
                .andExpect(status().isForbidden());

        verify(tradingRunService, never()).createRun(any());
    }

    @Test
    @DisplayName("Anonymous: POST /api/runs is denied and service not called")
    void createRun_Unauthenticated_IsDenied() throws Exception {
        mockMvc.perform(post("/api/runs")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(createRunRequest())))
                .andExpect(result -> {
                    int status = result.getResponse().getStatus();
                    if (status != 401 && status != 403) {
                        throw new AssertionError("Expected 401 or 403 for anonymous, got " + status);
                    }
                });

        verify(tradingRunService, never()).createRun(any());
    }

    // ===== updatePhase =====

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("ADMIN: PATCH /api/runs/{id}/phase returns 200")
    void updatePhase_WithAdminRole_Returns200() throws Exception {
        mockMvc.perform(patch("/api/runs/1/phase")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(updatePhaseRequest())))
                .andExpect(status().isOk());
    }

    @Test
    @WithMockUser(roles = "USER")
    @DisplayName("USER: PATCH /api/runs/{id}/phase returns 403")
    void updatePhase_WithUserRole_Returns403() throws Exception {
        mockMvc.perform(patch("/api/runs/1/phase")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(updatePhaseRequest())))
                .andExpect(status().isForbidden());

        verify(tradingRunService, never()).updatePhase(anyLong(), any(), any());
    }

    @Test
    @DisplayName("Anonymous: PATCH /api/runs/{id}/phase is denied")
    void updatePhase_Unauthenticated_IsDenied() throws Exception {
        mockMvc.perform(patch("/api/runs/1/phase")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(updatePhaseRequest())))
                .andExpect(result -> {
                    int status = result.getResponse().getStatus();
                    if (status != 401 && status != 403) {
                        throw new AssertionError("Expected 401 or 403 for anonymous, got " + status);
                    }
                });

        verify(tradingRunService, never()).updatePhase(anyLong(), any(), any());
    }

    // ===== completeRun =====

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("ADMIN: PUT /api/runs/{id}/complete returns 200")
    void completeRun_WithAdminRole_Returns200() throws Exception {
        mockMvc.perform(put("/api/runs/1/complete")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(completeRunJson()))
                .andExpect(status().isOk());
    }

    @Test
    @WithMockUser(roles = "USER")
    @DisplayName("USER: PUT /api/runs/{id}/complete returns 403")
    void completeRun_WithUserRole_Returns403() throws Exception {
        mockMvc.perform(put("/api/runs/1/complete")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(completeRunJson()))
                .andExpect(status().isForbidden());

        verify(tradingRunService, never()).completeRun(anyLong(), any());
    }

    @Test
    @DisplayName("Anonymous: PUT /api/runs/{id}/complete is denied")
    void completeRun_Unauthenticated_IsDenied() throws Exception {
        mockMvc.perform(put("/api/runs/1/complete")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(completeRunJson()))
                .andExpect(result -> {
                    int status = result.getResponse().getStatus();
                    if (status != 401 && status != 403) {
                        throw new AssertionError("Expected 401 or 403 for anonymous, got " + status);
                    }
                });

        verify(tradingRunService, never()).completeRun(anyLong(), any());
    }
}
