package com.trading.service;

import com.trading.enums.RunPhase;

/**
 * Validates phase transitions for a trading run.
 * Static helper — pure function over (currentPhase, targetPhase), no dependencies.
 * Delegates to {@link RunPhase#canTransitionTo(RunPhase)} for the transition table.
 */
public final class RunStateMachine {

    private RunStateMachine() {
        // utility class — no instances
    }

    /**
     * Throws {@link IllegalArgumentException} if transitioning from {@code from}
     * to {@code to} is not allowed by {@link RunPhase#canTransitionTo(RunPhase)}.
     *
     * @param from the current phase (must not be null)
     * @param to   the target phase
     * @throws IllegalArgumentException if the transition is not permitted
     */
    public static void requireValidTransition(RunPhase from, RunPhase to) {
        if (!from.canTransitionTo(to)) {
            throw new IllegalArgumentException("Invalid phase transition: " + from + " -> " + to);
        }
    }
}
