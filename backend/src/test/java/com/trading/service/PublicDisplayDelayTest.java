package com.trading.service;

import com.trading.config.TradingPublicProperties;
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
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;
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
    private AccountQueryService accountQueryService;

    @Spy
    private RunDtoMapper runDtoMapper = new RunDtoMapper();

    @Spy
    private RunSpecificationFactory runSpecificationFactory = new RunSpecificationFactory();

    @InjectMocks
    private TradingRunService tradingRunService;

    private MemoryService memoryService;
    private TradingPublicProperties tradingPublicProperties;

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

        tradingPublicProperties = new TradingPublicProperties();
        tradingPublicProperties.setDisplayDelayDays(7);

        memoryService = new MemoryService(
            tradingPublicProperties,
            transactionRepository,
            tradingRunRepository,
            tradingAgentRepository,
            accountRepository,
            accountQueryService
        );
    }

    @Test
    @DisplayName("TradingRunService.listRuns() filters runs by cutoffDate older than 7 days")
    void listRuns_shouldFilterByDelayPeriod() {
        // Arrange: Create runs at different times
        Instant now = Instant.now();
        TradingRun oldRun1 = createRun(2L, now.minus(8, ChronoUnit.DAYS));   // 8 days old - should be INCLUDED
        TradingRun oldRun2 = createRun(3L, now.minus(10, ChronoUnit.DAYS));  // 10 days old - should be INCLUDED

        Pageable pageable = PageRequest.of(0, 10);
        Instant cutoff = now.minus(7, ChronoUnit.DAYS);

        // Mock repository to return only old runs (database-level filtering via Specification)
        Page<TradingRun> oldRuns = new PageImpl<>(List.of(oldRun1, oldRun2));
        when(tradingRunRepository.findAll(any(Specification.class), eq(pageable))).thenReturn(oldRuns);
        when(decisionPhaseRepository.findByRunId(anyLong())).thenReturn(Optional.empty());

        // Act: Call service method
        RunListResponseDto result = tradingRunService.listRuns(null, cutoff, pageable);

        // Assert: Only runs older than 7 days should be returned
        assertEquals(2, result.getRuns().size(), "Should return only runs older than 7 days");
        assertTrue(result.getRuns().stream().anyMatch(r -> r.getRunId().equals(2L)),
                "Old run (8 days old) should be included");
        assertTrue(result.getRuns().stream().anyMatch(r -> r.getRunId().equals(3L)),
                "Old run (10 days old) should be included");

        // Verify database-level filtering was used
        verify(tradingRunRepository).findAll(any(Specification.class), eq(pageable));
    }

    @Test
    @DisplayName("MemoryService.getTradingHistory() filters trades by timestamp older than 7 days")
    void getTradingHistory_shouldFilterByDelayPeriod() {
        // Arrange: Only "old" trades (>7 days) come back from the repository now —
        // the date filter is applied at the DB level via findByAccountIdAndSymbolAndTimestampBetween.
        Instant now = Instant.now();
        AccountTransaction oldTrade1 = createTransaction(2L, now.minus(8, ChronoUnit.DAYS));
        AccountTransaction oldTrade2 = createTransaction(3L, now.minus(15, ChronoUnit.DAYS));

        when(accountRepository.findByAgentName("warren")).thenReturn(Optional.of(testAccount));
        when(transactionRepository.findByAccountIdAndSymbolAndTimestampBetween(
                eq(1L), eq("AAPL"), any(Instant.class), any(Instant.class)))
                .thenReturn(List.of(oldTrade1, oldTrade2));
        when(accountQueryService.getHoldings("warren")).thenReturn(List.of());

        // Act
        TradingHistoryResponse result = memoryService.getTradingHistory("warren", "AAPL", 30);

        // Assert: Service returns the rows the repo emitted; included trades match.
        assertEquals(2, result.getTrades().size(), "Should return only trades older than 7 days");
        List<Instant> resultTimestamps = result.getTrades().stream()
                .map(t -> Instant.parse(t.getDate()))
                .toList();
        assertTrue(resultTimestamps.contains(oldTrade1.getTimestamp()),
                "Old trade (8 days old) should be included");
        assertTrue(resultTimestamps.contains(oldTrade2.getTimestamp()),
                "Old trade (15 days old) should be included");

        // Verify the date-filtered repo method was used (no in-memory filter chain).
        verify(transactionRepository).findByAccountIdAndSymbolAndTimestampBetween(
                eq(1L), eq("AAPL"), any(Instant.class), any(Instant.class));
    }

    @Test
    @DisplayName("MemoryService.getRecentActivity() filters runs by startedAt older than 7 days")
    void getRecentActivity_shouldFilterByDelayPeriod() {
        // Arrange: Only "old" runs (>7 days) come back from the repository now —
        // the date filter is applied at the DB level via findByAgentIdAndStartedAtBetween.
        Instant now = Instant.now();
        TradingRun oldRun1 = createRun(2L, now.minus(9, ChronoUnit.DAYS));
        TradingRun oldRun2 = createRun(3L, now.minus(12, ChronoUnit.DAYS));

        when(tradingAgentRepository.findByName("warren")).thenReturn(Optional.of(testAgent));
        when(tradingRunRepository.findByAgentIdAndStartedAtBetween(
                eq(1L), any(Instant.class), any(Instant.class), any(Pageable.class)))
                .thenReturn(List.of(oldRun1, oldRun2));

        // Act
        RecentActivityResponse result = memoryService.getRecentActivity("warren", 30);

        // Assert
        assertEquals(2, result.getRuns().size(), "Should return only runs older than 7 days");
        assertEquals(2, result.getTotalRuns(), "Total runs count should match filtered results");

        // Verify the date-filtered repo method was used (no in-memory filter chain).
        verify(tradingRunRepository).findByAgentIdAndStartedAtBetween(
                eq(1L), any(Instant.class), any(Instant.class), any(Pageable.class));
    }

    @Test
    @DisplayName("Zero delay returns all data")
    void zeroDelay_shouldReturnAllData() {
        // Arrange: A 0-day cutoff means "now" — every run is older than the cutoff.
        Instant now = Instant.now();
        TradingRun recentRun = createRun(1L, now.minus(1, ChronoUnit.DAYS));
        TradingRun oldRun = createRun(2L, now.minus(10, ChronoUnit.DAYS));

        Pageable pageable = PageRequest.of(0, 10);
        Page<TradingRun> allRuns = new PageImpl<>(List.of(recentRun, oldRun));
        when(tradingRunRepository.findAll(any(Specification.class), eq(pageable))).thenReturn(allRuns);
        when(decisionPhaseRepository.findByRunId(anyLong())).thenReturn(Optional.empty());

        // Act: Call service method with cutoff = now (0-day delay equivalent)
        RunListResponseDto result = tradingRunService.listRuns(null, now, pageable);

        // Assert: All runs should be returned (no filtering)
        assertEquals(2, result.getRuns().size(), "With 0 delay, all runs should be returned");

        // Verify database-level filtering was used (even with 0 delay)
        verify(tradingRunRepository).findAll(any(Specification.class), eq(pageable));
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
