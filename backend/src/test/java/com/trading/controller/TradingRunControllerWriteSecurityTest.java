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
import com.trading.dto.request.PhaseFailureRequest;
import com.trading.dto.request.UpdatePhaseRequest;
import com.trading.dto.response.TradingRunDto;
import com.trading.enums.RunPhase;
import com.trading.enums.RunStatus;
import com.trading.security.JwtAuthenticationFilter;
import com.trading.security.JwtTokenProvider;
import com.trading.service.TradingRunService;
import java.time.Instant;
import java.util.stream.Stream;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
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
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;

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

    private enum Endpoint {
        CREATE_RUN,
        UPDATE_PHASE,
        COMPLETE_RUN,
        PHASE_FAILURE
    }

    private MockHttpServletRequestBuilder buildRequest(Endpoint endpoint) throws Exception {
        return switch (endpoint) {
            case CREATE_RUN -> post("/api/runs")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(createRunRequest()));
            case UPDATE_PHASE -> patch("/api/runs/1/phase")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(updatePhaseRequest()));
            case COMPLETE_RUN -> put("/api/runs/1/complete")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(completeRunJson());
            case PHASE_FAILURE -> post("/api/runs/1/phase-failure")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(phaseFailureRequest()));
        };
    }

    private void verifyServiceNotCalled(Endpoint endpoint) {
        switch (endpoint) {
            case CREATE_RUN -> verify(tradingRunService, never()).createRun(any());
            case UPDATE_PHASE -> verify(tradingRunService, never()).updatePhase(anyLong(), any(), any());
            case COMPLETE_RUN -> verify(tradingRunService, never()).completeRun(anyLong(), any());
            case PHASE_FAILURE -> verify(tradingRunService, never()).recordPhaseFailure(anyLong(), any());
            default -> throw new IllegalArgumentException("Unexpected endpoint: " + endpoint);
        }
    }

    private static Stream<Arguments> writeEndpoints() {
        // createRun returns 201, the other three return 200.
        return Stream.of(
                Arguments.of(Endpoint.CREATE_RUN, 201),
                Arguments.of(Endpoint.UPDATE_PHASE, 200),
                Arguments.of(Endpoint.COMPLETE_RUN, 200),
                Arguments.of(Endpoint.PHASE_FAILURE, 200));
    }

    @ParameterizedTest(name = "ADMIN: {0} → {1}")
    @MethodSource("writeEndpoints")
    @WithMockUser(roles = "ADMIN")
    @DisplayName("ADMIN role passes @PreAuthorize on all write endpoints")
    void writeEndpoint_WithAdminRole_Succeeds(Endpoint endpoint, int expectedStatus) throws Exception {
        when(tradingRunService.createRun(anyLong())).thenReturn(runDto());
        mockMvc.perform(buildRequest(endpoint)).andExpect(status().is(expectedStatus));
    }

    @ParameterizedTest(name = "USER: {0} → 403")
    @MethodSource("writeEndpoints")
    @WithMockUser(roles = "USER")
    @DisplayName("USER role is rejected by @PreAuthorize on all write endpoints")
    void writeEndpoint_WithUserRole_Returns403(Endpoint endpoint, int ignored) throws Exception {
        mockMvc.perform(buildRequest(endpoint)).andExpect(status().isForbidden());
        verifyServiceNotCalled(endpoint);
    }

    // Each anonymous test kept standalone (no @WithMockUser context) — the
    // entry-point/access-denied handler choice can differ per endpoint, so each
    // assertion lives separately for clean failure attribution.

    @Test
    @DisplayName("Anonymous: POST /api/runs is denied and service not called")
    void createRun_Unauthenticated_IsDenied() throws Exception {
        mockMvc.perform(buildRequest(Endpoint.CREATE_RUN)).andExpect(result -> {
            int status = result.getResponse().getStatus();
            if (status != 401 && status != 403) {
                throw new AssertionError("Expected 401 or 403 for anonymous, got " + status);
            }
        });
        verifyServiceNotCalled(Endpoint.CREATE_RUN);
    }

    @Test
    @DisplayName("Anonymous: PATCH /api/runs/{id}/phase is denied")
    void updatePhase_Unauthenticated_IsDenied() throws Exception {
        mockMvc.perform(buildRequest(Endpoint.UPDATE_PHASE)).andExpect(result -> {
            int status = result.getResponse().getStatus();
            if (status != 401 && status != 403) {
                throw new AssertionError("Expected 401 or 403 for anonymous, got " + status);
            }
        });
        verifyServiceNotCalled(Endpoint.UPDATE_PHASE);
    }

    @Test
    @DisplayName("Anonymous: PUT /api/runs/{id}/complete is denied")
    void completeRun_Unauthenticated_IsDenied() throws Exception {
        mockMvc.perform(buildRequest(Endpoint.COMPLETE_RUN)).andExpect(result -> {
            int status = result.getResponse().getStatus();
            if (status != 401 && status != 403) {
                throw new AssertionError("Expected 401 or 403 for anonymous, got " + status);
            }
        });
        verifyServiceNotCalled(Endpoint.COMPLETE_RUN);
    }

    @Test
    @DisplayName("Anonymous: POST /api/runs/{id}/phase-failure is denied")
    void recordPhaseFailure_Unauthenticated_IsDenied() throws Exception {
        mockMvc.perform(buildRequest(Endpoint.PHASE_FAILURE)).andExpect(result -> {
            int status = result.getResponse().getStatus();
            if (status != 401 && status != 403) {
                throw new AssertionError("Expected 401 or 403 for anonymous, got " + status);
            }
        });
        verifyServiceNotCalled(Endpoint.PHASE_FAILURE);
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

    private PhaseFailureRequest phaseFailureRequest() {
        PhaseFailureRequest req = new PhaseFailureRequest();
        req.setPhaseKind(PhaseFailureRequest.PhaseKind.RESEARCH);
        req.setGuardrailAttempts(3);
        req.setGuardrailOutcome(com.trading.enums.GuardrailOutcomeKind.EXHAUSTED);
        return req;
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
}
