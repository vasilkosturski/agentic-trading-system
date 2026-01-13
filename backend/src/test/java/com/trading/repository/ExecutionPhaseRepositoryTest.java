package com.trading.repository;

import com.trading.entity.*;
import com.trading.enums.PhaseStatus;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Repository tests for ExecutionPhase entity.
 * Tests FK relationships (decision_id, trade_id) with real PostgreSQL.
 */
@DisplayName("ExecutionPhaseRepository Tests")
class ExecutionPhaseRepositoryTest extends BaseRepositoryTest {

    @Autowired
    private ExecutionPhaseRepository executionPhaseRepository;

    @Autowired
    private DecisionPhaseRepository decisionPhaseRepository;

    @Autowired
    private TradingRunRepository tradingRunRepository;

    @Autowired
    private TradingAgentRepository tradingAgentRepository;

    @Autowired
    private TradingAccountRepository tradingAccountRepository;

    @Autowired
    private AccountTransactionRepository accountTransactionRepository;

    @Autowired
    private AgentRunRepository agentRunRepository;

    private TradingRun testRun;
    private DecisionPhase testDecision;
    private TradingAccount testAccount;
    private AgentRun testAgentRun; // Old entity - needed for AccountTransaction FK

    @BeforeEach
    void setUp() {
        // Clean up (order matters due to FKs)
        executionPhaseRepository.deleteAll();
        accountTransactionRepository.deleteAll();
        decisionPhaseRepository.deleteAll();
        tradingRunRepository.deleteAll();
        agentRunRepository.deleteAll(); // Old entity cleanup
        tradingAccountRepository.deleteAll();
        tradingAgentRepository.deleteAll();
        
        // Create test agent
        TradingAgent agent = new TradingAgent("TestAgent", "Test agent");
        agent.setInitialCapital(100000.0);
        agent = tradingAgentRepository.save(agent);
        
        // Create test account
        testAccount = new TradingAccount(agent, 100000.0);
        testAccount = tradingAccountRepository.save(testAccount);
        
        // Create old AgentRun (needed for AccountTransaction FK until migration complete)
        testAgentRun = new AgentRun(agent.getName(), "TRADING", "{}");
        testAgentRun.markAsTraded("Test trade", "Full reasoning", "[]", "{}", 1);
        testAgentRun = agentRunRepository.save(testAgentRun);
        
        // Create test run (new entity)
        testRun = new TradingRun(agent);
        testRun = tradingRunRepository.save(testRun);
        
        // Create test decision
        testDecision = new DecisionPhase(testRun);
        testDecision.setDecision(TradeDecision.BUY);
        testDecision.setSymbol("JPM");
        testDecision.setQuantity(10);
        testDecision = decisionPhaseRepository.save(testDecision);
    }

    @Test
    @DisplayName("Should save executed phase with trade FK")
    void shouldSaveExecutedPhaseWithTradeFk() {
        // Arrange - create a transaction (requires old AgentRun FK until migration)
        AccountTransaction trade = new AccountTransaction(
            testAccount, "JPM", 10, 150.0, java.time.Instant.now()
        );
        trade.setAgentRun(testAgentRun);
        trade.setTransactionType(TransactionType.BUY);
        trade = accountTransactionRepository.save(trade);
        
        ExecutionPhase phase = new ExecutionPhase(testRun, testDecision, trade);
        
        // Act
        ExecutionPhase saved = executionPhaseRepository.save(phase);
        Optional<ExecutionPhase> found = executionPhaseRepository.findById(saved.getId());
        
        // Assert
        assertThat(found).isPresent();
        assertThat(found.get().getStatus()).isEqualTo(PhaseStatus.COMPLETED);
        assertThat(found.get().isExecuted()).isTrue();
        assertThat(found.get().getTrade()).isNotNull();
        assertThat(found.get().getTrade().getId()).isEqualTo(trade.getId());
        assertThat(found.get().getDecision()).isNotNull();
        assertThat(found.get().getDecision().getId()).isEqualTo(testDecision.getId());
    }

    @Test
    @DisplayName("Should save failed phase with error details")
    void shouldSaveFailedPhaseWithErrorDetails() {
        // Arrange
        String errorMessage = "Insufficient funds: need $4500.00, have $2000.00";
        ExecutionPhase phase = new ExecutionPhase(testRun, testDecision, errorMessage);
        
        // Act
        executionPhaseRepository.save(phase);
        ExecutionPhase loaded = executionPhaseRepository.findByRunId(testRun.getId()).orElseThrow();
        
        // Assert
        assertThat(loaded.getStatus()).isEqualTo(PhaseStatus.FAILED);
        assertThat(loaded.isFailed()).isTrue();
        assertThat(loaded.getErrorDetails()).isEqualTo(errorMessage);
        assertThat(loaded.getTrade()).isNull();
        assertThat(loaded.getDecision()).isNotNull();
    }

    @Test
    @DisplayName("Should save skipped phase for HOLD decision")
    void shouldSaveSkippedPhaseForHoldDecision() {
        // Arrange
        ExecutionPhase phase = new ExecutionPhase(testRun);
        
        // Act
        executionPhaseRepository.save(phase);
        ExecutionPhase loaded = executionPhaseRepository.findByRunId(testRun.getId()).orElseThrow();
        
        // Assert
        assertThat(loaded.getStatus()).isEqualTo(PhaseStatus.SKIPPED);
        assertThat(loaded.isSkipped()).isTrue();
        assertThat(loaded.getErrorDetails()).isNull(); // HOLD is not an error - errorDetails should be null
        assertThat(loaded.getTrade()).isNull();
        assertThat(loaded.getDecision()).isNull(); // Skipped constructor doesn't set decision
    }

    @Test
    @DisplayName("Should find by run ID")
    void shouldFindByRunId() {
        // Arrange
        ExecutionPhase phase = new ExecutionPhase(testRun, testDecision, "Test error");
        executionPhaseRepository.save(phase);
        
        // Act
        Optional<ExecutionPhase> found = executionPhaseRepository.findByRunId(testRun.getId());

        // Assert
        assertThat(found).isPresent();
        assertThat(found.get().getStatus()).isEqualTo(PhaseStatus.FAILED);
    }

    @Test
    @DisplayName("Should find by decision ID")
    void shouldFindByDecisionId() {
        // Arrange (requires old AgentRun FK until migration)
        AccountTransaction trade = new AccountTransaction(
            testAccount, "JPM", 10, 150.0, java.time.Instant.now()
        );
        trade.setAgentRun(testAgentRun);
        trade.setTransactionType(TransactionType.BUY);
        trade = accountTransactionRepository.save(trade);
        
        ExecutionPhase phase = new ExecutionPhase(testRun, testDecision, trade);
        executionPhaseRepository.save(phase);
        
        // Act
        Optional<ExecutionPhase> found = executionPhaseRepository.findByDecisionId(testDecision.getId());
        
        // Assert
        assertThat(found).isPresent();
        assertThat(found.get().getDecision().getId()).isEqualTo(testDecision.getId());
    }

    @Test
    @DisplayName("Should check existence by run ID")
    void shouldCheckExistsByRunId() {
        // Arrange
        ExecutionPhase phase = new ExecutionPhase(testRun);
        executionPhaseRepository.save(phase);
        
        // Act & Assert
        assertThat(executionPhaseRepository.existsByRunId(testRun.getId())).isTrue();
        assertThat(executionPhaseRepository.existsByRunId(99999L)).isFalse();
    }

    @Test
    @DisplayName("Should handle null trade_id for failed/skipped")
    void shouldHandleNullTradeId() {
        // Arrange - failed execution (no trade)
        ExecutionPhase phase = new ExecutionPhase(testRun, testDecision, "Trade rejected");
        
        // Act
        executionPhaseRepository.save(phase);
        ExecutionPhase loaded = executionPhaseRepository.findByRunId(testRun.getId()).orElseThrow();
        
        // Assert
        assertThat(loaded.getTrade()).isNull();
        assertThat(loaded.getDecision()).isNotNull();
    }

    @Test
    @DisplayName("Should persist created_at timestamp")
    void shouldPersistCreatedAtTimestamp() {
        // Arrange
        ExecutionPhase phase = new ExecutionPhase(testRun);
        
        // Act
        ExecutionPhase saved = executionPhaseRepository.save(phase);
        ExecutionPhase loaded = executionPhaseRepository.findById(saved.getId()).orElseThrow();
        
        // Assert
        assertThat(loaded.getCreatedAt()).isNotNull();
    }
}

