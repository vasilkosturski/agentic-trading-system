package com.trading.enums;

import java.util.Map;
import java.util.Set;

public enum RunPhase {
    INITIALIZING,
    RESEARCHING,
    DECIDING,
    TRADING,
    COMPLETED,
    FAILED;

    private static final Map<RunPhase, Set<RunPhase>> VALID_TRANSITIONS = Map.of(
            INITIALIZING, Set.of(RESEARCHING, FAILED),
            RESEARCHING, Set.of(DECIDING, FAILED),
            DECIDING, Set.of(TRADING, COMPLETED, FAILED),
            TRADING, Set.of(COMPLETED, FAILED),
            COMPLETED, Set.of(),
            FAILED, Set.of(FAILED));

    public boolean canTransitionTo(RunPhase target) {
        return VALID_TRANSITIONS.getOrDefault(this, Set.of()).contains(target);
    }
}
