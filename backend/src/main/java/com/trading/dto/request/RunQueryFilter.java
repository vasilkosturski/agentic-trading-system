package com.trading.dto.request;

import com.trading.enums.RunStatus;
import com.trading.enums.TradeDecision;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Filter criteria for listing trading runs.
 * Per design.md: GET /api/runs?filters - All fields optional.
 *
 * Used with JPA Specification API for dynamic filtering.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RunQueryFilter {

    /**
     * Filter by agent ID (optional)
     */
    private Long agentId;

    /**
     * Filter by run status: IN_PROGRESS, COMPLETED, FAILED (optional)
     */
    private RunStatus status;

    /**
     * Filter by trade decision: BUY, SELL, HOLD (optional)
     * Requires join to decision_phases table.
     */
    private TradeDecision decision;

    /**
     * Filter by traded symbol (optional)
     * Requires join to decision_phases table.
     */
    private String symbol;

    /**
     * Check if any filters are set.
     */
    public boolean hasFilters() {
        return agentId != null || status != null || decision != null || symbol != null;
    }
}
