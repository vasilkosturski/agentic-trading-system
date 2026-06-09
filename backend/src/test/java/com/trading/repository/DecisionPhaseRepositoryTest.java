package com.trading.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.trading.dto.jsonb.ReasoningDto;
import com.trading.dto.jsonb.SourceDto;
import com.trading.dto.jsonb.ToolCallDto;
import com.trading.entity.DecisionPhase;
import com.trading.entity.TradingAgent;
import com.trading.entity.TradingRun;
import com.trading.enums.TradeDecision;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

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
        phase.setLatencyMs(3500L);

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
    @DisplayName("Should round-trip reasoning + tool_calls + sources JSONB columns")
    void shouldRoundTripAllJsonbColumns() {
        // Single round-trip exercises all 3 JSONB columns — the Hibernate
        // serializer wiring is shared across them, so one save/load proves
        // the same path for every column.
        DecisionPhase phase = new DecisionPhase(testRun);
        phase.setDecision(TradeDecision.BUY);
        phase.setSymbol("BAC");
        phase.setQuantity(15);

        ReasoningDto reasoning = new ReasoningDto();
        reasoning.setRationale("Buying BAC because strong earnings and value metrics are compelling.");
        reasoning.setPortfolioContext("Current cash: $50,000. Holdings: 5 positions.");
        reasoning.setHistoricalContext("No previous trades in BAC. Last financials trade was GS.");
        reasoning.setResearchContext("Market Analyst identified BAC as top candidate based on earnings.");
        phase.setReasoning(reasoning);

        ToolCallDto toolCall1 = new ToolCallDto();
        toolCall1.setTool("get_symbol_trade_history");
        toolCall1.setParams(Map.of("symbol", "BAC", "limit", 10));
        ToolCallDto toolCall2 = new ToolCallDto();
        toolCall2.setTool("get_current_price");
        toolCall2.setParams(Map.of("symbol", "BAC"));
        phase.setToolCalls(List.of(toolCall1, toolCall2));

        SourceDto source = new SourceDto();
        source.setType("system_context");
        source.setDescription("Earnings beat consensus by 12%");
        phase.setSources(List.of(source));

        decisionPhaseRepository.save(phase);
        DecisionPhase loaded =
                decisionPhaseRepository.findByRunId(testRun.getId()).orElseThrow();

        ReasoningDto loadedReasoning = loaded.getReasoning();
        assertThat(loadedReasoning).isNotNull();
        assertThat(loadedReasoning.getRationale())
                .isEqualTo("Buying BAC because strong earnings and value metrics are compelling.");
        assertThat(loadedReasoning.getPortfolioContext()).isEqualTo("Current cash: $50,000. Holdings: 5 positions.");
        assertThat(loadedReasoning.getHistoricalContext())
                .isEqualTo("No previous trades in BAC. Last financials trade was GS.");
        assertThat(loadedReasoning.getResearchContext())
                .isEqualTo("Market Analyst identified BAC as top candidate based on earnings.");

        assertThat(loaded.getToolCalls()).hasSize(2);
        assertThat(loaded.getToolCalls().get(0).getTool()).isEqualTo("get_symbol_trade_history");
        assertThat(loaded.getToolCalls().get(0).getParams()).containsEntry("symbol", "BAC");
        assertThat(loaded.getToolCalls().get(1).getTool()).isEqualTo("get_current_price");

        assertThat(loaded.getSources()).hasSize(1);
        assertThat(loaded.getSources().get(0).getType()).isEqualTo("system_context");
        assertThat(loaded.getSources().get(0).getDescription()).isEqualTo("Earnings beat consensus by 12%");
    }

    @Test
    @DisplayName("Should handle HOLD decision correctly")
    void shouldHandleHoldDecision() {
        // Arrange
        DecisionPhase phase = new DecisionPhase(testRun);
        phase.setDecision(TradeDecision.HOLD);
        // symbol and quantity should be null for HOLD

        ReasoningDto reasoning = new ReasoningDto();
        phase.setReasoning(reasoning);

        // Act
        decisionPhaseRepository.save(phase);
        DecisionPhase loaded =
                decisionPhaseRepository.findByRunId(testRun.getId()).orElseThrow();

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

    @Test
    @DisplayName("Should default guardrail outcome columns to first_try / 1 / null")
    void shouldDefaultGuardrailOutcomeColumns() {
        DecisionPhase phase = new DecisionPhase(testRun);
        phase.setDecision(TradeDecision.HOLD);
        decisionPhaseRepository.save(phase);
        DecisionPhase loaded =
                decisionPhaseRepository.findByRunId(testRun.getId()).orElseThrow();

        assertThat(loaded.getGuardrailAttempts()).isEqualTo(1);
        assertThat(loaded.getGuardrailOutcome()).isEqualTo("first_try");
        assertThat(loaded.getGuardrailIssues()).isNull();
    }

    @Test
    @DisplayName("Should round-trip recovered guardrail outcome with JSONB issues array")
    void shouldRoundTripRecoveredGuardrailOutcome() {
        DecisionPhase phase = new DecisionPhase(testRun);
        phase.setDecision(TradeDecision.HOLD);
        phase.setGuardrailAttempts(3);
        phase.setGuardrailOutcome("recovered");
        phase.setGuardrailIssues(List.of("invalid_quantity"));

        decisionPhaseRepository.save(phase);
        DecisionPhase loaded =
                decisionPhaseRepository.findByRunId(testRun.getId()).orElseThrow();

        assertThat(loaded.getGuardrailAttempts()).isEqualTo(3);
        assertThat(loaded.getGuardrailOutcome()).isEqualTo("recovered");
        assertThat(loaded.getGuardrailIssues()).containsExactly("invalid_quantity");
    }

    @Test
    @DisplayName("Should round-trip guardrail_failed_output JSONB with TradingDecision-shaped payload")
    void shouldRoundTripGuardrailFailedOutput() {
        // Representative payload mirroring a TradingDecision the LLM might
        // have produced that got flagged — invalid action/quantity combo.
        Map<String, Object> failedOutput = Map.of(
                "action", "BUY",
                "symbol", "JPM",
                "quantity", 0,
                "rationale", "Hesitant buy.",
                "portfolioContext", "5 holdings.",
                "historicalContext", "No prior JPM trades.",
                "researchContext", "Analyst flagged JPM as candidate.");

        DecisionPhase phase = new DecisionPhase(testRun);
        phase.setDecision(TradeDecision.HOLD);
        phase.setGuardrailAttempts(2);
        phase.setGuardrailOutcome("recovered");
        phase.setGuardrailIssues(List.of("invalid_quantity"));
        phase.setGuardrailFailedOutput(failedOutput);

        decisionPhaseRepository.save(phase);
        DecisionPhase loaded =
                decisionPhaseRepository.findByRunId(testRun.getId()).orElseThrow();

        Map<String, Object> loadedOutput = loaded.getGuardrailFailedOutput();
        assertThat(loadedOutput).isNotNull();
        assertThat(loadedOutput.get("action")).isEqualTo("BUY");
        assertThat(loadedOutput.get("symbol")).isEqualTo("JPM");
        assertThat(loadedOutput.get("quantity")).isEqualTo(0);
        assertThat(loadedOutput.get("rationale")).isEqualTo("Hesitant buy.");
    }

    @Test
    @DisplayName("Should default guardrail_failed_output to null")
    void shouldDefaultGuardrailFailedOutputToNull() {
        DecisionPhase phase = new DecisionPhase(testRun);
        phase.setDecision(TradeDecision.HOLD);
        decisionPhaseRepository.save(phase);
        DecisionPhase loaded =
                decisionPhaseRepository.findByRunId(testRun.getId()).orElseThrow();

        assertThat(loaded.getGuardrailFailedOutput()).isNull();
    }
}
