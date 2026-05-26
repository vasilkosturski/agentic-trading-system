package com.trading.repository;

import com.trading.entity.AccountTransaction;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.entity.TransactionType;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Repository tests for AccountTransaction date-range filtering.
 * Pins inclusive/exclusive boundary semantics of
 * findByAccountIdAndSymbolAndTimestampBetween — exclusive on both ends.
 */
@DisplayName("AccountTransactionRepository Date-Range Tests")
class AccountTransactionRepositoryTest extends BaseRepositoryTest {

    @Autowired
    private AccountTransactionRepository accountTransactionRepository;

    @Autowired
    private TradingAccountRepository tradingAccountRepository;

    @Autowired
    private TradingAgentRepository tradingAgentRepository;

    private TradingAccount accountA;
    private TradingAccount accountB;

    private static final String SYMBOL = "AAPL";
    private static final String OTHER_SYMBOL = "GOOGL";

    private Instant since;
    private Instant cutoffDate;

    @BeforeEach
    void setUp() {
        accountTransactionRepository.deleteAll();
        tradingAccountRepository.deleteAll();
        tradingAgentRepository.deleteAll();

        TradingAgent agentA = new TradingAgent("AgentA", "Test agent A");
        agentA.setInitialCapital(100000.0);
        agentA = tradingAgentRepository.save(agentA);

        TradingAgent agentB = new TradingAgent("AgentB", "Test agent B");
        agentB.setInitialCapital(100000.0);
        agentB = tradingAgentRepository.save(agentB);

        accountA = new TradingAccount(agentA, 100000.0);
        accountA = tradingAccountRepository.save(accountA);

        accountB = new TradingAccount(agentB, 100000.0);
        accountB = tradingAccountRepository.save(accountB);

        Instant now = Instant.now();
        since = now.minus(30, ChronoUnit.DAYS);
        cutoffDate = now.minus(7, ChronoUnit.DAYS);
    }

    private AccountTransaction persistTxn(TradingAccount account, String symbol, Instant timestamp) {
        AccountTransaction txn = new AccountTransaction(account, symbol, 10, 150.0, timestamp);
        txn.setTransactionType(TransactionType.BUY);
        return accountTransactionRepository.save(txn);
    }

    @Test
    @DisplayName("Includes txn just after 'since' (inclusive low edge)")
    void shouldIncludeTxnJustAfterSince() {
        AccountTransaction inRange = persistTxn(accountA, SYMBOL, since.plusMillis(1));

        List<AccountTransaction> results = accountTransactionRepository
                .findByAccountIdAndSymbolAndTimestampBetween(accountA.getId(), SYMBOL, since, cutoffDate);

        assertThat(results).extracting(AccountTransaction::getId).containsExactly(inRange.getId());
    }

    @Test
    @DisplayName("Excludes txn at exactly 'since' (exclusive low edge)")
    void shouldExcludeTxnAtExactlySince() {
        persistTxn(accountA, SYMBOL, since);

        List<AccountTransaction> results = accountTransactionRepository
                .findByAccountIdAndSymbolAndTimestampBetween(accountA.getId(), SYMBOL, since, cutoffDate);

        assertThat(results).isEmpty();
    }

    @Test
    @DisplayName("Includes txn just before 'cutoffDate' (inclusive high edge)")
    void shouldIncludeTxnJustBeforeCutoff() {
        AccountTransaction inRange = persistTxn(accountA, SYMBOL, cutoffDate.minusMillis(1));

        List<AccountTransaction> results = accountTransactionRepository
                .findByAccountIdAndSymbolAndTimestampBetween(accountA.getId(), SYMBOL, since, cutoffDate);

        assertThat(results).extracting(AccountTransaction::getId).containsExactly(inRange.getId());
    }

    @Test
    @DisplayName("Excludes txn at exactly 'cutoffDate' (exclusive high edge)")
    void shouldExcludeTxnAtExactlyCutoff() {
        persistTxn(accountA, SYMBOL, cutoffDate);

        List<AccountTransaction> results = accountTransactionRepository
                .findByAccountIdAndSymbolAndTimestampBetween(accountA.getId(), SYMBOL, since, cutoffDate);

        assertThat(results).isEmpty();
    }

    @Test
    @DisplayName("Filters out txns with other symbols")
    void shouldFilterBySymbol() {
        Instant inRangeTime = since.plus(10, ChronoUnit.DAYS);
        AccountTransaction matching = persistTxn(accountA, SYMBOL, inRangeTime);
        persistTxn(accountA, OTHER_SYMBOL, inRangeTime);

        List<AccountTransaction> results = accountTransactionRepository
                .findByAccountIdAndSymbolAndTimestampBetween(accountA.getId(), SYMBOL, since, cutoffDate);

        assertThat(results).extracting(AccountTransaction::getId).containsExactly(matching.getId());
    }

    @Test
    @DisplayName("Filters out txns belonging to other accounts")
    void shouldFilterByAccount() {
        Instant inRangeTime = since.plus(10, ChronoUnit.DAYS);
        AccountTransaction matching = persistTxn(accountA, SYMBOL, inRangeTime);
        persistTxn(accountB, SYMBOL, inRangeTime);

        List<AccountTransaction> results = accountTransactionRepository
                .findByAccountIdAndSymbolAndTimestampBetween(accountA.getId(), SYMBOL, since, cutoffDate);

        assertThat(results).extracting(AccountTransaction::getId).containsExactly(matching.getId());
    }

    @Test
    @DisplayName("Returns results ordered by timestamp DESC")
    void shouldOrderByTimestampDescending() {
        Instant oldest = since.plus(1, ChronoUnit.DAYS);
        Instant middle = since.plus(10, ChronoUnit.DAYS);
        Instant newest = since.plus(20, ChronoUnit.DAYS);

        AccountTransaction t1 = persistTxn(accountA, SYMBOL, oldest);
        AccountTransaction t2 = persistTxn(accountA, SYMBOL, middle);
        AccountTransaction t3 = persistTxn(accountA, SYMBOL, newest);

        List<AccountTransaction> results = accountTransactionRepository
                .findByAccountIdAndSymbolAndTimestampBetween(accountA.getId(), SYMBOL, since, cutoffDate);

        assertThat(results)
                .extracting(AccountTransaction::getId)
                .containsExactly(t3.getId(), t2.getId(), t1.getId());
    }
}
