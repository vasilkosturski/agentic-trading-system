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
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("SellTradeExecutor Tests")
class SellTradeExecutorTest {

    @Mock
    private TradingAccountRepository tradingAccountRepository;

    @Mock
    private AccountTransactionRepository transactionRepository;

    @Mock
    private AccountHoldingRepository holdingRepository;

    @Mock
    private MarketService marketService;

    @InjectMocks
    private SellTradeExecutor sellTradeExecutor;

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
        testPriceData = new MarketService.PriceData(150.0, true, Instant.now(), "Finnhub");
    }

    // ========== HAPPY PATH TESTS ==========

    @Test
    @DisplayName("Should sell partial shares successfully when all validations pass")
    void testExecuteSell_AllValidationPass_Success() {
        // Arrange
        String agentName = "Warren";
        String symbol = "AAPL";
        Integer existingQuantity = 20;
        Double averagePrice = 100.0;
        Integer sellQuantity = 10;
        Double marketPrice = 150.0;
        Double expectedBalance = 11500.0; // 10000 + (150 * 10)
        Integer expectedRemainingQuantity = 10;

        AccountHolding existingHolding = new AccountHolding(testAccount, symbol, existingQuantity, averagePrice);

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccountAndSymbol(testAccount, symbol))
            .thenReturn(existingHolding);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(existingHolding);

        // Act
        TradeResult result = sellTradeExecutor.executeSell(agentName, symbol, sellQuantity, 150.0, 1L);

        // Assert
        assertNotNull(result);
        assertEquals(symbol, result.symbol());
        assertEquals(sellQuantity, result.quantity());
        assertEquals(marketPrice, result.price());
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
            () -> assertEquals(TransactionType.SELL, savedTransaction.getTransactionType(), "Transaction type should be SELL"),
            () -> assertEquals(sellQuantity, savedTransaction.getQuantity(), "Quantity should match"),
            () -> assertEquals(marketPrice, savedTransaction.getPrice(), "Price should match"),
            () -> assertNotNull(savedTransaction.getTimestamp(), "Timestamp should be set")
        );

        // Verify holding was updated with correct business logic
        ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
        verify(holdingRepository).save(holdingCaptor.capture());
        verify(holdingRepository, never()).delete(any());

        AccountHolding savedHolding = holdingCaptor.getValue();
        assertAll("Holding should have correct business logic fields",
            () -> assertEquals(testAccount, savedHolding.getAccount(), "Account should match"),
            () -> assertEquals(symbol, savedHolding.getSymbol(), "Symbol should match"),
            () -> assertEquals(expectedRemainingQuantity, savedHolding.getQuantity(), "Quantity should be reduced"),
            () -> assertEquals(averagePrice, savedHolding.getAveragePrice(), "Average price should remain unchanged")
        );
    }

    @Test
    @DisplayName("Should delete holding when selling all shares")
    void testExecuteSell_SellAllShares_DeletesHolding() {
        // Arrange
        String agentName = "Warren";
        String symbol = "AAPL";
        Integer quantity = 10;
        Double averagePrice = 100.0;
        Double marketPrice = 150.0;

        AccountHolding existingHolding = new AccountHolding(testAccount, symbol, quantity, averagePrice);

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccountAndSymbol(testAccount, symbol))
            .thenReturn(existingHolding);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());

        // Act
        TradeResult result = sellTradeExecutor.executeSell(agentName, symbol, quantity, 150.0, 1L);

        // Assert
        assertNotNull(result);
        assertEquals(symbol, result.symbol());
        assertEquals(quantity, result.quantity());

        // Verify holding was DELETED (not saved)
        verify(holdingRepository).delete(existingHolding);
        verify(holdingRepository, never()).save(any());

        // Verify transaction was still created
        verify(transactionRepository).save(any(AccountTransaction.class));

        // Verify balance was still updated
        verify(tradingAccountRepository).save(testAccount);
    }

    @Test
    @DisplayName("Should update quantity only when selling partial shares")
    void testExecuteSell_PartialSale_UpdatesQuantityOnly() {
        // Arrange
        String agentName = "Warren";
        String symbol = "AAPL";
        Integer existingQuantity = 50;
        Double averagePrice = 100.0;
        Integer sellQuantity = 20;
        Integer expectedQuantity = 30;

        AccountHolding existingHolding = new AccountHolding(testAccount, symbol, existingQuantity, averagePrice);

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccountAndSymbol(testAccount, symbol))
            .thenReturn(existingHolding);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(existingHolding);

        // Act
        TradeResult result = sellTradeExecutor.executeSell(agentName, symbol, sellQuantity, 150.0, 1L);

        // Assert
        assertNotNull(result);

        // Verify holding was updated (not deleted)
        ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
        verify(holdingRepository).save(holdingCaptor.capture());
        verify(holdingRepository, never()).delete(any());

        AccountHolding updatedHolding = holdingCaptor.getValue();
        assertEquals(expectedQuantity, updatedHolding.getQuantity());
        assertEquals(averagePrice, updatedHolding.getAveragePrice());
    }

    // ========== VALIDATION TESTS ==========

    @Test
    @DisplayName("Should throw BusinessRuleException when no holding exists")
    void testExecuteSell_NoHolding_ThrowsException() {
        // Arrange
        String agentName = "Warren";
        String symbol = "AAPL";
        Integer quantity = 10;

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccountAndSymbol(testAccount, symbol))
            .thenReturn(null); // No holding exists

        // Act & Assert
        BusinessRuleException exception = assertThrows(BusinessRuleException.class, () -> {
            sellTradeExecutor.executeSell(agentName, symbol, quantity, 150.0, 1L);
        });

        assertTrue(exception.getMessage().contains("Cannot sell " + quantity + " shares of " + symbol));
        assertTrue(exception.getMessage().contains("Only have 0 shares available"));

        // Verify no repository operations were performed
        verify(marketService, never()).getSharePrice(any());
        verify(tradingAccountRepository, never()).save(any());
        verify(transactionRepository, never()).save(any());
        verify(holdingRepository, never()).save(any());
        verify(holdingRepository, never()).delete(any());
    }

    @Test
    @DisplayName("Should throw RuntimeException when insufficient shares available")
    void testExecuteSell_InsufficientShares_ThrowsException() {
        // Arrange
        String agentName = "Warren";
        String symbol = "AAPL";
        Integer availableQuantity = 5;
        Integer sellQuantity = 10;

        AccountHolding existingHolding = new AccountHolding(testAccount, symbol, availableQuantity, 100.0);

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccountAndSymbol(testAccount, symbol))
            .thenReturn(existingHolding);

        // Act & Assert
        BusinessRuleException exception = assertThrows(BusinessRuleException.class, () -> {
            sellTradeExecutor.executeSell(agentName, symbol, sellQuantity, 150.0, 1L);
        });

        assertTrue(exception.getMessage().contains("Cannot sell " + sellQuantity + " shares of " + symbol));
        assertTrue(exception.getMessage().contains("Only have " + availableQuantity + " shares available"));

        // Verify no repository operations were performed
        verify(marketService, never()).getSharePrice(any());
        verify(tradingAccountRepository, never()).save(any());
        verify(transactionRepository, never()).save(any());
        verify(holdingRepository, never()).save(any());
        verify(holdingRepository, never()).delete(any());
    }

    @Test
    @DisplayName("Should throw RuntimeException when account not found")
    void testExecuteSell_AccountNotFound_ThrowsException() {
        // Arrange
        String agentName = "NonExistent";
        String symbol = "AAPL";
        Integer quantity = 10;

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.empty());

        // Act & Assert
        ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
            sellTradeExecutor.executeSell(agentName, symbol, quantity, 150.0, 1L);
        });

        assertEquals("Trading account not found for agent: " + agentName +
            ". Agent must be initialized before trading operations.", exception.getMessage());

        // Verify no other operations were performed
        verify(holdingRepository, never()).findByAccountAndSymbol(any(), any());
        verify(marketService, never()).getSharePrice(any());
        verify(transactionRepository, never()).save(any());
        verify(holdingRepository, never()).save(any());
        verify(holdingRepository, never()).delete(any());
    }

    @Test
    @DisplayName("Should throw IllegalArgumentException when runId is null")
    void testExecuteSell_NullRunId_ThrowsException() {
        // Arrange
        String agentName = "Warren";
        String symbol = "AAPL";
        Integer quantity = 10;
        Long runId = null;

        // Act & Assert
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            sellTradeExecutor.executeSell(agentName, symbol, quantity, 150.0, runId);
        });

        assertEquals("runId is required - every transaction must be linked to an agent run",
            exception.getMessage());

        // Verify no repository calls were made
        verify(tradingAccountRepository, never()).findByAgentName(any());
        verify(holdingRepository, never()).findByAccountAndSymbol(any(), any());
        verify(marketService, never()).getSharePrice(any());
        verify(tradingAccountRepository, never()).save(any());
        verify(transactionRepository, never()).save(any());
        verify(holdingRepository, never()).save(any());
        verify(holdingRepository, never()).delete(any());
    }

    // ========== BUSINESS LOGIC TESTS ==========

    @Test
    @DisplayName("Should add exact proceeds to account balance")
    void testExecuteSell_BalanceCalculation_ExactAddition() {
        // Arrange
        String agentName = "Warren";
        Double initialBalance = 10000.0;
        Double marketPrice = 50.0;
        Integer quantity = 10;
        Double expectedBalance = 10500.0; // 10000 + (50 * 10)

        testAccount.setBalance(initialBalance);

        AccountHolding existingHolding = new AccountHolding(testAccount, "AAPL", 20, 100.0);

        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccountAndSymbol(testAccount, "AAPL"))
            .thenReturn(existingHolding);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(existingHolding);

        // Act
        TradeResult result = sellTradeExecutor.executeSell(agentName, "AAPL", quantity, marketPrice, 1L);

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
            () -> assertEquals(TransactionType.SELL, savedTransaction.getTransactionType()),
            () -> assertEquals(quantity, savedTransaction.getQuantity()),
            () -> assertEquals(marketPrice, savedTransaction.getPrice())
        );

        // Verify holding was updated with correct data
        ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
        verify(holdingRepository).save(holdingCaptor.capture());

        AccountHolding savedHolding = holdingCaptor.getValue();
        assertAll("Holding should have correct fields for balance calculation test",
            () -> assertEquals(testAccount, savedHolding.getAccount()),
            () -> assertEquals("AAPL", savedHolding.getSymbol()),
            () -> assertEquals(10, savedHolding.getQuantity()),
            () -> assertEquals(100.0, savedHolding.getAveragePrice())
        );
    }

    @Test
    @DisplayName("Should use provided price parameter correctly")
    void testExecuteSell_PriceParameter_UsedCorrectly() {
        // Arrange
        String symbol = "AAPL";
        Double providedPrice = 150.0;

        AccountHolding existingHolding = new AccountHolding(testAccount, symbol, 20, 100.0);

        when(tradingAccountRepository.findByAgentName("Warren"))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccountAndSymbol(testAccount, symbol))
            .thenReturn(existingHolding);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(existingHolding);

        // Act
        TradeResult result = sellTradeExecutor.executeSell("Warren", symbol, 10, providedPrice, 1L);

        // Assert - Verify price parameter was used correctly
        assertEquals(providedPrice, result.price());

        // Verify transaction was created with provided price
        ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
        verify(transactionRepository).save(transactionCaptor.capture());

        AccountTransaction savedTransaction = transactionCaptor.getValue();
        assertAll("Transaction should use provided price parameter",
            () -> assertEquals(testAccount, savedTransaction.getAccount()),
            () -> assertEquals(symbol, savedTransaction.getSymbol()),
            () -> assertEquals(TransactionType.SELL, savedTransaction.getTransactionType()),
            () -> assertEquals(10, savedTransaction.getQuantity()),
            () -> assertEquals(providedPrice, savedTransaction.getPrice(), "Price should match provided parameter")
        );
    }

    @Test
    @DisplayName("Should create transaction with correct type SELL")
    void testExecuteSell_TransactionCreation_CorrectType() {
        // Arrange
        AccountHolding existingHolding = new AccountHolding(testAccount, "AAPL", 20, 100.0);

        when(tradingAccountRepository.findByAgentName("Warren"))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccountAndSymbol(testAccount, "AAPL"))
            .thenReturn(existingHolding);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(existingHolding);

        // Act
        sellTradeExecutor.executeSell("Warren", "AAPL", 10, 150.0, 1L);

        // Assert - Verify transaction was created with SELL type
        ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
        verify(transactionRepository).save(transactionCaptor.capture());

        AccountTransaction transaction = transactionCaptor.getValue();
        assertEquals(TransactionType.SELL, transaction.getTransactionType());
        assertEquals("AAPL", transaction.getSymbol());
        assertEquals(10, transaction.getQuantity());
        assertEquals(150.0, transaction.getPrice());
        assertNotNull(transaction.getTimestamp());
    }

    // ========== EDGE CASES ==========

    @Test
    @DisplayName("Should handle selling exactly all remaining shares")
    void testExecuteSell_ExactShareDepletion_Success() {
        // Arrange
        Integer exactQuantity = 10;

        AccountHolding existingHolding = new AccountHolding(testAccount, "AAPL", exactQuantity, 100.0);

        when(tradingAccountRepository.findByAgentName("Warren"))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccountAndSymbol(testAccount, "AAPL"))
            .thenReturn(existingHolding);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());

        // Act
        TradeResult result = sellTradeExecutor.executeSell("Warren", "AAPL", exactQuantity, 150.0, 1L);

        // Assert - Sell should succeed and holding should be deleted
        assertNotNull(result);
        assertEquals("AAPL", result.symbol());

        // Verify holding was DELETED
        verify(holdingRepository).delete(existingHolding);
        verify(holdingRepository, never()).save(any());

        // Verify transaction was created with correct data
        ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
        verify(transactionRepository).save(transactionCaptor.capture());

        AccountTransaction savedTransaction = transactionCaptor.getValue();
        assertAll("Transaction should have correct fields for exact share depletion",
            () -> assertEquals(testAccount, savedTransaction.getAccount()),
            () -> assertEquals("AAPL", savedTransaction.getSymbol()),
            () -> assertEquals(TransactionType.SELL, savedTransaction.getTransactionType()),
            () -> assertEquals(exactQuantity, savedTransaction.getQuantity()),
            () -> assertEquals(150.0, savedTransaction.getPrice())
        );
    }

    @Test
    @DisplayName("Should handle fractional dollar amounts correctly")
    void testExecuteSell_FractionalDollars_CorrectCalculation() {
        // Arrange
        Double initialBalance = 10000.25;
        Double price = 150.75;
        Integer quantity = 10;
        Double expectedBalance = 11507.75; // 10000.25 + (150.75 * 10)

        testAccount.setBalance(initialBalance);

        AccountHolding existingHolding = new AccountHolding(testAccount, "AAPL", 20, 100.0);

        when(tradingAccountRepository.findByAgentName("Warren"))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccountAndSymbol(testAccount, "AAPL"))
            .thenReturn(existingHolding);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(existingHolding);

        // Act
        TradeResult result = sellTradeExecutor.executeSell("Warren", "AAPL", quantity, price, 1L);

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
            () -> assertEquals(TransactionType.SELL, savedTransaction.getTransactionType()),
            () -> assertEquals(quantity, savedTransaction.getQuantity()),
            () -> assertEquals(price, savedTransaction.getPrice(), 0.01, "Price should match fractional value")
        );
    }

    @Test
    @DisplayName("Should keep average price unchanged after selling shares")
    void testExecuteSell_AveragePriceUnchanged_AfterSell() {
        // Arrange
        String symbol = "AAPL";
        Integer existingQuantity = 50;
        Double originalAveragePrice = 100.0;
        Integer sellQuantity = 20;
        Integer expectedQuantity = 30;

        AccountHolding existingHolding = new AccountHolding(testAccount, symbol, existingQuantity, originalAveragePrice);

        when(tradingAccountRepository.findByAgentName("Warren"))
            .thenReturn(Optional.of(testAccount));
        when(holdingRepository.findByAccountAndSymbol(testAccount, symbol))
            .thenReturn(existingHolding);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(testAccount);
        when(transactionRepository.save(any(AccountTransaction.class)))
            .thenReturn(new AccountTransaction());
        when(holdingRepository.save(any(AccountHolding.class)))
            .thenReturn(existingHolding);

        // Act
        sellTradeExecutor.executeSell("Warren", symbol, sellQuantity, 150.0, 1L);

        // Assert - Verify average price remains unchanged
        ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
        verify(holdingRepository).save(holdingCaptor.capture());

        AccountHolding updatedHolding = holdingCaptor.getValue();
        assertEquals(expectedQuantity, updatedHolding.getQuantity(), "Quantity should be reduced");
        assertEquals(originalAveragePrice, updatedHolding.getAveragePrice(), "Average price should remain unchanged");
    }
}
