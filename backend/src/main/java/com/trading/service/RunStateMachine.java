package com.trading.service;

import com.trading.enums.RunPhase;

public final class RunStateMachine {

    private RunStateMachine() {}

    public static void requireValidTransition(RunPhase from, RunPhase to) {
        if (!from.canTransitionTo(to)) {
            throw new IllegalArgumentException("Invalid phase transition: " + from + " -> " + to);
        }
    }
}
