package com.trading.enums;

import java.util.Map;
import java.util.Set;

/**
 * Trading run execution phases.
 * Represents the current stage of an autonomous trading cycle.
 *
 * <p>Valid transitions:
 * <pre>
 * INITIALIZING -> RESEARCHING, ERROR
 * RESEARCHING  -> DECIDING, ERROR
 * DECIDING     -> TRADING, COMPLETED (HOLD), ERROR
 * TRADING      -> COMPLETED, ERROR
 * COMPLETED    -> (terminal)
 * ERROR        -> ERROR (idempotent)
 * </pre>
 */
public enum RunPhase {
    /** Starting trading cycle, initializing context */
    INITIALIZING,

    /** Gathering market data and analyzing opportunities */
    RESEARCHING,

    /** Making trading decision (BUY/SELL/HOLD) */
    DECIDING,

    /** Executing trade (if BUY/SELL decision) */
    TRADING,

    /** Cycle finished successfully (terminal) */
    COMPLETED,

    /** Cycle encountered error and stopped */
    ERROR;

    private static final Map<RunPhase, Set<RunPhase>> VALID_TRANSITIONS = Map.of(
        INITIALIZING, Set.of(RESEARCHING, ERROR),
        RESEARCHING,  Set.of(DECIDING, ERROR),
        DECIDING,     Set.of(TRADING, COMPLETED, ERROR),
        TRADING,      Set.of(COMPLETED, ERROR),
        COMPLETED,    Set.of(),
        ERROR,        Set.of(ERROR)
    );

    /**
     * Check whether transitioning from this phase to the target phase is allowed.
     *
     * @param target the phase to transition to
     * @return true if the transition is valid
     */
    public boolean canTransitionTo(RunPhase target) {
        return VALID_TRANSITIONS.getOrDefault(this, Set.of()).contains(target);
    }
}
