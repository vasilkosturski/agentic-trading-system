package com.trading.service;

import com.trading.dto.jsonb.ReasoningDto;
import com.trading.entity.DecisionPhase;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("ReasoningSummaryExtractor tests")
class ReasoningSummaryExtractorTest {

    @Test
    @DisplayName("null decision returns Optional.empty")
    void nullDecisionReturnsEmpty() {
        assertThat(ReasoningSummaryExtractor.extractSummary(null)).isEmpty();
    }

    @Test
    @DisplayName("null reasoning returns Optional.empty")
    void nullReasoningReturnsEmpty() {
        DecisionPhase decision = new DecisionPhase();
        decision.setReasoning(null);
        assertThat(ReasoningSummaryExtractor.extractSummary(decision)).isEmpty();
    }

    @Test
    @DisplayName("null researchContext returns Optional.empty")
    void nullResearchContextReturnsEmpty() {
        DecisionPhase decision = new DecisionPhase();
        decision.setReasoning(new ReasoningDto(null, null, null, null));
        assertThat(ReasoningSummaryExtractor.extractSummary(decision)).isEmpty();
    }

    @Test
    @DisplayName("empty researchContext returns Optional.empty")
    void emptyResearchContextReturnsEmpty() {
        DecisionPhase decision = new DecisionPhase();
        decision.setReasoning(new ReasoningDto(null, null, null, ""));
        assertThat(ReasoningSummaryExtractor.extractSummary(decision)).isEmpty();
    }

    @Test
    @DisplayName("non-empty researchContext returns Optional with value")
    void nonEmptyResearchContextReturnsValue() {
        DecisionPhase decision = new DecisionPhase();
        decision.setReasoning(new ReasoningDto(null, null, null, "Market Analyst found 5 value stocks"));
        Optional<String> result = ReasoningSummaryExtractor.extractSummary(decision);
        assertThat(result).contains("Market Analyst found 5 value stocks");
    }
}
