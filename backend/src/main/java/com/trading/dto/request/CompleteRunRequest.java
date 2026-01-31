package com.trading.dto.request;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request to complete a trading run with all phase data.
 * Per design.md: PUT /api/runs/{id}/complete - Persists all phases atomically.
 *
 * Structure: Nested phase DTOs for self-documenting API.
 * - research: Data from RESEARCHING phase
 * - decision: Data from DECIDING phase
 * - execution: Data from TRADING phase (optional for HOLD)
 *
 * Single endpoint simplifies agent code (one call at end of workflow).
 * All phases persisted in a single @Transactional operation.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CompleteRunRequest {

    /**
     * Research phase data (candidates, sources, notes, tool calls).
     */
    @Valid
    private ResearchPhaseDto research;

    /**
     * Decision phase data (decision, symbol, quantity, reasoning).
     */
    @NotNull(message = "Decision phase data is required")
    @Valid
    private DecisionPhaseDto decision;

    /**
     * Execution phase data (tradeId, status, errors).
     * May be null for HOLD decisions.
     */
    @Valid
    private ExecutionPhaseDto execution;

    /**
     * Validate the request structure.
     * Delegates to nested DTOs for phase-specific validation.
     */
    public void validate() {
        if (decision != null) {
            decision.validate();
        }
    }
}
