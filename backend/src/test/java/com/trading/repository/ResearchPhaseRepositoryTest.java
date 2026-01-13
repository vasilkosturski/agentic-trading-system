package com.trading.repository;

import com.trading.dto.jsonb.ResearchToolCallDto;
import com.trading.dto.jsonb.SourceDto;
import com.trading.entity.ResearchPhase;
import com.trading.entity.TradingAgent;
import com.trading.entity.TradingRun;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

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
        phase.setTokensUsed(1500);
        phase.setLatencyMs(2500L);
        phase.setCostUsd(new BigDecimal("0.000225"));
        
        // Act
        ResearchPhase saved = researchPhaseRepository.save(phase);
        Optional<ResearchPhase> found = researchPhaseRepository.findById(saved.getId());
        
        // Assert
        assertThat(found).isPresent();
        assertThat(found.get().getResearchNotes()).isEqualTo("Market analysis complete");
        assertThat(found.get().getTokensUsed()).isEqualTo(1500);
        assertThat(found.get().getLatencyMs()).isEqualTo(2500L);
        assertThat(found.get().getCostUsd()).isEqualByComparingTo(new BigDecimal("0.000225"));
    }

    @Test
    @DisplayName("Should round-trip candidates JSONB list")
    void shouldRoundTripCandidatesJsonb() {
        // Arrange
        ResearchPhase phase = new ResearchPhase(testRun);
        phase.setCandidates(List.of("JPM", "BAC", "WFC", "GS"));
        
        // Act
        researchPhaseRepository.save(phase);
        ResearchPhase loaded = researchPhaseRepository.findByRunId(testRun.getId()).orElseThrow();
        
        // Assert
        assertThat(loaded.getCandidates())
            .containsExactly("JPM", "BAC", "WFC", "GS");
    }

    @Test
    @DisplayName("Should round-trip sources JSONB list")
    void shouldRoundTripSourcesJsonb() {
        // Arrange
        ResearchPhase phase = new ResearchPhase(testRun);
        
        SourceDto webSource = new SourceDto();
        webSource.setType("web");
        webSource.setTitle("Market Analysis Report");
        webSource.setUrl("https://example.com/report");
        webSource.setDescription("Comprehensive market analysis");
        
        SourceDto systemSource = new SourceDto();
        systemSource.setType("system_context");
        systemSource.setDescription("Current portfolio state");
        
        phase.setSources(List.of(webSource, systemSource));
        
        // Act
        researchPhaseRepository.save(phase);
        ResearchPhase loaded = researchPhaseRepository.findByRunId(testRun.getId()).orElseThrow();
        
        // Assert
        assertThat(loaded.getSources()).hasSize(2);
        
        SourceDto loadedWebSource = loaded.getSources().get(0);
        assertThat(loadedWebSource.getType()).isEqualTo("web");
        assertThat(loadedWebSource.getTitle()).isEqualTo("Market Analysis Report");
        assertThat(loadedWebSource.getUrl()).isEqualTo("https://example.com/report");
        
        SourceDto loadedSystemSource = loaded.getSources().get(1);
        assertThat(loadedSystemSource.getType()).isEqualTo("system_context");
        assertThat(loadedSystemSource.getDescription()).isEqualTo("Current portfolio state");
    }

    @Test
    @DisplayName("Should round-trip tool_calls JSONB list")
    void shouldRoundTripToolCallsJsonb() {
        // Arrange
        ResearchPhase phase = new ResearchPhase(testRun);
        
        ResearchToolCallDto toolCall1 = new ResearchToolCallDto();
        toolCall1.setTool("brave_search");
        toolCall1.setDurationMs(1200L);
        
        ResearchToolCallDto toolCall2 = new ResearchToolCallDto();
        toolCall2.setTool("memory_search");
        toolCall2.setDurationMs(50L);
        
        phase.setToolCalls(List.of(toolCall1, toolCall2));
        
        // Act
        researchPhaseRepository.save(phase);
        ResearchPhase loaded = researchPhaseRepository.findByRunId(testRun.getId()).orElseThrow();
        
        // Assert
        assertThat(loaded.getToolCalls()).hasSize(2);
        
        ResearchToolCallDto loadedCall1 = loaded.getToolCalls().get(0);
        assertThat(loadedCall1.getTool()).isEqualTo("brave_search");
        assertThat(loadedCall1.getDurationMs()).isEqualTo(1200L);
        
        ResearchToolCallDto loadedCall2 = loaded.getToolCalls().get(1);
        assertThat(loadedCall2.getTool()).isEqualTo("memory_search");
        assertThat(loadedCall2.getDurationMs()).isEqualTo(50L);
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
        ResearchPhase loaded = researchPhaseRepository.findByRunId(testRun.getId()).orElseThrow();
        
        // Assert
        assertThat(loaded.getCandidates()).isNull();
        assertThat(loaded.getSources()).isNull();
        assertThat(loaded.getToolCalls()).isNull();
    }
}

