package com.trading.service;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.trading.dto.response.PortfolioSnapshotDto;
import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.repository.AccountPortfolioSnapshotRepository;
import java.time.Instant;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

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

    // The 4 filter-routing branches dispatch on the (agentName, start, end) triple
    // to one of 4 repository methods. Parametrize the triple + an enum tag that
    // selects which repository method the test stubs and verifies.
    private static final Instant FILTER_START = Instant.parse("2026-03-01T00:00:00Z");
    private static final Instant FILTER_END = Instant.parse("2026-03-31T23:59:59Z");

    private enum RepoMethod {
        BY_AGENT,
        BY_DATE_RANGE,
        BY_AGENT_AND_DATE_RANGE,
        ALL
    }

    static Stream<Arguments> filterRoutingCases() {
        return Stream.of(
                Arguments.of("agent only", "Warren", null, null, RepoMethod.BY_AGENT),
                Arguments.of("date range only", null, FILTER_START, FILTER_END, RepoMethod.BY_DATE_RANGE),
                Arguments.of(
                        "agent + date range", "Warren", FILTER_START, FILTER_END, RepoMethod.BY_AGENT_AND_DATE_RANGE),
                Arguments.of("no filters", null, null, null, RepoMethod.ALL));
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("filterRoutingCases")
    @DisplayName("getSnapshots routes to the right repository method per filter combination")
    void getSnapshots_RoutesFilterToCorrectRepositoryMethod(
            String label, String agentName, Instant start, Instant end, RepoMethod expected) {
        switch (expected) {
            case BY_AGENT -> when(snapshotRepository.findByAgentNameOrderByTimestampDesc("Warren"))
                    .thenReturn(Arrays.asList(snapshot));
            case BY_DATE_RANGE -> when(snapshotRepository.findByTimestampBetween(FILTER_START, FILTER_END))
                    .thenReturn(Arrays.asList(snapshot));
            case BY_AGENT_AND_DATE_RANGE -> when(snapshotRepository.findByAgentNameAndDateRange(
                            "Warren", FILTER_START, FILTER_END))
                    .thenReturn(Arrays.asList(snapshot));
            case ALL -> when(snapshotRepository.findAllOrderByTimestampDesc()).thenReturn(Arrays.asList(snapshot));
        }

        List<PortfolioSnapshotDto> result = portfolioService.getSnapshots(agentName, start, end, null);

        assertNotNull(result);
        assertEquals(1, result.size());
        switch (expected) {
            case BY_AGENT -> verify(snapshotRepository, times(1)).findByAgentNameOrderByTimestampDesc("Warren");
            case BY_DATE_RANGE -> verify(snapshotRepository, times(1)).findByTimestampBetween(FILTER_START, FILTER_END);
            case BY_AGENT_AND_DATE_RANGE -> verify(snapshotRepository, times(1))
                    .findByAgentNameAndDateRange("Warren", FILTER_START, FILTER_END);
            case ALL -> verify(snapshotRepository, times(1)).findAllOrderByTimestampDesc();
        }
    }

    @Test
    @DisplayName("limits results when limit parameter provided")
    void testGetSnapshotsWithLimit() {
        AccountPortfolioSnapshot snapshot2 =
                new AccountPortfolioSnapshot(account, Instant.now(), 106000.0, 51000.0, 55000.0);
        snapshot2.setId(2L);
        AccountPortfolioSnapshot snapshot3 =
                new AccountPortfolioSnapshot(account, Instant.now(), 107000.0, 52000.0, 55000.0);
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
        when(snapshotRepository.findByAgentNameOrderByTimestampDesc("Warren")).thenReturn(Arrays.asList(snapshot));

        List<PortfolioSnapshotDto> result = portfolioService.getSnapshots("Warren", null, null, 100);

        assertNotNull(result);
        assertEquals(1, result.size());
    }

    @Test
    @DisplayName("snapshot DTO contains expected chart fields")
    void testSnapshotDtoContainsOnlyChartFields() {
        when(snapshotRepository.findByAgentNameOrderByTimestampDesc("Warren")).thenReturn(Arrays.asList(snapshot));

        List<PortfolioSnapshotDto> result = portfolioService.getSnapshots("Warren", null, null, null);

        assertEquals(1, result.size());
        PortfolioSnapshotDto dto = result.get(0);
        assertEquals("Warren", dto.getAgentName());
        assertNotNull(dto.getTimestamp());
        assertEquals(105000.0, dto.getTotalValue());
    }
}
