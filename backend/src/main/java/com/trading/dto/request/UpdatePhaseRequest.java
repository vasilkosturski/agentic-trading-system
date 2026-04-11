package com.trading.dto.request;

import com.trading.enums.RunPhase;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request to update trading run phase.
 * Per design.md: PATCH /api/runs/{id}/phase - Updates phase field only.
 *
 * Valid transitions:
 * - INITIALIZING → RESEARCHING
 * - RESEARCHING → DECIDING
 * - DECIDING → TRADING
 * - TRADING → COMPLETED
 * - Any → ERROR (for failures)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UpdatePhaseRequest {

    @NotNull(message = "Phase is required")
    private RunPhase phase;

    /** Optional error message when transitioning to ERROR phase. */
    private String errorMessage;
}
