package com.trading.dto.request;

import com.trading.dto.jsonb.DecisionToolCallDto;
import com.trading.dto.jsonb.ReasoningDto;
import com.trading.dto.jsonb.ResearchToolCallDto;
import com.trading.dto.jsonb.SourceDto;
import com.trading.enums.PhaseStatus;
import com.trading.enums.TradeDecision;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * Request to complete a trading run with all phase data.
 * Per design.md: PUT /api/runs/{id}/complete - Persists all phases atomically.
 *
 * Single endpoint simplifies agent code (one call at end of workflow).
 * All phases persisted in a single @Transactional operation.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CompleteRunRequest {

    // ========== Research Phase Data ==========

    /**
     * Stock symbols researched (e.g., ["JPM", "BAC", "WFC"])
     */
    private List<String> candidates;

    /**
     * Web sources and system context used in research.
     */
    private List<SourceDto> researchSources;

    /**
     * Agent's research notes (markdown format)
     */
    private String researchNotes;

    /**
     * Tool calls made during research phase (Brave Search, Memory, etc.)
     */
    private List<ResearchToolCallDto> researchToolCalls;

    /**
     * Research phase execution time in milliseconds.
     */
    private Long researchLatencyMs;

    // ========== Decision Phase Data ==========

    @NotNull(message = "Decision is required (BUY, SELL, or HOLD)")
    private TradeDecision decision;

    /**
     * Symbol to trade (null for HOLD)
     */
    private String symbol;

    /**
     * Quantity to trade (null for HOLD)
     */
    private Integer quantity;

    /**
     * Structured reasoning for the decision.
     */
    @Valid
    private ReasoningDto reasoning;

    /**
     * Sources used in decision phase.
     */
    private List<SourceDto> decisionSources;

    /**
     * Tool calls made during decision phase.
     */
    private List<DecisionToolCallDto> decisionToolCalls;

    /**
     * Decision phase execution time in milliseconds.
     */
    private Long decisionLatencyMs;

    // ========== Execution Phase Data (optional - only for BUY/SELL) ==========

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
    private PhaseStatus executionStatus;

    /**
     * Error details for failed executions.
     * Example: "Insufficient funds: need $4500.00, have $2000.00"
     */
    private String errorDetails;

    /**
     * Validate decision consistency.
     * BUY/SELL decisions must have symbol and quantity.
     */
    public void validate() {
        if (decision == TradeDecision.BUY || decision == TradeDecision.SELL) {
            if (symbol == null || symbol.trim().isEmpty()) {
                throw new IllegalArgumentException(
                    decision + " decision requires symbol");
            }
            if (quantity == null || quantity <= 0) {
                throw new IllegalArgumentException(
                    decision + " decision requires positive quantity");
            }
        }
    }
}
