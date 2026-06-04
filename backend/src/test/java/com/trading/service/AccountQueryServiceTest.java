package com.trading.service;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.trading.config.AgentProperties;
import com.trading.dto.response.HoldingDto;
import com.trading.entity.AccountHolding;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.exception.ResourceNotFoundException;
import com.trading.repository.AccountHoldingRepository;
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.TradingAccountRepository;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
@DisplayName("AccountQueryService Tests")
@SuppressWarnings("null")
class AccountQueryServiceTest {

    @Mock
    private TradingAccountRepository tradingAccountRepository;

    @Mock
    private AccountTransactionRepository transactionRepository;

    @Mock
    private AccountHoldingRepository holdingRepository;

    @Mock
    private MarketService marketService;

    @Mock
    private AgentProperties agentProperties;

    @Mock
    private HoldingsValuationService holdingsValuationService;

    @InjectMocks
    private AccountQueryService accountQueryService;

    private TradingAgent testAgent;
    private TradingAccount testAccount;

    @BeforeEach
    void setUp() {
        testAgent = new TradingAgent("TestAgent", "Test trading agent");
        testAgent.setId(1L);

        testAccount = new TradingAccount(testAgent, 100000.0);
        testAccount.setId(1L);

        lenient().when(agentProperties.getInitialCapital("TestAgent")).thenReturn(100000.0);
    }

    // ==================== getBalance ====================

    @Test
    @DisplayName("Should return balance when account exists")
    void testGetBalance_AccountExists_ReturnsBalance() {
        String agentName = "TestAgent";
        when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));

        Double result = accountQueryService.getBalance(agentName);

        assertNotNull(result);
        assertEquals(100000.0, result);
    }

    @Test
    @DisplayName("getBalance throws ResourceNotFoundException when account does not exist")
    void testGetBalance_AccountMissing_ThrowsException() {
        String agentName = "NonExistentAgent";
        when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.empty());

        ResourceNotFoundException exception =
                assertThrows(ResourceNotFoundException.class, () -> accountQueryService.getBalance(agentName));

        assertEquals(
                "Trading account not found for agent: " + agentName
                        + ". Agent must be initialized before trading operations.",
                exception.getMessage());
    }

    // ==================== getHoldings ====================

    @Test
    @DisplayName("Should return holdings list when account has holdings")
    void testGetHoldings_AccountHasHoldings_ReturnsList() {
        String agentName = "TestAgent";
        AccountHolding holding1 = new AccountHolding(testAccount, "AAPL", 10, 150.0);
        AccountHolding holding2 = new AccountHolding(testAccount, "GOOGL", 5, 2800.0);
        List<AccountHolding> holdings = Arrays.asList(holding1, holding2);

        when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccount(testAccount)).thenReturn(holdings);

        List<HoldingDto> result = accountQueryService.getHoldings(agentName);

        assertNotNull(result);
        assertEquals(2, result.size());
        assertEquals("AAPL", result.get(0).getSymbol());
        assertEquals(10, result.get(0).getQuantity());
        assertEquals(150.0, result.get(0).getAveragePrice());
        assertEquals("GOOGL", result.get(1).getSymbol());
        assertEquals(5, result.get(1).getQuantity());
        assertEquals(2800.0, result.get(1).getAveragePrice());
    }

    @Test
    @DisplayName("getHoldings throws ResourceNotFoundException when account does not exist")
    void testGetHoldings_AccountMissing_ThrowsException() {
        String agentName = "NonExistentAgent";
        when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.empty());

        ResourceNotFoundException exception =
                assertThrows(ResourceNotFoundException.class, () -> accountQueryService.getHoldings(agentName));

        assertEquals(
                "Trading account not found for agent: " + agentName
                        + ". Agent must be initialized before trading operations.",
                exception.getMessage());
        verify(holdingRepository, never()).findByAccount(any());
    }

    // ==================== getAccountReport ====================

    @Test
    @DisplayName("Account report includes per-holding current prices and P&L")
    void testGetAccountReport_IncludesCurrentPrices() {
        String agentName = "TestAgent";
        AccountHolding holding = new AccountHolding(testAccount, "AAPL", 10, 150.0);
        List<AccountHolding> holdings = List.of(holding);

        when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccount(testAccount)).thenReturn(holdings);
        when(marketService.getSharePrice("AAPL"))
                .thenReturn(
                        new MarketService.PriceData(160.0, false, java.time.Instant.now(), "Real-time from Finnhub"));
        when(holdingsValuationService.calculateHoldingsValue(holdings)).thenReturn(1600.0);
        when(transactionRepository.countByAccount(testAccount)).thenReturn(1L);

        var report = accountQueryService.getAccountReport(agentName);

        assertNotNull(report);
        assertEquals(100000.0, report.getBalance());
        assertEquals(1600.0, report.getHoldingsValue());
        assertEquals(101600.0, report.getTotalPortfolioValue());

        assertNotNull(report.getHoldings());
        assertEquals(1, report.getHoldings().size());

        HoldingDto holdingDto = report.getHoldings().get(0);
        assertEquals("AAPL", holdingDto.getSymbol());
        assertEquals(10, holdingDto.getQuantity());
        assertEquals(150.0, holdingDto.getAveragePrice());
        assertEquals(160.0, holdingDto.getCurrentPrice());
        assertEquals(1600.0, holdingDto.getMarketValue());
        assertEquals(1500.0, holdingDto.getCostBasis());
        assertEquals(100.0, holdingDto.getUnrealizedPnl());
        assertEquals(6.67, holdingDto.getGainLossPercent(), 0.01);
        assertEquals(false, holdingDto.getCached());
        assertNotNull(holdingDto.getPriceTimestamp());
    }

    @Test
    @DisplayName("Returns null price fields when MarketService fails")
    void testGetAccountReport_MarketServiceFails_NullPriceFields() {
        String agentName = "TestAgent";
        AccountHolding holding = new AccountHolding(testAccount, "GOOGL", 5, 2800.0);
        List<AccountHolding> holdings = List.of(holding);

        when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccount(testAccount)).thenReturn(holdings);
        when(marketService.getSharePrice("GOOGL")).thenThrow(new RuntimeException("Finnhub API timeout"));
        when(holdingsValuationService.calculateHoldingsValue(holdings)).thenReturn(14000.0);
        when(transactionRepository.countByAccount(testAccount)).thenReturn(1L);

        var report = accountQueryService.getAccountReport(agentName);

        HoldingDto holdingDto = report.getHoldings().get(0);
        assertEquals("GOOGL", holdingDto.getSymbol());
        assertEquals(5, holdingDto.getQuantity());
        assertEquals(2800.0, holdingDto.getAveragePrice());
        assertNull(holdingDto.getCurrentPrice());
        assertNull(holdingDto.getMarketValue());
        assertNull(holdingDto.getCostBasis());
        assertNull(holdingDto.getUnrealizedPnl());
        assertNull(holdingDto.getGainLossPercent());
        assertEquals(14000.0, report.getHoldingsValue());
    }

    @Test
    @DisplayName("Multiple holdings all have prices and P&L calculated")
    void testGetAccountReport_MultipleHoldings_AllCalculated() {
        String agentName = "TestAgent";
        List<AccountHolding> holdings = Arrays.asList(
                new AccountHolding(testAccount, "AAPL", 10, 150.0),
                new AccountHolding(testAccount, "GOOGL", 5, 2800.0),
                new AccountHolding(testAccount, "MSFT", 8, 400.0));

        when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccount(testAccount)).thenReturn(holdings);
        when(marketService.getSharePrice("AAPL"))
                .thenReturn(new MarketService.PriceData(160.0, false, java.time.Instant.now(), "Real-time"));
        when(marketService.getSharePrice("GOOGL"))
                .thenReturn(new MarketService.PriceData(2900.0, true, java.time.Instant.now(), "Cached"));
        when(marketService.getSharePrice("MSFT"))
                .thenReturn(new MarketService.PriceData(380.0, false, java.time.Instant.now(), "Real-time"));
        when(holdingsValuationService.calculateHoldingsValue(holdings)).thenReturn(19140.0);
        when(transactionRepository.countByAccount(testAccount)).thenReturn(3L);

        var report = accountQueryService.getAccountReport(agentName);

        assertEquals(3, report.getHoldings().size());

        HoldingDto aapl = report.getHoldings().get(0);
        assertEquals(100.0, aapl.getUnrealizedPnl());
        assertEquals(6.67, aapl.getGainLossPercent(), 0.01);

        HoldingDto googl = report.getHoldings().get(1);
        assertEquals(500.0, googl.getUnrealizedPnl());
        assertEquals(3.57, googl.getGainLossPercent(), 0.01);

        HoldingDto msft = report.getHoldings().get(2);
        assertEquals(-160.0, msft.getUnrealizedPnl());
        assertEquals(-5.0, msft.getGainLossPercent(), 0.01);

        double expectedHoldingsValue = 1600.0 + 14500.0 + 3040.0;
        assertEquals(expectedHoldingsValue, report.getHoldingsValue(), 0.01);
    }

    @Test
    @DisplayName("getAccountReport propagates ResourceNotFoundException for unknown agent")
    void testGetAccountReport_UnknownAgent_PropagatesResourceNotFoundException() {
        String agentName = "nonexistent";
        when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.empty());

        ResourceNotFoundException thrown =
                assertThrows(ResourceNotFoundException.class, () -> accountQueryService.getAccountReport(agentName));
        assertTrue(thrown.getMessage().contains(agentName));
    }

    // ==================== getTotalPortfolioValue ====================

    @Test
    @DisplayName("getTotalPortfolioValue sums balance + holdings value when account has holdings")
    void testGetTotalPortfolioValue_WithHoldings_ReturnsSum() {
        String agentName = "TestAgent";
        AccountHolding holding = new AccountHolding(testAccount, "AAPL", 10, 150.0);
        List<AccountHolding> holdings = List.of(holding);

        when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccount(testAccount)).thenReturn(holdings);
        when(holdingsValuationService.calculateHoldingsValue(holdings)).thenReturn(1600.0);

        Double total = accountQueryService.getTotalPortfolioValue(agentName);

        assertEquals(101600.0, total);
    }
}
