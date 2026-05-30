package com.trading.dto.request;

import com.trading.entity.AccountTransaction;
import com.trading.entity.DecisionPhase;
import com.trading.entity.ExecutionPhase;
import com.trading.entity.TradingRun;
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

    /**
     * Convert this request DTO into an {@link ExecutionPhase} entity attached
     * to the given run and decision phase.
     *
     * <p>The caller is responsible for resolving {@link #tradeId} to an
     * {@link AccountTransaction} (DTOs must not depend on repositories) and
     * passing the result as {@code resolvedTrade}. The status precedence
     * matches the original inline binding:
     * <ol>
     *   <li>Explicit {@code status} on the DTO wins.</li>
     *   <li>Otherwise: {@code tradeId != null} ⇒ {@code COMPLETED} (intent
     *       expressed by the caller), {@code tradeId == null} ⇒ {@code FAILED}.</li>
     * </ol>
     * {@code resolvedTrade} may be {@code null} when {@code tradeId} did not
     * resolve to a row; the phase records the supplied/derived status
     * regardless.
     */
    public ExecutionPhase toEntity(TradingRun run, DecisionPhase decisionPhase, AccountTransaction resolvedTrade) {
        ExecutionPhase phase = new ExecutionPhase();
        phase.setRun(run);
        phase.setDecision(decisionPhase);
        phase.setTrade(resolvedTrade);
        if (status != null) {
            phase.setStatus(status);
        } else {
            phase.setStatus(tradeId != null ? PhaseStatus.COMPLETED : PhaseStatus.FAILED);
        }
        phase.setErrorDetails(errorDetails);
        return phase;
    }
}
