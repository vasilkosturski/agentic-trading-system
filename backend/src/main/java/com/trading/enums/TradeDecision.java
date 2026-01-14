package com.trading.enums;

/**
 * Trade decision enum - BUY, SELL, or HOLD.
 * Per design doc: Trader LLM makes one of three decisions per trading cycle.
 *
 * Values:
 * - BUY: Purchase shares of a symbol
 * - SELL: Sell existing shares of a symbol
 * - HOLD: No trades this cycle (maintain current portfolio)
 */
public enum TradeDecision {
    /**
     * Buy shares of a symbol.
     * Requires: symbol, quantity
     */
    BUY,

    /**
     * Sell existing shares of a symbol.
     * Requires: symbol, quantity
     */
    SELL,

    /**
     * No trades this cycle.
     * Symbol and quantity should be null.
     */
    HOLD;

    /**
     * Check if decision requires trade execution.
     */
    public boolean requiresExecution() {
        return this == BUY || this == SELL;
    }

    /**
     * Check if decision is HOLD (no execution).
     */
    public boolean isHold() {
        return this == HOLD;
    }
}
