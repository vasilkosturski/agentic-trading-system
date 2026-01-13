package com.trading.enums;

/**
 * Trading run execution phases.
 * Represents the current stage of an autonomous trading cycle.
 */
public enum RunPhase {
    /**
     * Starting trading cycle, initializing context
     */
    INITIALIZING,

    /**
     * Gathering market data and analyzing opportunities
     */
    RESEARCHING,

    /**
     * Making trading decision (BUY/SELL/HOLD)
     */
    DECIDING,

    /**
     * Executing trade (if BUY/SELL decision)
     */
    TRADING,

    /**
     * Cycle finished successfully
     */
    COMPLETED,

    /**
     * Cycle encountered error and stopped
     */
    ERROR
}
