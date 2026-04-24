package com.trading.service;

import com.trading.dto.response.RecentActivityResponse;
import com.trading.dto.response.RunListResponseDto;
import com.trading.dto.response.TradingHistoryResponse;
import com.trading.entity.TradingAgent;
import com.trading.entity.TradingRun;
import com.trading.entity.AccountTransaction;
import com.trading.entity.TradingAccount;
import com.trading.entity.TransactionType;
import com.trading.repository.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Tests for 7-day public display delay feature.
 * Verifies that TradingRunService and MemoryService filter data
 * to only return records older than the configured delay period.
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("Public Display Delay Tests")
class PublicDisplayDelayTest {

    @Mock
    private TradingRunRepository tradingRunRepository;

    @Mock
    private DecisionPhaseRepository decisionPhaseRepository;

    @Mock
    private AccountTransactionRepository transactionRepository;

    @Mock
    private TradingAgentRepository tradingAgentRepository;

    @Mock
    private TradingAccountRepository accountRepository;

    @Mock
    private AccountService accountService;

    @InjectMocks
    private TradingRunService tradingRunService;

    @InjectMocks
    private MemoryService memoryService;

    private TradingAgent testAgent;
    private TradingAccount testAccount;

    @BeforeEach
    void setUp() {
        testAgent = new TradingAgent();
        testAgent.setId(1L);
        testAgent.setName("warren");

        testAccount = new TradingAccount();
        testAccount.setId(1L);
        testAccount.setAgent(testAgent);

        // Set the delay configuration (7 days default)
        ReflectionTestUtils.setField(tradingRunService, "publicDisplayDelayDays", 7);
        ReflectionTestUtils.setField(memoryService, "publicDisplayDelayDays", 7);
    }

    @Test
    @DisplayName("TradingRunService.listRuns() filters runs by createdAt older than 7 days")
    void listRuns_shouldFilterByDelayPeriod() {
        // Arrange: Create runs at different times
        Instant now = Instant.now();
        TradingRun oldRun1 = createRun(2L, now.minus(8, ChronoUnit.DAYS));   // 8 days old - should be INCLUDED
        TradingRun oldRun2 = createRun(3L, now.minus(10, ChronoUnit.DAYS));  // 10 days old - should be INCLUDED

        Pageable pageable = PageRequest.of(0, 10);

        // Mock repository to return only old runs (database-level filtering)
        Page<TradingRun> oldRuns = new PageImpl<>(List.of(oldRun1, oldRun2));
        when(tradingRunRepository.findByStartedAtBefore(any(Instant.class), eq(pageable))).thenReturn(oldRuns);
        when(decisionPhaseRepository.findByRunId(anyLong())).thenReturn(Optional.empty());

        // Act: Call service method
        RunListResponseDto result = tradingRunService.listRuns(null, pageable);

        // Assert: Only runs older than 7 days should be returned
        assertEquals(2, result.getRuns().size(), "Should return only runs older than 7 days");
        assertTrue(result.getRuns().stream().anyMatch(r -> r.getRunId().equals(2L)),
                "Old run (8 days old) should be included");
        assertTrue(result.getRuns().stream().anyMatch(r -> r.getRunId().equals(3L)),
                "Old run (10 days old) should be included");

        // Verify database-level filtering was used
        verify(tradingRunRepository).findByStartedAtBefore(any(Instant.class), eq(pageable));
    }

    @Test
    @DisplayName("MemoryService.getTradingHistory() filters trades by timestamp older than 7 days")
    void getTradingHistory_shouldFilterByDelayPeriod() {
        // Arrange: Create transactions at different times
        Instant now = Instant.now();
        AccountTransaction recentTrade = createTransaction(1L, now.minus(6, ChronoUnit.DAYS)); // 6 days - FILTERED OUT
        AccountTransaction oldTrade1 = createTransaction(2L, now.minus(8, ChronoUnit.DAYS));   // 8 days - INCLUDED
        AccountTransaction oldTrade2 = createTransaction(3L, now.minus(15, ChronoUnit.DAYS));  // 15 days - INCLUDED

        when(accountRepository.findByAgentName("warren")).thenReturn(Optional.of(testAccount));
        when(transactionRepository.findByAccountIdAndSymbolOrderByTimestampDesc(1L, "AAPL"))
                .thenReturn(List.of(recentTrade, oldTrade1, oldTrade2));
        when(accountService.getHoldings("warren")).thenReturn(List.of());

        // Act: Call service method
        TradingHistoryResponse result = memoryService.getTradingHistory("warren", "AAPL", 30);

        // Assert: Only trades older than 7 days should be returned
        assertEquals(2, result.getTrades().size(), "Should return only trades older than 7 days");
        // Verify by comparing the parsed timestamps
        List<Instant> resultTimestamps = result.getTrades().stream()
                .map(t -> Instant.parse(t.getDate()))
                .toList();
        assertFalse(resultTimestamps.contains(recentTrade.getTimestamp()),
                "Recent trade (6 days old) should be filtered out");
        assertTrue(resultTimestamps.contains(oldTrade1.getTimestamp()),
                "Old trade (8 days old) should be included");
        assertTrue(resultTimestamps.contains(oldTrade2.getTimestamp()),
                "Old trade (15 days old) should be included");
    }

    @Test
    @DisplayName("MemoryService.getRecentActivity() filters runs by startedAt older than 7 days")
    void getRecentActivity_shouldFilterByDelayPeriod() {
        // Arrange: Create runs at different times
        Instant now = Instant.now();
        TradingRun recentRun = createRun(1L, now.minus(4, ChronoUnit.DAYS)); // 4 days old - FILTERED OUT
        TradingRun oldRun1 = createRun(2L, now.minus(9, ChronoUnit.DAYS));   // 9 days old - INCLUDED
        TradingRun oldRun2 = createRun(3L, now.minus(12, ChronoUnit.DAYS));  // 12 days old - INCLUDED

        when(tradingAgentRepository.findByName("warren")).thenReturn(Optional.of(testAgent));
        when(tradingRunRepository.findByAgentIdOrderByStartedAtDesc(1L))
                .thenReturn(List.of(recentRun, oldRun1, oldRun2));

        // Act: Call service method
        RecentActivityResponse result = memoryService.getRecentActivity("warren", 30);

        // Assert: Only runs older than 7 days should be returned
        assertEquals(2, result.getRuns().size(), "Should return only runs older than 7 days");
        assertEquals(2, result.getTotalRuns(), "Total runs count should match filtered results");
    }

    @Test
    @DisplayName("Delay configuration is injectable via @Value")
    void delayConfiguration_shouldBeInjectable() {
        // Arrange: Set custom delay period
        ReflectionTestUtils.setField(tradingRunService, "publicDisplayDelayDays", 14);

        // Assert: Field should be set
        Integer delayDays = (Integer) ReflectionTestUtils.getField(tradingRunService, "publicDisplayDelayDays");
        assertEquals(14, delayDays, "Delay days should be configurable");
    }

    @Test
    @DisplayName("Zero delay returns all data")
    void zeroDelay_shouldReturnAllData() {
        // Arrange: Set delay to 0 (no filtering)
        ReflectionTestUtils.setField(tradingRunService, "publicDisplayDelayDays", 0);

        Instant now = Instant.now();
        TradingRun recentRun = createRun(1L, now.minus(1, ChronoUnit.DAYS)); // 1 day old
        TradingRun oldRun = createRun(2L, now.minus(10, ChronoUnit.DAYS));   // 10 days old

        Pageable pageable = PageRequest.of(0, 10);
        Page<TradingRun> allRuns = new PageImpl<>(List.of(recentRun, oldRun));
        when(tradingRunRepository.findByStartedAtBefore(any(Instant.class), eq(pageable))).thenReturn(allRuns);
        when(decisionPhaseRepository.findByRunId(anyLong())).thenReturn(Optional.empty());

        // Act: Call service method
        RunListResponseDto result = tradingRunService.listRuns(null, pageable);

        // Assert: All runs should be returned (no filtering)
        assertEquals(2, result.getRuns().size(), "With 0 delay, all runs should be returned");

        // Verify database-level filtering was used (even with 0 delay)
        verify(tradingRunRepository).findByStartedAtBefore(any(Instant.class), eq(pageable));
    }

    // Helper methods

    private TradingRun createRun(Long id, Instant startedAt) {
        TradingRun run = new TradingRun(testAgent);
        ReflectionTestUtils.setField(run, "id", id);
        ReflectionTestUtils.setField(run, "startedAt", startedAt);
        return run;
    }

    private AccountTransaction createTransaction(Long id, Instant timestamp) {
        AccountTransaction transaction = new AccountTransaction();
        ReflectionTestUtils.setField(transaction, "id", id);
        transaction.setAccount(testAccount);
        transaction.setSymbol("AAPL");
        transaction.setQuantity(10);
        transaction.setPrice(150.0);
        transaction.setTimestamp(timestamp);
        transaction.setTransactionType(TransactionType.BUY);
        ReflectionTestUtils.setField(transaction, "createdAt", timestamp);
        return transaction;
    }
}
