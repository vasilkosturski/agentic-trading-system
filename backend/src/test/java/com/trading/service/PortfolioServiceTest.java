package com.trading.service;

import com.trading.dto.response.PortfolioSnapshotDto;
import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.repository.AccountPortfolioSnapshotRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("PortfolioService Tests")
class PortfolioServiceTest {

    @Mock
    private AccountPortfolioSnapshotRepository snapshotRepository;

    @InjectMocks
    private PortfolioService portfolioService;

    private TradingAgent agent;
    private TradingAccount account;
    private AccountPortfolioSnapshot snapshot;

    @BeforeEach
    void setUp() {
        agent = new TradingAgent("Warren", "Value investor");
        agent.setId(1L);

        account = new TradingAccount(agent, 100000.0);
        account.setId(1L);

        snapshot = new AccountPortfolioSnapshot(account, Instant.now(), 105000.0, 50000.0, 55000.0);
        snapshot.setId(1L);
        snapshot.setTotalPnl(5000.0);
        snapshot.setTotalReturnPercent(5.0);
    }

    @Test
    @DisplayName("returns snapshots filtered by agent name")
    void testGetSnapshotsByAgentName() {
        when(snapshotRepository.findByAgentNameOrderByTimestampDesc("Warren"))
            .thenReturn(Arrays.asList(snapshot));

        List<PortfolioSnapshotDto> result = portfolioService.getSnapshots("Warren", null, null, null);

        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals("Warren", result.get(0).getAgentName());
        assertEquals(105000.0, result.get(0).getTotalValue());
        verify(snapshotRepository, times(1)).findByAgentNameOrderByTimestampDesc("Warren");
    }

    @Test
    @DisplayName("returns snapshots filtered by date range")
    void testGetSnapshotsByDateRange() {
        Instant start = Instant.parse("2026-03-01T00:00:00Z");
        Instant end = Instant.parse("2026-03-31T23:59:59Z");
        when(snapshotRepository.findByTimestampBetween(start, end))
            .thenReturn(Arrays.asList(snapshot));

        List<PortfolioSnapshotDto> result = portfolioService.getSnapshots(null, start, end, null);

        assertNotNull(result);
        assertEquals(1, result.size());
        verify(snapshotRepository, times(1)).findByTimestampBetween(start, end);
    }

    @Test
    @DisplayName("returns snapshots filtered by agent name and date range")
    void testGetSnapshotsByAgentNameAndDateRange() {
        Instant start = Instant.parse("2026-03-01T00:00:00Z");
        Instant end = Instant.parse("2026-03-31T23:59:59Z");
        when(snapshotRepository.findByAgentNameAndDateRange("Warren", start, end))
            .thenReturn(Arrays.asList(snapshot));

        List<PortfolioSnapshotDto> result = portfolioService.getSnapshots("Warren", start, end, null);

        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals("Warren", result.get(0).getAgentName());
        verify(snapshotRepository, times(1)).findByAgentNameAndDateRange("Warren", start, end);
    }

    @Test
    @DisplayName("returns all snapshots when no filters provided")
    void testGetAllSnapshots() {
        when(snapshotRepository.findAllOrderByTimestampDesc())
            .thenReturn(Arrays.asList(snapshot));

        List<PortfolioSnapshotDto> result = portfolioService.getSnapshots(null, null, null, null);

        assertNotNull(result);
        assertEquals(1, result.size());
        verify(snapshotRepository, times(1)).findAllOrderByTimestampDesc();
    }

    @Test
    @DisplayName("limits results when limit parameter provided")
    void testGetSnapshotsWithLimit() {
        AccountPortfolioSnapshot snapshot2 = new AccountPortfolioSnapshot(account, Instant.now(), 106000.0, 51000.0, 55000.0);
        snapshot2.setId(2L);
        AccountPortfolioSnapshot snapshot3 = new AccountPortfolioSnapshot(account, Instant.now(), 107000.0, 52000.0, 55000.0);
        snapshot3.setId(3L);

        when(snapshotRepository.findByAgentNameOrderByTimestampDesc("Warren"))
            .thenReturn(Arrays.asList(snapshot, snapshot2, snapshot3));

        List<PortfolioSnapshotDto> result = portfolioService.getSnapshots("Warren", null, null, 2);

        assertNotNull(result);
        assertEquals(2, result.size());
    }

    @Test
    @DisplayName("returns all results when limit exceeds result count")
    void testGetSnapshotsWithLimitLargerThanResults() {
        when(snapshotRepository.findByAgentNameOrderByTimestampDesc("Warren"))
            .thenReturn(Arrays.asList(snapshot));

        List<PortfolioSnapshotDto> result = portfolioService.getSnapshots("Warren", null, null, 100);

        assertNotNull(result);
        assertEquals(1, result.size());
    }

    @Test
    @DisplayName("snapshot DTO contains expected chart fields")
    void testSnapshotDtoContainsOnlyChartFields() {
        when(snapshotRepository.findByAgentNameOrderByTimestampDesc("Warren"))
            .thenReturn(Arrays.asList(snapshot));

        List<PortfolioSnapshotDto> result = portfolioService.getSnapshots("Warren", null, null, null);

        assertEquals(1, result.size());
        PortfolioSnapshotDto dto = result.get(0);
        assertEquals("Warren", dto.getAgentName());
        assertNotNull(dto.getTimestamp());
        assertEquals(105000.0, dto.getTotalValue());
    }
}
