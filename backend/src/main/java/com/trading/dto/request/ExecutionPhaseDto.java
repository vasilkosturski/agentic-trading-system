package com.trading.dto.request;

import com.trading.enums.PhaseStatus;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Execution phase data for CompleteRunRequest.
 * Contains all data collected during the TRADING phase.
 * Only populated for BUY/SELL decisions.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ExecutionPhaseDto {

    /**
     * Reference to executed trade (if successful).
     * Null for HOLD or failed trades.
     */
    private Long tradeId;

    /**
     * Execution status: COMPLETED, FAILED, or SKIPPED.
     * - COMPLETED: Trade executed successfully
     * - FAILED: Trade validation failed
     * - SKIPPED: HOLD decision, no trade needed
     */
    private PhaseStatus status;

    /**
     * Error details for failed executions.
     * Example: "Insufficient funds: need $4500.00, have $2000.00"
     */
    private String errorDetails;
}
