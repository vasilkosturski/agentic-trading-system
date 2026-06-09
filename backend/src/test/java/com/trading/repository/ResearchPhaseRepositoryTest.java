package com.trading.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.trading.dto.jsonb.SourceDto;
import com.trading.dto.jsonb.ToolCallDto;
import com.trading.entity.ResearchPhase;
import com.trading.entity.TradingAgent;
import com.trading.entity.TradingRun;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * Repository tests for ResearchPhase entity.
 * Tests JSONB round-trip serialization with real PostgreSQL.
 */
@DisplayName("ResearchPhaseRepository Tests")
class ResearchPhaseRepositoryTest extends BaseRepositoryTest {

    @Autowired
    private ResearchPhaseRepository researchPhaseRepository;

    @Autowired
    private TradingRunRepository tradingRunRepository;

    @Autowired
    private TradingAgentRepository tradingAgentRepository;

    private TradingRun testRun;

    @BeforeEach
    void setUp() {
        // Clean up
        researchPhaseRepository.deleteAll();
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
    @DisplayName("Should save and retrieve ResearchPhase")
    void shouldSaveAndRetrieveResearchPhase() {
        // Arrange
        ResearchPhase phase = new ResearchPhase(testRun);
        phase.setResearchNotes("Market analysis complete");
        phase.setLatencyMs(2500L);

        // Act
        ResearchPhase saved = researchPhaseRepository.save(phase);
        Optional<ResearchPhase> found = researchPhaseRepository.findById(saved.getId());

        // Assert
        assertThat(found).isPresent();
        assertThat(found.get().getResearchNotes()).isEqualTo("Market analysis complete");
        assertThat(found.get().getLatencyMs()).isEqualTo(2500L);
    }

    @Test
    @DisplayName("Should round-trip candidates + sources + tool_calls JSONB lists")
    void shouldRoundTripAllJsonbColumns() {
        // Single round-trip exercises the 3 JSONB columns — Hibernate's
        // serializer wiring is shared across them, so one save/load proves
        // the same path for every column.
        ResearchPhase phase = new ResearchPhase(testRun);
        phase.setCandidates(List.of("JPM", "BAC", "WFC", "GS"));

        SourceDto webSource = new SourceDto();
        webSource.setType("web");
        webSource.setTitle("Market Analysis Report");
        webSource.setUrl("https://example.com/report");
        webSource.setDescription("Comprehensive market analysis");

        SourceDto systemSource = new SourceDto();
        systemSource.setType("system_context");
        systemSource.setDescription("Current portfolio state");

        phase.setSources(List.of(webSource, systemSource));

        ToolCallDto toolCall1 = new ToolCallDto();
        toolCall1.setTool("brave_search");
        ToolCallDto toolCall2 = new ToolCallDto();
        toolCall2.setTool("memory_search");
        phase.setToolCalls(List.of(toolCall1, toolCall2));

        researchPhaseRepository.save(phase);
        ResearchPhase loaded =
                researchPhaseRepository.findByRunId(testRun.getId()).orElseThrow();

        assertThat(loaded.getCandidates()).containsExactly("JPM", "BAC", "WFC", "GS");

        assertThat(loaded.getSources()).hasSize(2);
        SourceDto loadedWebSource = loaded.getSources().get(0);
        assertThat(loadedWebSource.getType()).isEqualTo("web");
        assertThat(loadedWebSource.getTitle()).isEqualTo("Market Analysis Report");
        assertThat(loadedWebSource.getUrl()).isEqualTo("https://example.com/report");
        SourceDto loadedSystemSource = loaded.getSources().get(1);
        assertThat(loadedSystemSource.getType()).isEqualTo("system_context");
        assertThat(loadedSystemSource.getDescription()).isEqualTo("Current portfolio state");

        assertThat(loaded.getToolCalls()).hasSize(2);
        assertThat(loaded.getToolCalls().get(0).getTool()).isEqualTo("brave_search");
        assertThat(loaded.getToolCalls().get(1).getTool()).isEqualTo("memory_search");
    }

    @Test
    @DisplayName("Should find research phase by run ID")
    void shouldFindByRunId() {
        // Arrange
        ResearchPhase phase = new ResearchPhase(testRun);
        phase.setCandidates(List.of("AAPL", "MSFT"));
        researchPhaseRepository.save(phase);

        // Act
        Optional<ResearchPhase> found = researchPhaseRepository.findByRunId(testRun.getId());

        // Assert
        assertThat(found).isPresent();
        assertThat(found.get().getCandidates()).containsExactly("AAPL", "MSFT");
    }

    @Test
    @DisplayName("Should check existence by run ID")
    void shouldCheckExistsByRunId() {
        // Arrange
        ResearchPhase phase = new ResearchPhase(testRun);
        researchPhaseRepository.save(phase);

        // Act & Assert
        assertThat(researchPhaseRepository.existsByRunId(testRun.getId())).isTrue();
        assertThat(researchPhaseRepository.existsByRunId(99999L)).isFalse();
    }

    @Test
    @DisplayName("Should handle null JSONB fields")
    void shouldHandleNullJsonbFields() {
        // Arrange
        ResearchPhase phase = new ResearchPhase(testRun);
        // Don't set any JSONB fields

        // Act
        researchPhaseRepository.save(phase);
        ResearchPhase loaded =
                researchPhaseRepository.findByRunId(testRun.getId()).orElseThrow();

        // Assert
        assertThat(loaded.getCandidates()).isNull();
        assertThat(loaded.getSources()).isNull();
        assertThat(loaded.getToolCalls()).isNull();
    }

    @Test
    @DisplayName("Should default guardrail outcome columns to first_try / 1 / null")
    void shouldDefaultGuardrailOutcomeColumns() {
        ResearchPhase phase = new ResearchPhase(testRun);
        researchPhaseRepository.save(phase);
        ResearchPhase loaded =
                researchPhaseRepository.findByRunId(testRun.getId()).orElseThrow();

        assertThat(loaded.getGuardrailAttempts()).isEqualTo(1);
        assertThat(loaded.getGuardrailOutcome()).isEqualTo("first_try");
        assertThat(loaded.getGuardrailIssues()).isNull();
    }

    @Test
    @DisplayName("Should round-trip recovered guardrail outcome with JSONB issues array")
    void shouldRoundTripRecoveredGuardrailOutcome() {
        ResearchPhase phase = new ResearchPhase(testRun);
        phase.setGuardrailAttempts(2);
        phase.setGuardrailOutcome("recovered");
        phase.setGuardrailIssues(List.of("fake_url", "empty_candidates"));

        researchPhaseRepository.save(phase);
        ResearchPhase loaded =
                researchPhaseRepository.findByRunId(testRun.getId()).orElseThrow();

        assertThat(loaded.getGuardrailAttempts()).isEqualTo(2);
        assertThat(loaded.getGuardrailOutcome()).isEqualTo("recovered");
        assertThat(loaded.getGuardrailIssues()).containsExactly("fake_url", "empty_candidates");
    }

    @Test
    @DisplayName("Should round-trip guardrail_failed_output JSONB with ResearchResponse-shaped payload")
    void shouldRoundTripGuardrailFailedOutput() {
        // Representative payload mirroring a ResearchResponse the Market Analyst
        // might have produced that got flagged — candidates list, web sources,
        // summary string — so the JSONB serializer is exercised end-to-end.
        Map<String, Object> failedOutput = Map.of(
                "summary",
                "Banks look strong this quarter.",
                "candidates",
                List.of(Map.of("symbol", "JPM", "price", 195.42), Map.of("symbol", "BAC", "price", 38.10)),
                "webSources",
                List.of(Map.of("title", "WSJ Banks Report", "url", "https://example.com/wsj")),
                "portfolio_context",
                "Cash heavy, no bank exposure.");

        ResearchPhase phase = new ResearchPhase(testRun);
        phase.setGuardrailAttempts(2);
        phase.setGuardrailOutcome("recovered");
        phase.setGuardrailIssues(List.of("fake_url"));
        phase.setGuardrailFailedOutput(failedOutput);

        researchPhaseRepository.save(phase);
        ResearchPhase loaded =
                researchPhaseRepository.findByRunId(testRun.getId()).orElseThrow();

        Map<String, Object> loadedOutput = loaded.getGuardrailFailedOutput();
        assertThat(loadedOutput).isNotNull();
        assertThat(loadedOutput.get("summary")).isEqualTo("Banks look strong this quarter.");
        assertThat(loadedOutput.get("portfolio_context")).isEqualTo("Cash heavy, no bank exposure.");
        assertThat(loadedOutput.get("candidates")).isInstanceOf(List.class);
        assertThat(loadedOutput.get("webSources")).isInstanceOf(List.class);
    }

    @Test
    @DisplayName("Should default guardrail_failed_output to null")
    void shouldDefaultGuardrailFailedOutputToNull() {
        ResearchPhase phase = new ResearchPhase(testRun);
        researchPhaseRepository.save(phase);
        ResearchPhase loaded =
                researchPhaseRepository.findByRunId(testRun.getId()).orElseThrow();

        assertThat(loaded.getGuardrailFailedOutput()).isNull();
    }
}
