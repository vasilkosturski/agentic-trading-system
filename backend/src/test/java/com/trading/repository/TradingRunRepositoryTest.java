package com.trading.repository;

import com.trading.entity.TradingAgent;
import com.trading.entity.TradingRun;
import com.trading.enums.RunPhase;
import com.trading.enums.RunStatus;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Repository tests for TradingRun entity.
 * Tests CRUD operations and custom queries with real PostgreSQL.
 */
@DisplayName("TradingRunRepository Tests")
class TradingRunRepositoryTest extends BaseRepositoryTest {

    @Autowired
    private TradingRunRepository tradingRunRepository;

    @Autowired
    private TradingAgentRepository tradingAgentRepository;

    private TradingAgent testAgent;

    @BeforeEach
    void setUp() {
        // Clean up
        tradingRunRepository.deleteAll();
        tradingAgentRepository.deleteAll();
        
        // Create test agent
        testAgent = new TradingAgent("TestAgent", "Test trading agent for repository tests");
        testAgent.setInitialCapital(100000.0);
        testAgent = tradingAgentRepository.save(testAgent);
    }

    @Test
    @DisplayName("Should save and retrieve TradingRun")
    void shouldSaveAndRetrieveTradingRun() {
        // Arrange
        TradingRun run = new TradingRun(testAgent);
        
        // Act
        TradingRun saved = tradingRunRepository.save(run);
        Optional<TradingRun> found = tradingRunRepository.findById(saved.getId());
        
        // Assert
        assertThat(found).isPresent();
        assertThat(found.get().getAgent().getId()).isEqualTo(testAgent.getId());
        assertThat(found.get().getStatus()).isEqualTo(RunStatus.IN_PROGRESS);
        assertThat(found.get().getPhase()).isEqualTo(RunPhase.INITIALIZING);
        assertThat(found.get().getStartedAt()).isNotNull();
    }

    @Test
    @DisplayName("Should find runs by agent ID ordered by started_at desc")
    void shouldFindByAgentIdOrderByStartedAtDesc() throws InterruptedException {
        // Arrange - create multiple runs with slight delay to ensure different timestamps
        TradingRun run1 = new TradingRun(testAgent);
        tradingRunRepository.save(run1);
        
        Thread.sleep(10); // Small delay to ensure different timestamps
        
        TradingRun run2 = new TradingRun(testAgent);
        tradingRunRepository.save(run2);
        
        Thread.sleep(10);
        
        TradingRun run3 = new TradingRun(testAgent);
        tradingRunRepository.save(run3);
        
        // Act
        List<TradingRun> runs = tradingRunRepository.findByAgentIdOrderByStartedAtDesc(testAgent.getId());
        
        // Assert
        assertThat(runs).hasSize(3);
        // Most recent first
        assertThat(runs.get(0).getId()).isEqualTo(run3.getId());
        assertThat(runs.get(1).getId()).isEqualTo(run2.getId());
        assertThat(runs.get(2).getId()).isEqualTo(run1.getId());
    }

    @Test
    @DisplayName("Should find runs by agent ID and status")
    void shouldFindByAgentIdAndStatus() {
        // Arrange
        TradingRun run1 = new TradingRun(testAgent);
        run1 = tradingRunRepository.save(run1);
        
        TradingRun run2 = new TradingRun(testAgent);
        run2.markAsCompleted();
        tradingRunRepository.save(run2);
        
        TradingRun run3 = new TradingRun(testAgent);
        run3.markAsError("Test error");
        tradingRunRepository.save(run3);
        
        // Act
        List<TradingRun> inProgressRuns = tradingRunRepository.findByAgentIdAndStatus(testAgent.getId(), RunStatus.IN_PROGRESS);
        List<TradingRun> completedRuns = tradingRunRepository.findByAgentIdAndStatus(testAgent.getId(), RunStatus.COMPLETED);
        List<TradingRun> failedRuns = tradingRunRepository.findByAgentIdAndStatus(testAgent.getId(), RunStatus.FAILED);
        
        // Assert
        assertThat(inProgressRuns).hasSize(1);
        assertThat(completedRuns).hasSize(1);
        assertThat(failedRuns).hasSize(1);
    }

    @Test
    @DisplayName("Should find active run by agent ID")
    void shouldFindActiveRunByAgentId() {
        // Arrange
        TradingRun completedRun = new TradingRun(testAgent);
        completedRun.markAsCompleted();
        tradingRunRepository.save(completedRun);
        
        TradingRun activeRun = new TradingRun(testAgent);
        activeRun.updatePhase(RunPhase.RESEARCHING);
        tradingRunRepository.save(activeRun);

        // Act
        Optional<TradingRun> found = tradingRunRepository.findActiveRunByAgentId(testAgent.getId());

        // Assert
        assertThat(found).isPresent();
        assertThat(found.get().getPhase()).isEqualTo(RunPhase.RESEARCHING);
    }

    @Test
    @DisplayName("Should return empty when no active run exists")
    void shouldReturnEmptyWhenNoActiveRun() {
        // Arrange
        TradingRun completedRun = new TradingRun(testAgent);
        completedRun.markAsCompleted();
        tradingRunRepository.save(completedRun);
        
        // Act
        Optional<TradingRun> found = tradingRunRepository.findActiveRunByAgentId(testAgent.getId());
        
        // Assert
        assertThat(found).isEmpty();
    }

    @Test
    @DisplayName("Should count runs by agent ID and status")
    void shouldCountByAgentIdAndStatus() {
        // Arrange
        for (int i = 0; i < 3; i++) {
            TradingRun run = new TradingRun(testAgent);
            run.markAsCompleted();
            tradingRunRepository.save(run);
        }
        
        TradingRun failedRun = new TradingRun(testAgent);
        failedRun.markAsError("Error");
        tradingRunRepository.save(failedRun);
        
        // Act
        Long completedCount = tradingRunRepository.countByAgentIdAndStatus(testAgent.getId(), RunStatus.COMPLETED);
        Long failedCount = tradingRunRepository.countByAgentIdAndStatus(testAgent.getId(), RunStatus.FAILED);
        
        // Assert
        assertThat(completedCount).isEqualTo(3);
        assertThat(failedCount).isEqualTo(1);
    }

    @Test
    @DisplayName("Should update phase correctly")
    void shouldUpdatePhaseCorrectly() {
        // Arrange
        TradingRun run = new TradingRun(testAgent);
        run = tradingRunRepository.save(run);
        
        // Act - simulate phase progression
        run.updatePhase(RunPhase.RESEARCHING);
        tradingRunRepository.save(run);

        run.updatePhase(RunPhase.DECIDING);
        tradingRunRepository.save(run);

        run.updatePhase(RunPhase.TRADING);
        tradingRunRepository.save(run);

        run.updatePhase(RunPhase.COMPLETED);
        TradingRun finalRun = tradingRunRepository.save(run);

        // Assert
        TradingRun loaded = tradingRunRepository.findById(finalRun.getId()).orElseThrow();
        assertThat(loaded.getPhase()).isEqualTo(RunPhase.COMPLETED);
        assertThat(loaded.getStatus()).isEqualTo(RunStatus.COMPLETED);
        assertThat(loaded.getCompletedAt()).isNotNull();
    }
}

