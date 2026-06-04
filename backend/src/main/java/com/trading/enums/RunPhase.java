package com.trading.enums;

import java.util.Map;
import java.util.Set;

/**
 * Trading run execution phases.
 * Represents the current stage of an autonomous trading cycle.
 *
 * <p>Valid transitions:
 * <pre>
 * INITIALIZING -> RESEARCHING, FAILED
 * RESEARCHING  -> DECIDING, FAILED
 * DECIDING     -> TRADING, COMPLETED (HOLD), FAILED
 * TRADING      -> COMPLETED, FAILED
 * COMPLETED    -> (terminal)
 * FAILED       -> FAILED (idempotent)
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

    /** Cycle failed (terminal) */
    FAILED;

    private static final Map<RunPhase, Set<RunPhase>> VALID_TRANSITIONS = Map.of(
            INITIALIZING, Set.of(RESEARCHING, FAILED),
            RESEARCHING, Set.of(DECIDING, FAILED),
            DECIDING, Set.of(TRADING, COMPLETED, FAILED),
            TRADING, Set.of(COMPLETED, FAILED),
            COMPLETED, Set.of(),
            FAILED, Set.of(FAILED));

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
