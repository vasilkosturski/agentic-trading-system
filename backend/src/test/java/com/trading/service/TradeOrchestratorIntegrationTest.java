package com.trading.service;

import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.entity.TradingRun;
import com.trading.enums.RunPhase;
import com.trading.enums.RunStatus;
import com.trading.repository.AccountHoldingRepository;
import com.trading.repository.AccountPortfolioSnapshotRepository;
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.TradingAccountRepository;
import com.trading.repository.TradingAgentRepository;
import com.trading.repository.TradingRunRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import com.trading.testsupport.SharedPostgresContainer;

import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.timeout;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

/**
 * Integration tests for {@link TradeOrchestrator} — verifies that the
 * {@code @Transactional} buy flow composes with the AFTER_COMMIT event listener
 * so that committed trades produce broadcasts and rolled-back trades produce
 * zero effects.
 *
 * <p>The HAPPY PATH proves the full pipeline end-to-end: a successful
 * {@code buyShares} call inserts a transaction row, reduces the account
 * balance, and (after the surrounding transaction commits) fires a broadcast
 * through the leaf {@link SimpMessagingTemplate}.</p>
 *
 * <p>The ROLLBACK PATH is the load-bearing transactional-safety proof: forcing
 * {@link PortfolioSnapshotService#createSnapshot(String)} to throw inside the
 * orchestrator's transaction must (1) roll back the trade row insert performed
 * by {@code BuyTradeExecutor.executeBuy}, (2) roll back the balance update,
 * and (3) prevent any broadcast from firing — verified via
 * {@code verifyNoInteractions(messagingTemplate)}.</p>
 */
@SpringBootTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@DisplayName("TradeOrchestrator integration tests")
class TradeOrchestratorIntegrationTest {

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        SharedPostgresContainer.register(registry);
    }

    @Autowired private TradeOrchestrator tradeOrchestrator;
    @Autowired private TradingAccountRepository accountRepository;
    @Autowired private AccountTransactionRepository transactionRepository;
    @Autowired private AccountHoldingRepository holdingRepository;
    @Autowired private AccountPortfolioSnapshotRepository snapshotRepository;
    @Autowired private TradingAgentRepository agentRepository;
    @Autowired private TradingRunRepository runRepository;

    @MockBean private SimpMessagingTemplate messagingTemplate;
    @MockBean private PortfolioSnapshotService portfolioSnapshotService;
    @MockBean private MarketService marketService;

    private static final String AGENT_NAME = "testagent";
    private static final String SYMBOL = "NVDA";
    private static final double INITIAL_BALANCE = 100_000.0;
    private static final double PRICE = 178.70;

    private TradingAgent agent;
    private TradingAccount account;
    private TradingRun run;

    @BeforeEach
    void setUp() {
        reset(messagingTemplate, portfolioSnapshotService, marketService);

        // Wipe the in-flight test database so each test starts from a known
        // empty state. The shared singleton Testcontainer survives across
        // tests, so we cannot rely on @Transactional rollback (a transactional
        // test wrapper would swallow the orchestrator's commits and defeat the
        // load-bearing rollback assertion). Manual cleanup is the simplest
        // mechanism that preserves the production transaction semantics.
        snapshotRepository.deleteAll();
        transactionRepository.deleteAll();
        holdingRepository.deleteAll();
        runRepository.deleteAll();
        accountRepository.deleteAll();
        agentRepository.deleteAll();

        agent = new TradingAgent(AGENT_NAME, "Integration-test agent");
        agent.setInitialCapital(INITIAL_BALANCE);
        agent = agentRepository.save(agent);

        account = new TradingAccount(agent, INITIAL_BALANCE);
        account = accountRepository.save(account);

        run = new TradingRun(agent);
        run.setStatus(RunStatus.IN_PROGRESS);
        run.setPhase(RunPhase.TRADING);
        run.setStartedAt(Instant.now());
        run = runRepository.save(run);

        when(marketService.getSharePrice(anyString()))
            .thenReturn(new MarketService.PriceData(PRICE, false, Instant.now(), "test"));
    }

    @Test
    @DisplayName("HAPPY PATH: buyShares commits → transaction row inserted, balance reduced, broadcast fired")
    void happyPathCommitsAndBroadcasts() {
        long txnCountBefore = transactionRepository.count();

        var result = tradeOrchestrator.buyShares(AGENT_NAME, SYMBOL, 10, run.getId());

        assertThat(result).isNotNull();
        assertThat(result.symbol()).isEqualTo(SYMBOL);
        assertThat(result.quantity()).isEqualTo(10);

        // Transaction row inserted.
        assertThat(transactionRepository.count()).isEqualTo(txnCountBefore + 1);

        // Balance reduced by trade cost.
        TradingAccount reloaded = accountRepository.findByAgentName(AGENT_NAME).orElseThrow();
        assertThat(reloaded.getBalance()).isLessThan(INITIAL_BALANCE);
        assertThat(reloaded.getBalance()).isEqualTo(INITIAL_BALANCE - (PRICE * 10));

        // Broadcast fires (AFTER_COMMIT, asynchronous via TransactionalEventListener).
        verify(messagingTemplate, timeout(2000)).convertAndSend(any(String.class), any(Object.class));
    }

    @Test
    @DisplayName("ROLLBACK PATH: PortfolioSnapshotService throws → no txn row, no balance change, no broadcast")
    void rollbackProducesZeroEffects() {
        long txnCountBefore = transactionRepository.count();

        // Force a throw INSIDE the @Transactional boundary, AFTER the executor has inserted the trade row.
        doThrow(new RuntimeException("forced rollback for test"))
            .when(portfolioSnapshotService).createSnapshot(anyString());

        assertThatThrownBy(() -> tradeOrchestrator.buyShares(AGENT_NAME, SYMBOL, 10, run.getId()))
            .isInstanceOf(RuntimeException.class)
            .hasMessageContaining("forced rollback");

        // All effects rolled back:
        assertThat(transactionRepository.count()).isEqualTo(txnCountBefore);

        TradingAccount reloaded = accountRepository.findByAgentName(AGENT_NAME).orElseThrow();
        assertThat(reloaded.getBalance()).isEqualTo(INITIAL_BALANCE);

        // AFTER_COMMIT listener never fires because the transaction never commits.
        verifyNoInteractions(messagingTemplate);
    }
}
