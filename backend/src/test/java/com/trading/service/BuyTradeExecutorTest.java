package com.trading.service;

import com.trading.dto.response.TradeResult;
import com.trading.entity.*;
import com.trading.repository.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import com.trading.exception.BusinessRuleException;
import com.trading.exception.ResourceNotFoundException;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("BuyTradeExecutor Tests")
class BuyTradeExecutorTest {

    @Mock
    private TradingAccountRepository tradingAccountRepository;

    @Mock
    private AccountTransactionRepository transactionRepository;

    @Mock
    private AccountHoldingRepository holdingRepository;

    @Mock
    private MarketService marketService;

    @InjectMocks
    private BuyTradeExecutor buyTradeExecutor;

    private TradingAccount testAccount;
    private TradingAgent testAgent;
    private MarketService.PriceData testPriceData;

    @BeforeEach
    void setUp() {
        // Create test agent
        testAgent = new TradingAgent("Warren", "Value investor");
        testAgent.setId(1L);

        // Create test account with $10,000 balance
        testAccount = new TradingAccount(testAgent, 10000.0);
        testAccount.setId(1L);

        // Create test price data
        testPriceData = new MarketService.PriceData(150.0, DataTier.REAL_TIME, Instant.now(), "Finnhub");
    }

    // ========== HAPPY PATH TESTS ==========

    @Test
    @DisplayName("Should buy shares successfully when all validations pass")
    void testExecuteBuy_AllValidationPass_Success() {
        // Arrange
        String agentName = "Warren";
        String symbol = "AAPL";
        Integer quantity = 10;
        Long runId = 1L;
        Double price = 150.0;
        Double expectedBalance = 8500.0; // 10000 - 1500

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findActiveHoldingsByAccount(testAccount))
            .thenReturn(new ArrayList<>()); // No existing holdings
        when(marketService.getSharePrice(symbol))
            .thenReturn(testPriceData);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.findByAccountAndSymbol(testAccount, symbol))
            .thenReturn(null); // New holding

        AccountHolding newHolding = new AccountHolding(testAccount, symbol, quantity, price);
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(newHolding);

        // Act
        TradeResult result = buyTradeExecutor.executeBuy(agentName, symbol, quantity, runId);

        // Assert
        assertNotNull(result);
        assertEquals(symbol, result.symbol());
        assertEquals(quantity, result.quantity());
        assertEquals(price, result.price());
        assertEquals(expectedBalance, result.newBalance());

        // Verify balance was updated
        verify(tradingAccountRepository).save(testAccount);
        assertEquals(expectedBalance, testAccount.getBalance());

        // Verify transaction was created with correct business logic
        ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
        verify(transactionRepository).save(transactionCaptor.capture());

        AccountTransaction savedTransaction = transactionCaptor.getValue();
        assertAll("Transaction should have correct business logic fields",
            () -> assertEquals(testAccount, savedTransaction.getAccount(), "Account should match"),
            () -> assertEquals(symbol, savedTransaction.getSymbol(), "Symbol should match"),
            () -> assertEquals(TransactionType.BUY, savedTransaction.getTransactionType(), "Transaction type should be BUY"),
            () -> assertEquals(quantity, savedTransaction.getQuantity(), "Quantity should match"),
            () -> assertEquals(price, savedTransaction.getPrice(), "Price should match"),
            () -> assertNotNull(savedTransaction.getTimestamp(), "Timestamp should be set")
        );

        // Verify holding was created with correct business logic
        ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
        verify(holdingRepository).save(holdingCaptor.capture());

        AccountHolding savedHolding = holdingCaptor.getValue();
        assertAll("Holding should have correct business logic fields",
            () -> assertEquals(testAccount, savedHolding.getAccount(), "Account should match"),
            () -> assertEquals(symbol, savedHolding.getSymbol(), "Symbol should match"),
            () -> assertEquals(quantity, savedHolding.getQuantity(), "Quantity should match"),
            () -> assertEquals(price, savedHolding.getAveragePrice(), "Average price should equal purchase price for new holding")
        );
    }

    @Test
    @DisplayName("Should add to existing holding when symbol already owned")
    void testExecuteBuy_ExistingHolding_UpdatesAveragePrice() {
        // Arrange
        String agentName = "Warren";
        String symbol = "AAPL";
        Integer existingQuantity = 50;
        Double existingAvgPrice = 150.0;
        Integer buyQuantity = 30;
        Double buyPrice = 160.0;

        // Expected: (50*150 + 30*160) / 80 = (7500 + 4800) / 80 = 153.75
        Double expectedAvgPrice = 153.75;
        Integer expectedQuantity = 80;

        AccountHolding existingHolding = new AccountHolding(testAccount, symbol, existingQuantity, existingAvgPrice);

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findActiveHoldingsByAccount(testAccount))
            .thenReturn(Arrays.asList(existingHolding)); // Has existing holding
        when(marketService.getSharePrice(symbol))
            .thenReturn(new MarketService.PriceData(buyPrice, DataTier.REAL_TIME, Instant.now(), "Finnhub"));
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.findByAccountAndSymbol(testAccount, symbol))
            .thenReturn(existingHolding); // Return existing holding
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(existingHolding);

        // Act
        TradeResult result = buyTradeExecutor.executeBuy(agentName, symbol, buyQuantity, 1L);

        // Assert
        assertNotNull(result);
        assertEquals(symbol, result.symbol());

        // Verify holding was updated (not deleted)
        ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
        verify(holdingRepository).save(holdingCaptor.capture());
        verify(holdingRepository, never()).delete(any());

        AccountHolding updatedHolding = holdingCaptor.getValue();
        assertEquals(expectedQuantity, updatedHolding.getQuantity());
        assertEquals(expectedAvgPrice, updatedHolding.getAveragePrice(), 0.01);
    }

    @Test
    @DisplayName("Should create new holding when symbol not owned")
    void testExecuteBuy_NewSymbol_CreatesNewHolding() {
        // Arrange
        String agentName = "Warren";
        String symbol = "MSFT";
        Integer quantity = 20;
        Double price = 300.0;

        // Create 5 existing holdings (different symbols)
        List<AccountHolding> existingHoldings = Arrays.asList(
            new AccountHolding(testAccount, "AAPL", 10, 150.0),
            new AccountHolding(testAccount, "GOOGL", 5, 2800.0),
            new AccountHolding(testAccount, "TSLA", 15, 200.0),
            new AccountHolding(testAccount, "AMZN", 8, 3000.0),
            new AccountHolding(testAccount, "META", 12, 250.0)
        );

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findActiveHoldingsByAccount(testAccount))
            .thenReturn(existingHoldings);
        when(marketService.getSharePrice(symbol))
            .thenReturn(new MarketService.PriceData(price, DataTier.REAL_TIME, Instant.now(), "Finnhub"));
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.findByAccountAndSymbol(testAccount, symbol))
            .thenReturn(null); // New holding

        AccountHolding newHolding = new AccountHolding(testAccount, symbol, quantity, price);
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(newHolding);

        // Act
        TradeResult result = buyTradeExecutor.executeBuy(agentName, symbol, quantity, 1L);

        // Assert
        assertNotNull(result);
        assertEquals(symbol, result.symbol());
        assertEquals(quantity, result.quantity());

        // Verify new holding was created
        ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
        verify(holdingRepository).save(holdingCaptor.capture());

        AccountHolding capturedHolding = holdingCaptor.getValue();
        assertEquals(symbol, capturedHolding.getSymbol());
        assertEquals(quantity, capturedHolding.getQuantity());
        assertEquals(price, capturedHolding.getAveragePrice());
    }

    @Test
    @DisplayName("Should allow buying more of existing symbol even at position limit")
    void testExecuteBuy_ExistingSymbolAtPositionLimit_Success() {
        // Arrange
        String agentName = "Warren";
        String symbol = "AAPL"; // Already owned

        // Create exactly 10 holdings including AAPL
        List<AccountHolding> tenHoldings = Arrays.asList(
            new AccountHolding(testAccount, "AAPL", 50, 150.0), // Existing AAPL
            new AccountHolding(testAccount, "GOOGL", 5, 2800.0),
            new AccountHolding(testAccount, "MSFT", 10, 300.0),
            new AccountHolding(testAccount, "TSLA", 15, 200.0),
            new AccountHolding(testAccount, "AMZN", 8, 3000.0),
            new AccountHolding(testAccount, "META", 12, 250.0),
            new AccountHolding(testAccount, "NFLX", 7, 400.0),
            new AccountHolding(testAccount, "NVDA", 10, 500.0),
            new AccountHolding(testAccount, "AMD", 20, 100.0),
            new AccountHolding(testAccount, "INTC", 30, 50.0)
        );

        AccountHolding aaplHolding = tenHoldings.get(0);

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findActiveHoldingsByAccount(testAccount))
            .thenReturn(tenHoldings);
        when(marketService.getSharePrice(symbol))
            .thenReturn(testPriceData);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.findByAccountAndSymbol(testAccount, symbol))
            .thenReturn(aaplHolding); // Existing AAPL holding
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(aaplHolding);

        // Act - Should succeed (adding to existing, not new position)
        TradeResult result = buyTradeExecutor.executeBuy(agentName, symbol, 10, 1L);

        // Assert
        assertNotNull(result);
        assertEquals(symbol, result.symbol());
        // No exception thrown - buy succeeded
    }

    // ========== VALIDATION TESTS ==========

    @Test
    @DisplayName("Should throw IllegalArgumentException when runId is null")
    void testExecuteBuy_NullRunId_ThrowsException() {
        // Arrange
        String agentName = "Warren";
        String symbol = "AAPL";
        Integer quantity = 10;
        Long runId = null;

        // Act & Assert
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            buyTradeExecutor.executeBuy(agentName, symbol, quantity, runId);
        });

        assertEquals("runId is required - every transaction must be linked to an agent run",
            exception.getMessage());

        // Verify no repository calls were made
        verify(tradingAccountRepository, never()).findByAgentName(any());
        verify(tradingAccountRepository, never()).save(any());
        verify(transactionRepository, never()).save(any());
        verify(holdingRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should throw RuntimeException when insufficient funds")
    void testExecuteBuy_InsufficientFunds_ThrowsException() {
        // Arrange
        String agentName = "Warren";
        String symbol = "AAPL";
        Integer quantity = 100;
        // Cost would be $15,000 (100 * $150) - more than $10,000 balance

        testAccount.setBalance(1000.0); // Only $1,000 available

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findActiveHoldingsByAccount(testAccount))
            .thenReturn(new ArrayList<>());
        when(marketService.getSharePrice(symbol))
            .thenReturn(testPriceData);

        // Act & Assert
        BusinessRuleException exception = assertThrows(BusinessRuleException.class, () -> {
            buyTradeExecutor.executeBuy(agentName, symbol, quantity, 1L);
        });

        assertTrue(exception.getMessage().contains("Insufficient funds"));
        assertTrue(exception.getMessage().contains("Required: $15000.00"));
        assertTrue(exception.getMessage().contains("Available: $1000.00"));

        // Verify balance was not changed
        assertEquals(1000.0, testAccount.getBalance());

        // Verify no transaction or holding was created
        verify(transactionRepository, never()).save(any());
        verify(holdingRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should throw RuntimeException when at position limit buying new symbol")
    void testExecuteBuy_AtPositionLimitNewSymbol_ThrowsException() {
        // Arrange
        String agentName = "Warren";
        String symbol = "ORCL"; // New symbol (11th position)

        // Create exactly 10 holdings (all different symbols)
        List<AccountHolding> tenHoldings = Arrays.asList(
            new AccountHolding(testAccount, "AAPL", 10, 150.0),
            new AccountHolding(testAccount, "GOOGL", 5, 2800.0),
            new AccountHolding(testAccount, "MSFT", 10, 300.0),
            new AccountHolding(testAccount, "TSLA", 15, 200.0),
            new AccountHolding(testAccount, "AMZN", 8, 3000.0),
            new AccountHolding(testAccount, "META", 12, 250.0),
            new AccountHolding(testAccount, "NFLX", 7, 400.0),
            new AccountHolding(testAccount, "NVDA", 10, 500.0),
            new AccountHolding(testAccount, "AMD", 20, 100.0),
            new AccountHolding(testAccount, "INTC", 30, 50.0)
        );

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findActiveHoldingsByAccount(testAccount))
            .thenReturn(tenHoldings);

        // Act & Assert
        BusinessRuleException exception = assertThrows(BusinessRuleException.class, () -> {
            buyTradeExecutor.executeBuy(agentName, symbol, 10, 1L);
        });

        // Verify error message contains all expected information
        String message = exception.getMessage();
        assertTrue(message.contains("POSITION LIMIT REACHED"));
        assertTrue(message.contains("10 positions"));
        assertTrue(message.contains("AAPL")); // First symbol
        assertTrue(message.contains("INTC")); // Last symbol
        assertTrue(message.contains("To buy " + symbol));
        assertTrue(message.contains("you must first sell"));

        // Verify error message lists all current holdings (helpful for agent decision-making)
        assertTrue(message.contains("AAPL, GOOGL, MSFT, TSLA, AMZN, META, NFLX, NVDA, AMD, INTC"));
        assertTrue(message.contains("Review your holdings"));

        // Verify no transaction or holding was created
        verify(marketService, never()).getSharePrice(any());
        verify(transactionRepository, never()).save(any());
        verify(holdingRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should throw RuntimeException when account not found")
    void testExecuteBuy_AccountNotFound_ThrowsException() {
        // Arrange
        String agentName = "NonExistent";
        String symbol = "AAPL";
        Integer quantity = 10;

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.empty());

        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
            buyTradeExecutor.executeBuy(agentName, symbol, quantity, 1L);
        });

        assertEquals("Trading account not found for agent: " + agentName +
            ". Agent must be initialized before trading operations.", exception.getMessage());

        // Verify no other operations were performed
        verify(holdingRepository, never()).findActiveHoldingsByAccount(any());
        verify(marketService, never()).getSharePrice(any());
        verify(transactionRepository, never()).save(any());
    }

    // ========== BUSINESS LOGIC TESTS ==========

    @Test
    @DisplayName("Should deduct exact cost from account balance")
    void testExecuteBuy_BalanceCalculation_ExactDeduction() {
        // Arrange
        String agentName = "Warren";
        Double initialBalance = 10000.0;
        Double price = 50.0;
        Integer quantity = 10;
        Double expectedBalance = 9500.0; // 10000 - (50 * 10)

        testAccount.setBalance(initialBalance);

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findActiveHoldingsByAccount(testAccount))
            .thenReturn(new ArrayList<>());
        when(marketService.getSharePrice("AAPL"))
            .thenReturn(new MarketService.PriceData(price, DataTier.REAL_TIME, Instant.now(), "Finnhub"));
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.findByAccountAndSymbol(any(), any()))
            .thenReturn(null);
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(new AccountHolding());

        // Act
        TradeResult result = buyTradeExecutor.executeBuy(agentName, "AAPL", quantity, 1L);

        // Assert
        assertEquals(expectedBalance, result.newBalance());
        assertEquals(expectedBalance, testAccount.getBalance());

        // Verify account was saved with new balance
        verify(tradingAccountRepository).save(testAccount);

        // Verify transaction was created with correct data
        ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
        verify(transactionRepository).save(transactionCaptor.capture());

        AccountTransaction savedTransaction = transactionCaptor.getValue();
        assertAll("Transaction should have correct fields for balance calculation test",
            () -> assertEquals(testAccount, savedTransaction.getAccount()),
            () -> assertEquals("AAPL", savedTransaction.getSymbol()),
            () -> assertEquals(TransactionType.BUY, savedTransaction.getTransactionType()),
            () -> assertEquals(quantity, savedTransaction.getQuantity()),
            () -> assertEquals(price, savedTransaction.getPrice())
        );

        // Verify holding was created with correct data
        ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
        verify(holdingRepository).save(holdingCaptor.capture());

        AccountHolding savedHolding = holdingCaptor.getValue();
        assertAll("Holding should have correct fields for balance calculation test",
            () -> assertEquals(testAccount, savedHolding.getAccount()),
            () -> assertEquals("AAPL", savedHolding.getSymbol()),
            () -> assertEquals(quantity, savedHolding.getQuantity()),
            () -> assertEquals(price, savedHolding.getAveragePrice())
        );
    }

    @Test
    @DisplayName("Should create transaction with correct type BUY")
    void testExecuteBuy_TransactionCreation_CorrectType() {
        // Arrange
        when(tradingAccountRepository.findByAgentName("Warren"))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findActiveHoldingsByAccount(testAccount))
            .thenReturn(new ArrayList<>());
        when(marketService.getSharePrice("AAPL"))
            .thenReturn(testPriceData);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.findByAccountAndSymbol(any(), any()))
            .thenReturn(null);
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(new AccountHolding());

        // Act
        buyTradeExecutor.executeBuy("Warren", "AAPL", 10, 1L);

        // Assert - Verify transaction was created with BUY type
        ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
        verify(transactionRepository).save(transactionCaptor.capture());

        AccountTransaction transaction = transactionCaptor.getValue();
        assertEquals(TransactionType.BUY, transaction.getTransactionType());
        assertEquals("AAPL", transaction.getSymbol());
        assertEquals(10, transaction.getQuantity());
        assertEquals(150.0, transaction.getPrice());
        assertNotNull(transaction.getTimestamp());
    }

    @Test
    @DisplayName("Should fetch market price from MarketService")
    void testExecuteBuy_MarketPriceFetch_CalledCorrectly() {
        // Arrange
        String symbol = "AAPL";
        Double expectedPrice = 150.0;

        when(tradingAccountRepository.findByAgentName("Warren"))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findActiveHoldingsByAccount(testAccount))
            .thenReturn(new ArrayList<>());
        when(marketService.getSharePrice(symbol))
            .thenReturn(testPriceData);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.findByAccountAndSymbol(any(), any()))
            .thenReturn(null);
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(new AccountHolding());

        // Act
        TradeResult result = buyTradeExecutor.executeBuy("Warren", symbol, 10, 1L);

        // Assert - Verify MarketService was called with correct symbol
        verify(marketService).getSharePrice(symbol);

        // Verify price was used correctly
        assertEquals(expectedPrice, result.price());

        // Verify transaction was created with fetched price
        ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
        verify(transactionRepository).save(transactionCaptor.capture());

        AccountTransaction savedTransaction = transactionCaptor.getValue();
        assertAll("Transaction should use market price from MarketService",
            () -> assertEquals(testAccount, savedTransaction.getAccount()),
            () -> assertEquals(symbol, savedTransaction.getSymbol()),
            () -> assertEquals(TransactionType.BUY, savedTransaction.getTransactionType()),
            () -> assertEquals(10, savedTransaction.getQuantity()),
            () -> assertEquals(expectedPrice, savedTransaction.getPrice(), "Price should match market price")
        );

        // Verify holding was created with fetched price
        ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
        verify(holdingRepository).save(holdingCaptor.capture());

        AccountHolding savedHolding = holdingCaptor.getValue();
        assertAll("Holding should use market price from MarketService",
            () -> assertEquals(testAccount, savedHolding.getAccount()),
            () -> assertEquals(symbol, savedHolding.getSymbol()),
            () -> assertEquals(10, savedHolding.getQuantity()),
            () -> assertEquals(expectedPrice, savedHolding.getAveragePrice(), "Average price should match market price")
        );
    }

    // ========== EDGE CASES ==========

    @Test
    @DisplayName("Should handle buying exactly enough shares to deplete balance")
    void testExecuteBuy_ExactBalanceDepletion_Success() {
        // Arrange
        Double exactBalance = 1000.0;
        Double price = 100.0;
        Integer quantity = 10; // Exactly $1,000

        testAccount.setBalance(exactBalance);

        when(tradingAccountRepository.findByAgentName("Warren"))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findActiveHoldingsByAccount(testAccount))
            .thenReturn(new ArrayList<>());
        when(marketService.getSharePrice("AAPL"))
            .thenReturn(new MarketService.PriceData(price, DataTier.REAL_TIME, Instant.now(), "Finnhub"));
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.findByAccountAndSymbol(any(), any()))
            .thenReturn(null);
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(new AccountHolding());

        // Act
        TradeResult result = buyTradeExecutor.executeBuy("Warren", "AAPL", quantity, 1L);

        // Assert - Buy should succeed and balance should be exactly $0
        assertNotNull(result);
        assertEquals(0.0, result.newBalance());
        assertEquals(0.0, testAccount.getBalance());

        // Verify transaction was created with correct data
        ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
        verify(transactionRepository).save(transactionCaptor.capture());

        AccountTransaction savedTransaction = transactionCaptor.getValue();
        assertAll("Transaction should have correct fields for exact balance depletion",
            () -> assertEquals(testAccount, savedTransaction.getAccount()),
            () -> assertEquals("AAPL", savedTransaction.getSymbol()),
            () -> assertEquals(TransactionType.BUY, savedTransaction.getTransactionType()),
            () -> assertEquals(quantity, savedTransaction.getQuantity()),
            () -> assertEquals(price, savedTransaction.getPrice())
        );

        // Verify holding was created with correct data
        ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
        verify(holdingRepository).save(holdingCaptor.capture());

        AccountHolding savedHolding = holdingCaptor.getValue();
        assertAll("Holding should have correct fields for exact balance depletion",
            () -> assertEquals(testAccount, savedHolding.getAccount()),
            () -> assertEquals("AAPL", savedHolding.getSymbol()),
            () -> assertEquals(quantity, savedHolding.getQuantity()),
            () -> assertEquals(price, savedHolding.getAveragePrice())
        );
    }

    @Test
    @DisplayName("Should handle fractional dollar amounts correctly")
    void testExecuteBuy_FractionalDollars_CorrectCalculation() {
        // Arrange
        Double initialBalance = 10000.75;
        Double price = 33.33;
        Integer quantity = 15;
        Double expectedBalance = 9500.80; // 10000.75 - (33.33 * 15)

        testAccount.setBalance(initialBalance);

        when(tradingAccountRepository.findByAgentName("Warren"))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findActiveHoldingsByAccount(testAccount))
            .thenReturn(new ArrayList<>());
        when(marketService.getSharePrice("AAPL"))
            .thenReturn(new MarketService.PriceData(price, DataTier.REAL_TIME, Instant.now(), "Finnhub"));
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.findByAccountAndSymbol(any(), any()))
            .thenReturn(null);
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(new AccountHolding());

        // Act
        TradeResult result = buyTradeExecutor.executeBuy("Warren", "AAPL", quantity, 1L);

        // Assert - Verify fractional amounts handled correctly
        assertEquals(expectedBalance, result.newBalance(), 0.01);
        assertEquals(expectedBalance, testAccount.getBalance(), 0.01);

        // Verify transaction was created with correct fractional data
        ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
        verify(transactionRepository).save(transactionCaptor.capture());

        AccountTransaction savedTransaction = transactionCaptor.getValue();
        assertAll("Transaction should have correct fields for fractional dollars",
            () -> assertEquals(testAccount, savedTransaction.getAccount()),
            () -> assertEquals("AAPL", savedTransaction.getSymbol()),
            () -> assertEquals(TransactionType.BUY, savedTransaction.getTransactionType()),
            () -> assertEquals(quantity, savedTransaction.getQuantity()),
            () -> assertEquals(price, savedTransaction.getPrice(), 0.01, "Price should match fractional value")
        );

        // Verify holding was created with correct fractional data
        ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
        verify(holdingRepository).save(holdingCaptor.capture());

        AccountHolding savedHolding = holdingCaptor.getValue();
        assertAll("Holding should have correct fields for fractional dollars",
            () -> assertEquals(testAccount, savedHolding.getAccount()),
            () -> assertEquals("AAPL", savedHolding.getSymbol()),
            () -> assertEquals(quantity, savedHolding.getQuantity()),
            () -> assertEquals(price, savedHolding.getAveragePrice(), 0.01, "Average price should match fractional value")
        );
    }
}
