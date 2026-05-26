package com.trading.service;

import com.trading.entity.DecisionPhase;

import java.util.Optional;

/**
 * Extracts the research-context summary from a decision's reasoning JSONB blob.
 * Static helper — pure transformation, no dependencies.
 */
public final class ReasoningSummaryExtractor {

    private ReasoningSummaryExtractor() {
        // utility class — no instances
    }

    /**
     * Returns the research-context summary if present and non-empty.
     * Handles null decision, null reasoning, and null/empty researchContext defensively.
     */
    public static Optional<String> extractSummary(DecisionPhase decision) {
        if (decision == null || decision.getReasoning() == null) {
            return Optional.empty();
        }
        String summary = decision.getReasoning().getResearchContext();
        if (summary == null || summary.isEmpty()) {
            return Optional.empty();
        }
        return Optional.of(summary);
    }
}
