package com.trading.repository;

import com.trading.dto.jsonb.DecisionToolCallDto;
import com.trading.dto.jsonb.ReasoningDto;
import com.trading.dto.jsonb.SourceDto;
import com.trading.entity.DecisionPhase;
import com.trading.enums.TradeDecision;
import com.trading.entity.TradingAgent;
import com.trading.entity.TradingRun;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Repository tests for DecisionPhase entity.
 * Tests JSONB round-trip serialization for reasoning and tool_calls.
 */
@DisplayName("DecisionPhaseRepository Tests")
class DecisionPhaseRepositoryTest extends BaseRepositoryTest {

    @Autowired
    private DecisionPhaseRepository decisionPhaseRepository;

    @Autowired
    private TradingRunRepository tradingRunRepository;

    @Autowired
    private TradingAgentRepository tradingAgentRepository;

    private TradingRun testRun;

    @BeforeEach
    void setUp() {
        // Clean up
        decisionPhaseRepository.deleteAll();
        tradingRunRepository.deleteAll();
        tradingAgentRepository.deleteAll();
        
        // Create test agent and run
        TradingAgent agent = new TradingAgent("TestAgent", "Test agent");
        agent.setInitialCapital(100000.0);
        agent = tradingAgentRepository.save(agent);
        
        testRun = new TradingRun(agent);
        testRun = tradingRunRepository.save(testRun);
    }

    @Test
    @DisplayName("Should save and retrieve DecisionPhase with enum")
    void shouldSaveAndRetrieveDecisionPhase() {
        // Arrange
        DecisionPhase phase = new DecisionPhase(testRun);
        phase.setDecision(TradeDecision.BUY);
        phase.setSymbol("JPM");
        phase.setQuantity(10);
        phase.setTokensUsed(2000);
        phase.setLatencyMs(3500L);
        phase.setCostUsd(new BigDecimal("0.000300"));
        
        // Act
        DecisionPhase saved = decisionPhaseRepository.save(phase);
        Optional<DecisionPhase> found = decisionPhaseRepository.findById(saved.getId());
        
        // Assert
        assertThat(found).isPresent();
        assertThat(found.get().getDecision()).isEqualTo(TradeDecision.BUY);
        assertThat(found.get().getSymbol()).isEqualTo("JPM");
        assertThat(found.get().getQuantity()).isEqualTo(10);
        assertThat(found.get().isBuy()).isTrue();
        assertThat(found.get().requiresExecution()).isTrue();
    }

    @Test
    @DisplayName("Should round-trip reasoning JSONB object")
    void shouldRoundTripReasoningJsonb() {
        // Arrange
        DecisionPhase phase = new DecisionPhase(testRun);
        phase.setDecision(TradeDecision.BUY);
        phase.setSymbol("BAC");
        phase.setQuantity(15);
        
        ReasoningDto reasoning = new ReasoningDto();
        reasoning.setPortfolioContext("Current cash: $50,000. Holdings: 5 positions.");
        reasoning.setHistoricalContext("No previous trades in BAC. Last financials trade was GS.");
        reasoning.setResearchSummary("Market Analyst identified BAC as top candidate based on earnings.");
        reasoning.setCandidateEvaluation("BAC: Strong buy signal. JPM: Hold. WFC: Weak.");
        reasoning.setFinalRationale("BAC has the best risk/reward ratio given current portfolio exposure.");
        
        phase.setReasoning(reasoning);
        
        // Act
        decisionPhaseRepository.save(phase);
        DecisionPhase loaded = decisionPhaseRepository.findByRunId(testRun.getId()).orElseThrow();
        
        // Assert
        ReasoningDto loadedReasoning = loaded.getReasoning();
        assertThat(loadedReasoning).isNotNull();
        assertThat(loadedReasoning.getPortfolioContext()).isEqualTo("Current cash: $50,000. Holdings: 5 positions.");
        assertThat(loadedReasoning.getHistoricalContext()).isEqualTo("No previous trades in BAC. Last financials trade was GS.");
        assertThat(loadedReasoning.getResearchSummary()).isEqualTo("Market Analyst identified BAC as top candidate based on earnings.");
        assertThat(loadedReasoning.getCandidateEvaluation()).isEqualTo("BAC: Strong buy signal. JPM: Hold. WFC: Weak.");
        assertThat(loadedReasoning.getFinalRationale()).isEqualTo("BAC has the best risk/reward ratio given current portfolio exposure.");
    }

    @Test
    @DisplayName("Should round-trip tool_calls JSONB with params")
    void shouldRoundTripToolCallsWithParams() {
        // Arrange
        DecisionPhase phase = new DecisionPhase(testRun);
        phase.setDecision(TradeDecision.SELL);
        phase.setSymbol("AAPL");
        phase.setQuantity(5);
        
        DecisionToolCallDto toolCall1 = new DecisionToolCallDto();
        toolCall1.setTool("get_symbol_trade_history");
        toolCall1.setParams(Map.of("symbol", "AAPL", "limit", 10));
        toolCall1.setDurationMs(150L);
        
        DecisionToolCallDto toolCall2 = new DecisionToolCallDto();
        toolCall2.setTool("get_current_price");
        toolCall2.setParams(Map.of("symbol", "AAPL"));
        toolCall2.setDurationMs(80L);
        
        phase.setToolCalls(List.of(toolCall1, toolCall2));
        
        // Act
        decisionPhaseRepository.save(phase);
        DecisionPhase loaded = decisionPhaseRepository.findByRunId(testRun.getId()).orElseThrow();
        
        // Assert
        assertThat(loaded.getToolCalls()).hasSize(2);
        
        DecisionToolCallDto loadedCall1 = loaded.getToolCalls().get(0);
        assertThat(loadedCall1.getTool()).isEqualTo("get_symbol_trade_history");
        assertThat(loadedCall1.getDurationMs()).isEqualTo(150L);
        assertThat(loadedCall1.getParams()).containsEntry("symbol", "AAPL");
        
        DecisionToolCallDto loadedCall2 = loaded.getToolCalls().get(1);
        assertThat(loadedCall2.getTool()).isEqualTo("get_current_price");
        assertThat(loadedCall2.getDurationMs()).isEqualTo(80L);
    }

    @Test
    @DisplayName("Should round-trip sources JSONB")
    void shouldRoundTripSourcesJsonb() {
        // Arrange
        DecisionPhase phase = new DecisionPhase(testRun);
        phase.setDecision(TradeDecision.HOLD);
        
        SourceDto source = new SourceDto();
        source.setType("system_context");
        source.setDescription("Portfolio already has maximum positions");
        
        phase.setSources(List.of(source));
        
        // Act
        decisionPhaseRepository.save(phase);
        DecisionPhase loaded = decisionPhaseRepository.findByRunId(testRun.getId()).orElseThrow();
        
        // Assert
        assertThat(loaded.getSources()).hasSize(1);
        assertThat(loaded.getSources().get(0).getType()).isEqualTo("system_context");
        assertThat(loaded.getSources().get(0).getDescription()).isEqualTo("Portfolio already has maximum positions");
    }

    @Test
    @DisplayName("Should handle HOLD decision correctly")
    void shouldHandleHoldDecision() {
        // Arrange
        DecisionPhase phase = new DecisionPhase(testRun);
        phase.setDecision(TradeDecision.HOLD);
        // symbol and quantity should be null for HOLD
        
        ReasoningDto reasoning = new ReasoningDto();
        reasoning.setFinalRationale("Market conditions unfavorable. Holding cash.");
        phase.setReasoning(reasoning);
        
        // Act
        decisionPhaseRepository.save(phase);
        DecisionPhase loaded = decisionPhaseRepository.findByRunId(testRun.getId()).orElseThrow();
        
        // Assert
        assertThat(loaded.getDecision()).isEqualTo(TradeDecision.HOLD);
        assertThat(loaded.isHold()).isTrue();
        assertThat(loaded.requiresExecution()).isFalse();
        assertThat(loaded.getSymbol()).isNull();
        assertThat(loaded.getQuantity()).isNull();
    }

    @Test
    @DisplayName("Should find by run ID")
    void shouldFindByRunId() {
        // Arrange
        DecisionPhase phase = new DecisionPhase(testRun);
        phase.setDecision(TradeDecision.BUY);
        phase.setSymbol("MSFT");
        phase.setQuantity(20);
        decisionPhaseRepository.save(phase);
        
        // Act
        Optional<DecisionPhase> found = decisionPhaseRepository.findByRunId(testRun.getId());
        
        // Assert
        assertThat(found).isPresent();
        assertThat(found.get().getSymbol()).isEqualTo("MSFT");
    }

    @Test
    @DisplayName("Should check existence by run ID")
    void shouldCheckExistsByRunId() {
        // Arrange
        DecisionPhase phase = new DecisionPhase(testRun);
        phase.setDecision(TradeDecision.HOLD);
        decisionPhaseRepository.save(phase);
        
        // Act & Assert
        assertThat(decisionPhaseRepository.existsByRunId(testRun.getId())).isTrue();
        assertThat(decisionPhaseRepository.existsByRunId(99999L)).isFalse();
    }
}

