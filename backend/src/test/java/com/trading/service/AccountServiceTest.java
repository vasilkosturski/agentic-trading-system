package com.trading.service;

import com.trading.config.AgentProperties;
import com.trading.dto.response.HoldingDto;
import com.trading.entity.AccountHolding;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.repository.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import com.trading.exception.ResourceNotFoundException;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("AccountService Tests")
@SuppressWarnings("null")
class AccountServiceTest {

    @Mock
    private TradingAgentRepository agentRepository;

    @Mock
    private TradingAccountRepository tradingAccountRepository;

    @Mock
    private AccountHoldingRepository holdingRepository;

    @Mock
    private AccountTransactionRepository transactionRepository;

    @Mock
    private MarketService marketService;

    @Mock
    private AgentProperties agentProperties;

    @Mock
    private HoldingsValuationService holdingsValuationService;

    @InjectMocks
    private AccountService accountService;

    private TradingAgent testAgent;
    private TradingAccount testAccount;

    @BeforeEach
    void setUp() {
        // Create test agent
        testAgent = new TradingAgent("TestAgent", "Test trading agent");
        testAgent.setId(1L);

        // Create test account
        testAccount = new TradingAccount(testAgent, 100000.0);
        testAccount.setId(1L);

        // Stub agent-properties lookup for the TestAgent profile so methods that
        // resolve initial capital (e.g. getAccountReport) get a real value.
        // lenient() lets tests that never call it stay clean.
        lenient().when(agentProperties.getInitialCapital("TestAgent")).thenReturn(100000.0);
    }

    @Test
    @DisplayName("Should return existing account when both agent and account exist")
    @SuppressWarnings("null")
    void testInitializeAgent_AgentExistsAccountExists_ReturnsExisting() {
        // Arrange
        String agentName = "TestAgent";
        Double initialBalance = 100000.0;

        when(agentRepository.findByName(agentName))
            .thenReturn(Optional.of(testAgent));
        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));

        // Act
        TradingAccount result = accountService.initializeAgent(agentName, initialBalance);

        // Assert
        assertNotNull(result);
        assertEquals(testAccount.getId(), result.getId());
        assertEquals(testAccount.getBalance(), result.getBalance());

        // Verify that save was never called (we're returning existing)
        verify(tradingAccountRepository, never()).save(any());
        verify(agentRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should create new account when agent exists but account does not")
    @SuppressWarnings("null")
    void testInitializeAgent_AgentExistsAccountMissing_CreatesNewAccount() {
        // Arrange
        String agentName = "TestAgent";
        Double initialBalance = 150000.0;

        when(agentRepository.findByName(agentName))
            .thenReturn(Optional.of(testAgent));
        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.empty());

        TradingAccount savedAccount = new TradingAccount(testAgent, initialBalance);
        savedAccount.setId(2L);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(savedAccount);

        // Act
        TradingAccount result = accountService.initializeAgent(agentName, initialBalance);

        // Assert
        assertNotNull(result);
        assertEquals(initialBalance, result.getBalance());
        assertEquals(testAgent.getId(), result.getAgent().getId());

        // Verify that save was called exactly once with the correct account
        ArgumentCaptor<TradingAccount> accountCaptor = ArgumentCaptor.forClass(TradingAccount.class);
        verify(tradingAccountRepository, times(1)).save(accountCaptor.capture());

        TradingAccount capturedAccount = accountCaptor.getValue();
        assertEquals(testAgent.getId(), capturedAccount.getAgent().getId());
        assertEquals(initialBalance, capturedAccount.getBalance());

        // Verify agent was not saved
        verify(agentRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should create new agent and account when neither exist")
    @SuppressWarnings("null")
    void testInitializeAgent_AgentMissing_CreatesNewAgentAndAccount() {
        // Arrange
        String agentName = "NewAgent";
        Double initialBalance = 200000.0;

        when(agentRepository.findByName(agentName))
            .thenReturn(Optional.empty());

        TradingAgent newAgent = new TradingAgent(agentName, "Autonomous trading agent");
        newAgent.setId(3L);
        newAgent.setInitialCapital(initialBalance);
        when(agentRepository.save(any(TradingAgent.class)))
            .thenReturn(newAgent);

        TradingAccount newAccount = new TradingAccount(newAgent, initialBalance);
        newAccount.setId(3L);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(newAccount);

        // Act
        TradingAccount result = accountService.initializeAgent(agentName, initialBalance);

        // Assert
        assertNotNull(result);
        assertEquals(initialBalance, result.getBalance());
        assertEquals(newAgent.getId(), result.getAgent().getId());

        // Verify agent was saved (unknown agent name, so populateStyle is a no-op)
        ArgumentCaptor<TradingAgent> agentCaptor = ArgumentCaptor.forClass(TradingAgent.class);
        verify(agentRepository, times(1)).save(agentCaptor.capture());

        TradingAgent capturedAgent = agentCaptor.getValue();
        assertEquals(agentName, capturedAgent.getName());
        assertEquals("Autonomous trading agent", capturedAgent.getDescription());
        assertEquals(initialBalance, capturedAgent.getInitialCapital());

        // Verify account was saved with correct agent and balance
        ArgumentCaptor<TradingAccount> accountCaptor = ArgumentCaptor.forClass(TradingAccount.class);
        verify(tradingAccountRepository, times(1)).save(accountCaptor.capture());

        TradingAccount capturedAccount = accountCaptor.getValue();
        assertEquals(newAgent.getId(), capturedAccount.getAgent().getId());
        assertEquals(initialBalance, capturedAccount.getBalance());
    }

    @Test
    @DisplayName("Should set style for known agent on creation")
    void testInitializeAgent_KnownAgent_SetsStyle() {
        // Arrange
        String agentName = "Warren";
        Double initialBalance = 100000.0;

        when(agentRepository.findByName(agentName))
            .thenReturn(Optional.empty());

        TradingAgent savedAgent = new TradingAgent(agentName, "Autonomous trading agent");
        savedAgent.setId(1L);
        savedAgent.setStyle("Value Investor");
        when(agentRepository.save(any(TradingAgent.class)))
            .thenReturn(savedAgent);

        TradingAccount newAccount = new TradingAccount(savedAgent, initialBalance);
        newAccount.setId(1L);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(newAccount);

        // Act
        accountService.initializeAgent(agentName, initialBalance);

        // Assert - verify style was set before the single save
        ArgumentCaptor<TradingAgent> agentCaptor = ArgumentCaptor.forClass(TradingAgent.class);
        verify(agentRepository, times(1)).save(agentCaptor.capture());

        TradingAgent saved = agentCaptor.getValue();
        assertEquals("Value Investor", saved.getStyle());
    }

    @Test
    @DisplayName("Should backfill style for existing agent with missing style")
    void testInitializeAgent_ExistingAgentMissingStyle_BackfillsStyle() {
        // Arrange
        String agentName = "Warren";
        Double initialBalance = 100000.0;

        TradingAgent existingAgent = new TradingAgent(agentName, "Autonomous trading agent");
        existingAgent.setId(1L);
        existingAgent.setStyle(null);

        when(agentRepository.findByName(agentName))
            .thenReturn(Optional.of(existingAgent));
        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));

        // Act
        accountService.initializeAgent(agentName, initialBalance);

        // Assert - verify style was set on the managed entity directly.
        // No explicit save needed: within @Transactional, JPA dirty-checking flushes changes.
        verify(agentRepository, never()).save(any());
        assertEquals("Value Investor", existingAgent.getStyle());
    }

    @Test
    @DisplayName("Should preserve existing balance when calling initialize again on existing agent")
    void testInitializeAgent_MultipleCallsSameAgent_PreservesOriginalBalance() {
        // Arrange
        String agentName = "TestAgent";
        Double originalBalance = 100000.0;
        Double newBalance = 500000.0; // Different balance supplied

        when(agentRepository.findByName(agentName))
            .thenReturn(Optional.of(testAgent));
        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount)); // Account already exists

        // Act - Call with different balance
        TradingAccount result = accountService.initializeAgent(agentName, newBalance);

        // Assert - Should return existing account with original balance
        assertNotNull(result);
        assertEquals(originalBalance, result.getBalance()); // Original balance, not new one

        // Verify no saves occurred
        verify(tradingAccountRepository, never()).save(any());
        verify(agentRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should return balance when account exists")
    void testGetBalance_AccountExists_ReturnsBalance() {
        // Arrange
        String agentName = "TestAgent";
        Double expectedBalance = 100000.0;

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));

        // Act
        Double result = accountService.getBalance(agentName);

        // Assert
        assertNotNull(result);
        assertEquals(expectedBalance, result);
        assertEquals(testAccount.getBalance(), result);
    }

    @Test
    @DisplayName("Should throw exception when account does not exist")
    void testGetBalance_AccountMissing_ThrowsException() {
        // Arrange
        String agentName = "NonExistentAgent";

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.empty());

        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
            accountService.getBalance(agentName);
        });

        assertEquals("Trading account not found for agent: " + agentName +
            ". Agent must be initialized before trading operations.", exception.getMessage());
    }

    @Test
    @DisplayName("Should return holdings list when account has holdings")
    void testGetHoldings_AccountHasHoldings_ReturnsList() {
        // Arrange
        String agentName = "TestAgent";

        AccountHolding holding1 = new AccountHolding(testAccount, "AAPL", 10, 150.0);
        AccountHolding holding2 = new AccountHolding(testAccount, "GOOGL", 5, 2800.0);
        List<AccountHolding> holdings = Arrays.asList(holding1, holding2);

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccount(testAccount))
            .thenReturn(holdings);

        // Act
        List<HoldingDto> result = accountService.getHoldings(agentName);

        // Assert
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
    @DisplayName("Should throw exception when account does not exist")
    void testGetHoldings_AccountMissing_ThrowsException() {
        // Arrange
        String agentName = "NonExistentAgent";

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.empty());

        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
            accountService.getHoldings(agentName);
        });

        assertEquals("Trading account not found for agent: " + agentName +
            ". Agent must be initialized before trading operations.", exception.getMessage());
        verify(holdingRepository, never()).findByAccount(any()); // Ensure holdingRepository is not called
    }

    // ==================== Account Report with Prices and P&L Tests ====================

    @Test
    @DisplayName("Account report includes per-holding current prices and P&L")
    void testGetAccountReport_IncludesCurrentPrices() {
        // Arrange
        String agentName = "TestAgent";
        AccountHolding holding = new AccountHolding(testAccount, "AAPL", 10, 150.0);
        List<AccountHolding> holdings = List.of(holding);

        when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccount(testAccount)).thenReturn(holdings);
        when(marketService.getSharePrice("AAPL"))
            .thenReturn(new MarketService.PriceData(160.0, false, java.time.Instant.now(), "Real-time from Finnhub"));
        when(holdingsValuationService.calculateHoldingsValue(holdings)).thenReturn(1600.0);
        when(transactionRepository.countByAccount(testAccount)).thenReturn(1L);

        // Act
        var report = accountService.getAccountReport(agentName);

        // Assert - portfolio level
        assertNotNull(report);
        assertEquals(100000.0, report.getBalance());
        assertEquals(1600.0, report.getHoldingsValue());  // 10 * 160
        assertEquals(101600.0, report.getTotalPortfolioValue());  // 100000 + 1600

        // Assert - per-holding level
        assertNotNull(report.getHoldings());
        assertEquals(1, report.getHoldings().size());

        HoldingDto holdingDto = report.getHoldings().get(0);
        assertEquals("AAPL", holdingDto.getSymbol());
        assertEquals(10, holdingDto.getQuantity());
        assertEquals(150.0, holdingDto.getAveragePrice());

        // Current price and market values
        assertEquals(160.0, holdingDto.getCurrentPrice());
        assertEquals(1600.0, holdingDto.getMarketValue());      // 10 * 160
        assertEquals(1500.0, holdingDto.getCostBasis());        // 10 * 150
        assertEquals(100.0, holdingDto.getUnrealizedPnl());     // 1600 - 1500
        assertEquals(6.67, holdingDto.getGainLossPercent(), 0.01);  // 100/1500 * 100
        assertEquals(false, holdingDto.getCached());
        assertNotNull(holdingDto.getPriceTimestamp());
    }

    @Test
    @DisplayName("Returns null price fields when MarketService fails")
    void testGetAccountReport_MarketServiceFails_NullPriceFields() {
        // Arrange
        String agentName = "TestAgent";
        AccountHolding holding = new AccountHolding(testAccount, "GOOGL", 5, 2800.0);
        List<AccountHolding> holdings = List.of(holding);

        when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccount(testAccount)).thenReturn(holdings);
        when(marketService.getSharePrice("GOOGL"))
            .thenThrow(new RuntimeException("Finnhub API timeout"));
        when(holdingsValuationService.calculateHoldingsValue(holdings)).thenReturn(14000.0);
        when(transactionRepository.countByAccount(testAccount)).thenReturn(1L);

        // Act
        var report = accountService.getAccountReport(agentName);

        // Assert - price fields are null so frontend shows "N/A"
        HoldingDto holdingDto = report.getHoldings().get(0);
        assertEquals("GOOGL", holdingDto.getSymbol());
        assertEquals(5, holdingDto.getQuantity());
        assertEquals(2800.0, holdingDto.getAveragePrice());
        assertNull(holdingDto.getCurrentPrice());
        assertNull(holdingDto.getMarketValue());
        assertNull(holdingDto.getCostBasis());
        assertNull(holdingDto.getUnrealizedPnl());
        assertNull(holdingDto.getGainLossPercent());

        // Holdings value still calculated via calculateHoldingsValue (falls back to averagePrice)
        assertEquals(14000.0, report.getHoldingsValue());
    }

    @Test
    @DisplayName("Multiple holdings all have prices and P&L calculated")
    void testGetAccountReport_MultipleHoldings_AllCalculated() {
        // Arrange
        String agentName = "TestAgent";
        List<AccountHolding> holdings = Arrays.asList(
            new AccountHolding(testAccount, "AAPL", 10, 150.0),
            new AccountHolding(testAccount, "GOOGL", 5, 2800.0),
            new AccountHolding(testAccount, "MSFT", 8, 400.0)
        );

        when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccount(testAccount)).thenReturn(holdings);
        when(marketService.getSharePrice("AAPL"))
            .thenReturn(new MarketService.PriceData(160.0, false, java.time.Instant.now(), "Real-time"));
        when(marketService.getSharePrice("GOOGL"))
            .thenReturn(new MarketService.PriceData(2900.0, true, java.time.Instant.now(), "Cached"));
        when(marketService.getSharePrice("MSFT"))
            .thenReturn(new MarketService.PriceData(380.0, false, java.time.Instant.now(), "Real-time"));
        // 160*10 + 2900*5 + 380*8 = 19140
        when(holdingsValuationService.calculateHoldingsValue(holdings)).thenReturn(19140.0);
        when(transactionRepository.countByAccount(testAccount)).thenReturn(3L);

        // Act
        var report = accountService.getAccountReport(agentName);

        // Assert
        assertEquals(3, report.getHoldings().size());

        // AAPL: +$100 gain
        HoldingDto aapl = report.getHoldings().get(0);
        assertEquals(100.0, aapl.getUnrealizedPnl());
        assertEquals(6.67, aapl.getGainLossPercent(), 0.01);

        // GOOGL: +$500 gain
        HoldingDto googl = report.getHoldings().get(1);
        assertEquals(500.0, googl.getUnrealizedPnl());
        assertEquals(3.57, googl.getGainLossPercent(), 0.01);

        // MSFT: -$160 loss
        HoldingDto msft = report.getHoldings().get(2);
        assertEquals(-160.0, msft.getUnrealizedPnl());
        assertEquals(-5.0, msft.getGainLossPercent(), 0.01);

        // Portfolio total
        double expectedHoldingsValue = 1600.0 + 14500.0 + 3040.0;  // 160*10 + 2900*5 + 380*8
        assertEquals(expectedHoldingsValue, report.getHoldingsValue(), 0.01);
    }

    @Test
    @DisplayName("getAccountReport propagates ResourceNotFoundException for unknown agent")
    void testGetAccountReport_UnknownAgent_PropagatesResourceNotFoundException() {
        // Arrange — repository returns Optional.empty so getAccount() throws ResourceNotFoundException
        String agentName = "nonexistent";
        when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.empty());

        // Act + Assert — the typed exception must reach the caller unchanged so the
        // RestControllerAdvice can map it to HTTP 404. Any wrapper (e.g. RuntimeException)
        // would destroy the type and produce HTTP 500.
        ResourceNotFoundException thrown = assertThrows(
            ResourceNotFoundException.class,
            () -> accountService.getAccountReport(agentName)
        );
        assertTrue(thrown.getMessage().contains(agentName));
    }
}
