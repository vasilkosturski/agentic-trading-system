package com.trading.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.trading.config.TestSecurityConfig;
import com.trading.config.TradingPublicProperties;
import com.trading.dto.request.PhaseFailureRequest;
import com.trading.enums.GuardrailOutcomeKind;
import com.trading.exception.ResourceNotFoundException;
import com.trading.service.TradingRunService;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Wire-level controller test for {@code POST /api/runs/{id}/phase-failure}.
 *
 * <p>The existing {@code TradingRunControllerWriteSecurityTest} only verifies
 * the auth gate. This test exercises the Jackson deserialisation contract:
 * the Python orchestrator POSTs lowercase wire values ({@code phaseKind:"RESEARCH"},
 * {@code guardrailOutcome:"exhausted"}) plus a JSONB {@code guardrailFailedOutput}
 * payload, and the controller must hand the deserialised {@link PhaseFailureRequest}
 * to {@link TradingRunService#recordPhaseFailure(Long, PhaseFailureRequest)} with
 * the right enum + map values. Validation rejection (typo'd outcome → 400) is
 * also covered here so the Python {@code Literal} constraint is mirrored on the
 * Java intake.
 */
@WebMvcTest(TradingRunController.class)
@AutoConfigureMockMvc(addFilters = false)
@Import(TestSecurityConfig.class)
@DisplayName("TradingRunController phase-failure wire-level Tests")
class TradingRunControllerPhaseFailureIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private TradingRunService tradingRunService;

    @MockitoBean
    private TradingPublicProperties tradingPublicProperties;

    @Test
    @DisplayName("Python-shaped RESEARCH body deserialises into PhaseFailureRequest and reaches service")
    void recordPhaseFailure_ResearchBody_DeserialisesAndCallsService() throws Exception {
        doNothing().when(tradingRunService).recordPhaseFailure(eq(100L), any(PhaseFailureRequest.class));

        // Realistic Python payload — mixed JSONB types in guardrailFailedOutput
        // (string, int, nested dict, array) verify the Map<String, Object>
        // round-trip Jackson preserves.
        String pythonShapedJson =
                """
                {
                  "phaseKind": "RESEARCH",
                  "guardrailAttempts": 3,
                  "guardrailIssues": ["fake_url", "empty_candidates"],
                  "guardrailOutcome": "exhausted",
                  "guardrailFailedOutput": {
                    "summary": "Banks look hot.",
                    "attemptCount": 3,
                    "candidates": [{"symbol": "FAKE", "price": -1.5}],
                    "meta": {"flagged": true, "reason": "fake_url"}
                  }
                }
                """;

        mockMvc.perform(post("/api/runs/100/phase-failure")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(pythonShapedJson))
                .andExpect(status().isOk());

        ArgumentCaptor<PhaseFailureRequest> captor = ArgumentCaptor.forClass(PhaseFailureRequest.class);
        verify(tradingRunService).recordPhaseFailure(eq(100L), captor.capture());

        PhaseFailureRequest delivered = captor.getValue();
        assertThat(delivered.getPhaseKind()).isEqualTo(PhaseFailureRequest.PhaseKind.RESEARCH);
        assertThat(delivered.getGuardrailAttempts()).isEqualTo(3);
        assertThat(delivered.getGuardrailIssues()).containsExactly("fake_url", "empty_candidates");
        assertThat(delivered.getGuardrailOutcome()).isEqualTo(GuardrailOutcomeKind.EXHAUSTED);

        // JSONB shape preservation — strings, ints, nested dicts, arrays must all
        // make it through Jackson into the Map<String, Object> the service writes.
        var failedOutput = delivered.getGuardrailFailedOutput();
        assertThat(failedOutput).containsEntry("summary", "Banks look hot.");
        assertThat(failedOutput).containsEntry("attemptCount", 3);
        assertThat(failedOutput.get("candidates")).isInstanceOf(List.class);
        assertThat(failedOutput.get("meta")).isInstanceOf(java.util.Map.class);
        @SuppressWarnings("unchecked")
        var meta = (java.util.Map<String, Object>) failedOutput.get("meta");
        assertThat(meta).containsEntry("flagged", true).containsEntry("reason", "fake_url");
    }

    @Test
    @DisplayName("Python-shaped DECISION body deserialises into PhaseFailureRequest")
    void recordPhaseFailure_DecisionBody_DeserialisesAndCallsService() throws Exception {
        doNothing().when(tradingRunService).recordPhaseFailure(eq(100L), any(PhaseFailureRequest.class));

        String pythonShapedJson =
                """
                {
                  "phaseKind": "DECISION",
                  "guardrailAttempts": 2,
                  "guardrailIssues": ["invalid_action"],
                  "guardrailOutcome": "recovered",
                  "guardrailFailedOutput": {"action": "BUY", "quantity": 0}
                }
                """;

        mockMvc.perform(post("/api/runs/100/phase-failure")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(pythonShapedJson))
                .andExpect(status().isOk());

        ArgumentCaptor<PhaseFailureRequest> captor = ArgumentCaptor.forClass(PhaseFailureRequest.class);
        verify(tradingRunService).recordPhaseFailure(eq(100L), captor.capture());

        PhaseFailureRequest delivered = captor.getValue();
        assertThat(delivered.getPhaseKind()).isEqualTo(PhaseFailureRequest.PhaseKind.DECISION);
        assertThat(delivered.getGuardrailOutcome()).isEqualTo(GuardrailOutcomeKind.RECOVERED);
    }

    @Test
    @DisplayName("Unknown guardrailOutcome value returns 400 and service is not called (validates R2)")
    void recordPhaseFailure_TypoOutcome_Returns400() throws Exception {
        // Common typo — Python's Literal would reject this on its side; Java must too.
        String typoJson =
                """
                {
                  "phaseKind": "RESEARCH",
                  "guardrailAttempts": 3,
                  "guardrailOutcome": "exausted"
                }
                """;

        mockMvc.perform(post("/api/runs/100/phase-failure")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(typoJson))
                .andExpect(status().isBadRequest());

        verify(tradingRunService, never()).recordPhaseFailure(any(), any());
    }

    @Test
    @DisplayName("All three valid outcome values deserialise cleanly")
    void recordPhaseFailure_AllValidOutcomes_Deserialise() throws Exception {
        doNothing().when(tradingRunService).recordPhaseFailure(eq(100L), any(PhaseFailureRequest.class));

        for (String wireValue : List.of("first_try", "recovered", "exhausted")) {
            String body = String.format(
                    """
                    {
                      "phaseKind": "RESEARCH",
                      "guardrailAttempts": 1,
                      "guardrailOutcome": "%s"
                    }
                    """,
                    wireValue);
            mockMvc.perform(post("/api/runs/100/phase-failure")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(body))
                    .andExpect(status().isOk());
        }
    }

    @Test
    @DisplayName("Stale run id returns 404 when service throws ResourceNotFoundException")
    void recordPhaseFailure_MissingRun_Returns404() throws Exception {
        doThrow(new ResourceNotFoundException("Trading run not found with ID: 404"))
                .when(tradingRunService)
                .recordPhaseFailure(eq(404L), any(PhaseFailureRequest.class));

        String body =
                """
                {
                  "phaseKind": "RESEARCH",
                  "guardrailAttempts": 3,
                  "guardrailOutcome": "exhausted"
                }
                """;

        mockMvc.perform(post("/api/runs/404/phase-failure")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("Missing guardrailOutcome returns 400 via @NotNull")
    void recordPhaseFailure_MissingOutcome_Returns400() throws Exception {
        String body =
                """
                {
                  "phaseKind": "RESEARCH",
                  "guardrailAttempts": 3
                }
                """;
        mockMvc.perform(post("/api/runs/100/phase-failure")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest());

        verify(tradingRunService, never()).recordPhaseFailure(any(), any());
    }
}
