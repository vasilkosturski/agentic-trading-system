package com.trading.dto.request;

import com.trading.enums.GuardrailOutcomeKind;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.Map;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request body for {@code POST /api/runs/{id}/phase-failure}.
 *
 * <p>Records a stub research/decision phase row with guardrail outcome columns
 * populated when the guardrail-retry loop exhausts and the orchestrator's
 * {@code complete_run} pathway never fires. Closes the {@code outcome='exhausted'}
 * persistence gap so the row exists in the audit DB even on a FAILED run.
 *
 * <p>{@link #guardrailOutcome} is a typed {@link GuardrailOutcomeKind} enum so
 * Jackson rejects unknown wire values (e.g. {@code "exausted"} typo) with a
 * 400 response, matching the Python-side {@code Literal} constraint.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PhaseFailureRequest {

    public enum PhaseKind {
        RESEARCH,
        DECISION
    }

    @NotNull(message = "Phase kind is required")
    private PhaseKind phaseKind;

    @NotNull(message = "Guardrail attempts is required")
    private Integer guardrailAttempts;

    private List<String> guardrailIssues;

    @NotNull(message = "Guardrail outcome is required")
    private GuardrailOutcomeKind guardrailOutcome;

    private Map<String, Object> guardrailFailedOutput;
}
