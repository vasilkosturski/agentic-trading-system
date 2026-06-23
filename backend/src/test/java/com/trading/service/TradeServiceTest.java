package com.trading.service;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.trading.dto.response.TradeResult;
import com.trading.entity.AccountHolding;
import com.trading.entity.AccountTransaction;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.entity.TransactionType;
import com.trading.exception.BusinessRuleException;
import com.trading.exception.ResourceNotFoundException;
import com.trading.repository.AccountHoldingRepository;
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.TradingAccountRepository;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
@DisplayName("TradeService Tests")
class TradeServiceTest {

    @Mock
    private TradingAccountRepository tradingAccountRepository;

    @Mock
    private AccountTransactionRepository transactionRepository;

    @Mock
    private AccountHoldingRepository holdingRepository;

    @Mock
    private MarketService marketService;

    @Mock
    private PortfolioSnapshotService portfolioSnapshotService;

    @InjectMocks
    private TradeService tradeService;

    private TradingAccount testAccount;
    private TradingAgent testAgent;
    private MarketService.PriceData testPriceData;

    @BeforeEach
    void setUp() {
        testAgent = new TradingAgent("Warren", "Value investor");
        testAgent.setId(1L);

        testAccount = new TradingAccount(testAgent, 10000.0);
        testAccount.setId(1L);

        testPriceData = new MarketService.PriceData(150.0, true, Instant.now(), "Finnhub");
    }

    @Nested
    @DisplayName("buyShares")
    class BuyTests {

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

            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findActiveHoldingsByAccount(testAccount)).thenReturn(new ArrayList<>());
            when(marketService.getSharePrice(symbol))
                    .thenReturn(new MarketService.PriceData(150.0, true, Instant.now(), "Finnhub"));
            when(tradingAccountRepository.save(any(TradingAccount.class))).thenReturn(testAccount);
            when(transactionRepository.save(any(AccountTransaction.class))).thenReturn(new AccountTransaction());
            when(holdingRepository.findByAccountAndSymbol(testAccount, symbol)).thenReturn(null);

            AccountHolding newHolding = new AccountHolding(testAccount, symbol, quantity, price);
            when(holdingRepository.save(any(AccountHolding.class))).thenReturn(newHolding);

            // Act
            TradeResult result = tradeService.buyShares(agentName, symbol, quantity, runId);

            // Assert
            assertNotNull(result);
            assertEquals(symbol, result.symbol());
            assertEquals(quantity, result.quantity());
            assertEquals(price, result.price());
            assertEquals(expectedBalance, result.newBalance());

            verify(tradingAccountRepository).save(testAccount);
            assertEquals(expectedBalance, testAccount.getBalance());

            ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
            verify(transactionRepository).save(transactionCaptor.capture());

            AccountTransaction savedTransaction = transactionCaptor.getValue();
            assertAll(
                    "Transaction should have correct business logic fields",
                    () -> assertEquals(testAccount, savedTransaction.getAccount(), "Account should match"),
                    () -> assertEquals(symbol, savedTransaction.getSymbol(), "Symbol should match"),
                    () -> assertEquals(
                            TransactionType.BUY,
                            savedTransaction.getTransactionType(),
                            "Transaction type should be BUY"),
                    () -> assertEquals(quantity, savedTransaction.getQuantity(), "Quantity should match"),
                    () -> assertEquals(price, savedTransaction.getPrice(), "Price should match"),
                    () -> assertNotNull(savedTransaction.getTimestamp(), "Timestamp should be set"));

            ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
            verify(holdingRepository).save(holdingCaptor.capture());

            AccountHolding savedHolding = holdingCaptor.getValue();
            assertAll(
                    "Holding should have correct business logic fields",
                    () -> assertEquals(testAccount, savedHolding.getAccount(), "Account should match"),
                    () -> assertEquals(symbol, savedHolding.getSymbol(), "Symbol should match"),
                    () -> assertEquals(quantity, savedHolding.getQuantity(), "Quantity should match"),
                    () -> assertEquals(
                            price,
                            savedHolding.getAveragePrice(),
                            "Average price should equal purchase price for new holding"));
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

            Double expectedAvgPrice = 153.75;
            Integer expectedQuantity = 80;

            AccountHolding existingHolding =
                    new AccountHolding(testAccount, symbol, existingQuantity, existingAvgPrice);

            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findActiveHoldingsByAccount(testAccount)).thenReturn(Arrays.asList(existingHolding));
            when(marketService.getSharePrice(symbol))
                    .thenReturn(new MarketService.PriceData(buyPrice, true, Instant.now(), "Finnhub"));
            when(tradingAccountRepository.save(any(TradingAccount.class))).thenReturn(testAccount);
            when(transactionRepository.save(any(AccountTransaction.class))).thenReturn(new AccountTransaction());
            when(holdingRepository.findByAccountAndSymbol(testAccount, symbol)).thenReturn(existingHolding);
            when(holdingRepository.save(any(AccountHolding.class))).thenReturn(existingHolding);

            // Act
            TradeResult result = tradeService.buyShares(agentName, symbol, buyQuantity, 1L);

            // Assert
            assertNotNull(result);
            assertEquals(symbol, result.symbol());

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

            List<AccountHolding> existingHoldings = Arrays.asList(
                    new AccountHolding(testAccount, "AAPL", 10, 150.0),
                    new AccountHolding(testAccount, "GOOGL", 5, 2800.0),
                    new AccountHolding(testAccount, "TSLA", 15, 200.0),
                    new AccountHolding(testAccount, "AMZN", 8, 3000.0),
                    new AccountHolding(testAccount, "META", 12, 250.0));

            testAccount.setBalance(20000.0);

            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findActiveHoldingsByAccount(testAccount)).thenReturn(existingHoldings);
            when(marketService.getSharePrice(symbol))
                    .thenReturn(new MarketService.PriceData(price, true, Instant.now(), "Finnhub"));
            when(tradingAccountRepository.save(any(TradingAccount.class))).thenReturn(testAccount);
            when(transactionRepository.save(any(AccountTransaction.class))).thenReturn(new AccountTransaction());
            when(holdingRepository.findByAccountAndSymbol(testAccount, symbol)).thenReturn(null);

            AccountHolding newHolding = new AccountHolding(testAccount, symbol, quantity, price);
            when(holdingRepository.save(any(AccountHolding.class))).thenReturn(newHolding);

            // Act
            TradeResult result = tradeService.buyShares(agentName, symbol, quantity, 1L);

            // Assert
            assertNotNull(result);
            assertEquals(symbol, result.symbol());
            assertEquals(quantity, result.quantity());

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
            String symbol = "AAPL";

            List<AccountHolding> tenHoldings = Arrays.asList(
                    new AccountHolding(testAccount, "AAPL", 50, 150.0),
                    new AccountHolding(testAccount, "GOOGL", 5, 2800.0),
                    new AccountHolding(testAccount, "MSFT", 10, 300.0),
                    new AccountHolding(testAccount, "TSLA", 15, 200.0),
                    new AccountHolding(testAccount, "AMZN", 8, 3000.0),
                    new AccountHolding(testAccount, "META", 12, 250.0),
                    new AccountHolding(testAccount, "NFLX", 7, 400.0),
                    new AccountHolding(testAccount, "NVDA", 10, 500.0),
                    new AccountHolding(testAccount, "AMD", 20, 100.0),
                    new AccountHolding(testAccount, "INTC", 30, 50.0));

            AccountHolding aaplHolding = tenHoldings.get(0);

            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findActiveHoldingsByAccount(testAccount)).thenReturn(tenHoldings);
            when(marketService.getSharePrice(symbol))
                    .thenReturn(new MarketService.PriceData(150.0, true, Instant.now(), "Finnhub"));
            when(tradingAccountRepository.save(any(TradingAccount.class))).thenReturn(testAccount);
            when(transactionRepository.save(any(AccountTransaction.class))).thenReturn(new AccountTransaction());
            when(holdingRepository.findByAccountAndSymbol(testAccount, symbol)).thenReturn(aaplHolding);
            when(holdingRepository.save(any(AccountHolding.class))).thenReturn(aaplHolding);

            // Act
            TradeResult result = tradeService.buyShares(agentName, symbol, 10, 1L);

            // Assert
            assertNotNull(result);
            assertEquals(symbol, result.symbol());
        }

        // ========== VALIDATION TESTS ==========

        @Test
        @DisplayName("Should throw IllegalArgumentException when runId is null")
        void testExecuteBuy_NullRunId_ThrowsException() {
            String agentName = "Warren";
            String symbol = "AAPL";
            Integer quantity = 10;
            Long runId = null;

            IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
                tradeService.buyShares(agentName, symbol, quantity, runId);
            });

            assertEquals(
                    "runId is required - every transaction must be linked to an agent run", exception.getMessage());

            verify(tradingAccountRepository, never()).findByAgentName(any());
            verify(tradingAccountRepository, never()).save(any());
            verify(transactionRepository, never()).save(any());
            verify(holdingRepository, never()).save(any());
            verifyNoInteractions(portfolioSnapshotService);
        }

        @Test
        @DisplayName("Should throw RuntimeException when insufficient funds")
        void testExecuteBuy_InsufficientFunds_ThrowsException() {
            String agentName = "Warren";
            String symbol = "AAPL";
            Integer quantity = 100;

            testAccount.setBalance(1000.0);

            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findActiveHoldingsByAccount(testAccount)).thenReturn(new ArrayList<>());
            when(marketService.getSharePrice(symbol))
                    .thenReturn(new MarketService.PriceData(150.0, true, Instant.now(), "Finnhub"));

            BusinessRuleException exception = assertThrows(BusinessRuleException.class, () -> {
                tradeService.buyShares(agentName, symbol, quantity, 1L);
            });

            assertTrue(exception.getMessage().contains("Insufficient funds"));
            assertTrue(exception.getMessage().contains("Required: $15000.00"));
            assertTrue(exception.getMessage().contains("Available: $1000.00"));

            assertEquals(1000.0, testAccount.getBalance());

            verify(transactionRepository, never()).save(any());
            verify(holdingRepository, never()).save(any());
            verifyNoInteractions(portfolioSnapshotService);
        }

        @Test
        @DisplayName("Should throw RuntimeException when at position limit buying new symbol")
        void testExecuteBuy_AtPositionLimitNewSymbol_ThrowsException() {
            String agentName = "Warren";
            String symbol = "ORCL";

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
                    new AccountHolding(testAccount, "INTC", 30, 50.0));

            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findActiveHoldingsByAccount(testAccount)).thenReturn(tenHoldings);

            BusinessRuleException exception = assertThrows(BusinessRuleException.class, () -> {
                tradeService.buyShares(agentName, symbol, 10, 1L);
            });

            String message = exception.getMessage();
            assertTrue(message.contains("POSITION LIMIT REACHED"));
            assertTrue(message.contains("10 positions"));
            assertTrue(message.contains("AAPL"));
            assertTrue(message.contains("INTC"));
            assertTrue(message.contains("To buy " + symbol));
            assertTrue(message.contains("you must first sell"));

            assertTrue(message.contains("AAPL, GOOGL, MSFT, TSLA, AMZN, META, NFLX, NVDA, AMD, INTC"));
            assertTrue(message.contains("Review your holdings"));

            verify(marketService, never()).getSharePrice(any());
            verify(transactionRepository, never()).save(any());
            verify(holdingRepository, never()).save(any());
            verifyNoInteractions(portfolioSnapshotService);
        }

        @Test
        @DisplayName("Should throw RuntimeException when account not found")
        void testExecuteBuy_AccountNotFound_ThrowsException() {
            String agentName = "NonExistent";
            String symbol = "AAPL";
            Integer quantity = 10;

            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.empty());

            ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
                tradeService.buyShares(agentName, symbol, quantity, 1L);
            });

            assertEquals(
                    "Trading account not found for agent: " + agentName
                            + ". Agent must be initialized before trading operations.",
                    exception.getMessage());

            verify(holdingRepository, never()).findActiveHoldingsByAccount(any());
            verify(marketService, never()).getSharePrice(any());
            verify(transactionRepository, never()).save(any());
            verifyNoInteractions(portfolioSnapshotService);
        }

        // ========== EDGE CASES ==========

        @Test
        @DisplayName("Should handle buying exactly enough shares to deplete balance")
        void testExecuteBuy_ExactBalanceDepletion_Success() {
            Double exactBalance = 1000.0;
            Double price = 100.0;
            Integer quantity = 10;

            testAccount.setBalance(exactBalance);

            when(tradingAccountRepository.findByAgentName("Warren")).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findActiveHoldingsByAccount(testAccount)).thenReturn(new ArrayList<>());
            when(marketService.getSharePrice("AAPL"))
                    .thenReturn(new MarketService.PriceData(price, true, Instant.now(), "Finnhub"));
            when(tradingAccountRepository.save(any(TradingAccount.class))).thenReturn(testAccount);
            when(transactionRepository.save(any(AccountTransaction.class))).thenReturn(new AccountTransaction());
            when(holdingRepository.findByAccountAndSymbol(any(), any())).thenReturn(null);
            when(holdingRepository.save(any(AccountHolding.class))).thenReturn(new AccountHolding());

            TradeResult result = tradeService.buyShares("Warren", "AAPL", quantity, 1L);

            assertNotNull(result);
            assertEquals(0.0, result.newBalance());
            assertEquals(0.0, testAccount.getBalance());

            ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
            verify(transactionRepository).save(transactionCaptor.capture());

            AccountTransaction savedTransaction = transactionCaptor.getValue();
            assertAll(
                    "Transaction should have correct fields for exact balance depletion",
                    () -> assertEquals(testAccount, savedTransaction.getAccount()),
                    () -> assertEquals("AAPL", savedTransaction.getSymbol()),
                    () -> assertEquals(TransactionType.BUY, savedTransaction.getTransactionType()),
                    () -> assertEquals(quantity, savedTransaction.getQuantity()),
                    () -> assertEquals(price, savedTransaction.getPrice()));

            ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
            verify(holdingRepository).save(holdingCaptor.capture());

            AccountHolding savedHolding = holdingCaptor.getValue();
            assertAll(
                    "Holding should have correct fields for exact balance depletion",
                    () -> assertEquals(testAccount, savedHolding.getAccount()),
                    () -> assertEquals("AAPL", savedHolding.getSymbol()),
                    () -> assertEquals(quantity, savedHolding.getQuantity()),
                    () -> assertEquals(price, savedHolding.getAveragePrice()));
        }

        @Test
        @DisplayName("Should handle fractional dollar amounts correctly")
        void testExecuteBuy_FractionalDollars_CorrectCalculation() {
            Double initialBalance = 10000.75;
            Double price = 33.33;
            Integer quantity = 15;
            Double expectedBalance = 9500.80;

            testAccount.setBalance(initialBalance);

            when(tradingAccountRepository.findByAgentName("Warren")).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findActiveHoldingsByAccount(testAccount)).thenReturn(new ArrayList<>());
            when(marketService.getSharePrice("AAPL"))
                    .thenReturn(new MarketService.PriceData(price, true, Instant.now(), "Finnhub"));
            when(tradingAccountRepository.save(any(TradingAccount.class))).thenReturn(testAccount);
            when(transactionRepository.save(any(AccountTransaction.class))).thenReturn(new AccountTransaction());
            when(holdingRepository.findByAccountAndSymbol(any(), any())).thenReturn(null);
            when(holdingRepository.save(any(AccountHolding.class))).thenReturn(new AccountHolding());

            TradeResult result = tradeService.buyShares("Warren", "AAPL", quantity, 1L);

            assertEquals(expectedBalance, result.newBalance(), 0.01);
            assertEquals(expectedBalance, testAccount.getBalance(), 0.01);

            ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
            verify(transactionRepository).save(transactionCaptor.capture());

            AccountTransaction savedTransaction = transactionCaptor.getValue();
            assertAll(
                    "Transaction should have correct fields for fractional dollars",
                    () -> assertEquals(testAccount, savedTransaction.getAccount()),
                    () -> assertEquals("AAPL", savedTransaction.getSymbol()),
                    () -> assertEquals(TransactionType.BUY, savedTransaction.getTransactionType()),
                    () -> assertEquals(quantity, savedTransaction.getQuantity()),
                    () -> assertEquals(
                            price, savedTransaction.getPrice(), 0.01, "Price should match fractional value"));

            ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
            verify(holdingRepository).save(holdingCaptor.capture());

            AccountHolding savedHolding = holdingCaptor.getValue();
            assertAll(
                    "Holding should have correct fields for fractional dollars",
                    () -> assertEquals(testAccount, savedHolding.getAccount()),
                    () -> assertEquals("AAPL", savedHolding.getSymbol()),
                    () -> assertEquals(quantity, savedHolding.getQuantity()),
                    () -> assertEquals(
                            price,
                            savedHolding.getAveragePrice(),
                            0.01,
                            "Average price should match fractional value"));
        }
    }

    @Nested
    @DisplayName("sellShares")
    class SellTests {

        // ========== HAPPY PATH TESTS ==========

        @Test
        @DisplayName("Should sell partial shares successfully when all validations pass")
        void testExecuteSell_AllValidationPass_Success() {
            String agentName = "Warren";
            String symbol = "AAPL";
            Integer existingQuantity = 20;
            Double averagePrice = 100.0;
            Integer sellQuantity = 10;
            Double marketPrice = 150.0;
            Double expectedBalance = 11500.0;
            Integer expectedRemainingQuantity = 10;

            AccountHolding existingHolding = new AccountHolding(testAccount, symbol, existingQuantity, averagePrice);

            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findByAccountAndSymbol(testAccount, symbol)).thenReturn(existingHolding);
            when(marketService.getSharePrice(symbol))
                    .thenReturn(new MarketService.PriceData(marketPrice, true, Instant.now(), "Finnhub"));
            when(tradingAccountRepository.save(any(TradingAccount.class))).thenReturn(testAccount);
            when(transactionRepository.save(any(AccountTransaction.class))).thenReturn(new AccountTransaction());
            when(holdingRepository.save(any(AccountHolding.class))).thenReturn(existingHolding);

            TradeResult result = tradeService.sellShares(agentName, symbol, sellQuantity, 1L);

            assertNotNull(result);
            assertEquals(symbol, result.symbol());
            assertEquals(sellQuantity, result.quantity());
            assertEquals(marketPrice, result.price());
            assertEquals(expectedBalance, result.newBalance());

            verify(tradingAccountRepository).save(testAccount);
            assertEquals(expectedBalance, testAccount.getBalance());

            ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
            verify(transactionRepository).save(transactionCaptor.capture());

            AccountTransaction savedTransaction = transactionCaptor.getValue();
            assertAll(
                    "Transaction should have correct business logic fields",
                    () -> assertEquals(testAccount, savedTransaction.getAccount(), "Account should match"),
                    () -> assertEquals(symbol, savedTransaction.getSymbol(), "Symbol should match"),
                    () -> assertEquals(
                            TransactionType.SELL,
                            savedTransaction.getTransactionType(),
                            "Transaction type should be SELL"),
                    () -> assertEquals(sellQuantity, savedTransaction.getQuantity(), "Quantity should match"),
                    () -> assertEquals(marketPrice, savedTransaction.getPrice(), "Price should match"),
                    () -> assertNotNull(savedTransaction.getTimestamp(), "Timestamp should be set"));

            ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
            verify(holdingRepository).save(holdingCaptor.capture());
            verify(holdingRepository, never()).delete(any());

            AccountHolding savedHolding = holdingCaptor.getValue();
            assertAll(
                    "Holding should have correct business logic fields",
                    () -> assertEquals(testAccount, savedHolding.getAccount(), "Account should match"),
                    () -> assertEquals(symbol, savedHolding.getSymbol(), "Symbol should match"),
                    () -> assertEquals(
                            expectedRemainingQuantity, savedHolding.getQuantity(), "Quantity should be reduced"),
                    () -> assertEquals(
                            averagePrice, savedHolding.getAveragePrice(), "Average price should remain unchanged"));
        }

        @Test
        @DisplayName("Should delete holding when selling all shares")
        void testExecuteSell_SellAllShares_DeletesHolding() {
            String agentName = "Warren";
            String symbol = "AAPL";
            Integer quantity = 10;
            Double averagePrice = 100.0;

            AccountHolding existingHolding = new AccountHolding(testAccount, symbol, quantity, averagePrice);

            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findByAccountAndSymbol(testAccount, symbol)).thenReturn(existingHolding);
            when(marketService.getSharePrice(symbol))
                    .thenReturn(new MarketService.PriceData(150.0, true, Instant.now(), "Finnhub"));
            when(tradingAccountRepository.save(any(TradingAccount.class))).thenReturn(testAccount);
            when(transactionRepository.save(any(AccountTransaction.class))).thenReturn(new AccountTransaction());

            TradeResult result = tradeService.sellShares(agentName, symbol, quantity, 1L);

            assertNotNull(result);
            assertEquals(symbol, result.symbol());
            assertEquals(quantity, result.quantity());

            verify(holdingRepository).delete(existingHolding);
            verify(holdingRepository, never()).save(any());

            verify(transactionRepository).save(any(AccountTransaction.class));

            verify(tradingAccountRepository).save(testAccount);
        }

        @Test
        @DisplayName("Should update quantity only when selling partial shares")
        void testExecuteSell_PartialSale_UpdatesQuantityOnly() {
            String agentName = "Warren";
            String symbol = "AAPL";
            Integer existingQuantity = 50;
            Double averagePrice = 100.0;
            Integer sellQuantity = 20;
            Integer expectedQuantity = 30;

            AccountHolding existingHolding = new AccountHolding(testAccount, symbol, existingQuantity, averagePrice);

            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findByAccountAndSymbol(testAccount, symbol)).thenReturn(existingHolding);
            when(marketService.getSharePrice(symbol))
                    .thenReturn(new MarketService.PriceData(150.0, true, Instant.now(), "Finnhub"));
            when(tradingAccountRepository.save(any(TradingAccount.class))).thenReturn(testAccount);
            when(transactionRepository.save(any(AccountTransaction.class))).thenReturn(new AccountTransaction());
            when(holdingRepository.save(any(AccountHolding.class))).thenReturn(existingHolding);

            TradeResult result = tradeService.sellShares(agentName, symbol, sellQuantity, 1L);

            assertNotNull(result);

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
            String agentName = "Warren";
            String symbol = "AAPL";
            Integer quantity = 10;

            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findByAccountAndSymbol(testAccount, symbol)).thenReturn(null);

            BusinessRuleException exception = assertThrows(BusinessRuleException.class, () -> {
                tradeService.sellShares(agentName, symbol, quantity, 1L);
            });

            assertTrue(exception.getMessage().contains("Cannot sell " + quantity + " shares of " + symbol));
            assertTrue(exception.getMessage().contains("Only have 0 shares available"));

            verify(marketService, never()).getSharePrice(any());
            verify(tradingAccountRepository, never()).save(any());
            verify(transactionRepository, never()).save(any());
            verify(holdingRepository, never()).save(any());
            verify(holdingRepository, never()).delete(any());
            verifyNoInteractions(portfolioSnapshotService);
        }

        @Test
        @DisplayName("Should throw RuntimeException when insufficient shares available")
        void testExecuteSell_InsufficientShares_ThrowsException() {
            String agentName = "Warren";
            String symbol = "AAPL";
            Integer availableQuantity = 5;
            Integer sellQuantity = 10;

            AccountHolding existingHolding = new AccountHolding(testAccount, symbol, availableQuantity, 100.0);

            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findByAccountAndSymbol(testAccount, symbol)).thenReturn(existingHolding);

            BusinessRuleException exception = assertThrows(BusinessRuleException.class, () -> {
                tradeService.sellShares(agentName, symbol, sellQuantity, 1L);
            });

            assertTrue(exception.getMessage().contains("Cannot sell " + sellQuantity + " shares of " + symbol));
            assertTrue(exception.getMessage().contains("Only have " + availableQuantity + " shares available"));

            verify(marketService, never()).getSharePrice(any());
            verify(tradingAccountRepository, never()).save(any());
            verify(transactionRepository, never()).save(any());
            verify(holdingRepository, never()).save(any());
            verify(holdingRepository, never()).delete(any());
            verifyNoInteractions(portfolioSnapshotService);
        }

        @Test
        @DisplayName("Should throw RuntimeException when account not found")
        void testExecuteSell_AccountNotFound_ThrowsException() {
            String agentName = "NonExistent";
            String symbol = "AAPL";
            Integer quantity = 10;

            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.empty());

            ResourceNotFoundException exception = assertThrows(ResourceNotFoundException.class, () -> {
                tradeService.sellShares(agentName, symbol, quantity, 1L);
            });

            assertEquals(
                    "Trading account not found for agent: " + agentName
                            + ". Agent must be initialized before trading operations.",
                    exception.getMessage());

            verify(holdingRepository, never()).findByAccountAndSymbol(any(), any());
            verify(marketService, never()).getSharePrice(any());
            verify(transactionRepository, never()).save(any());
            verify(holdingRepository, never()).save(any());
            verify(holdingRepository, never()).delete(any());
            verifyNoInteractions(portfolioSnapshotService);
        }

        @Test
        @DisplayName("Should throw IllegalArgumentException when runId is null")
        void testExecuteSell_NullRunId_ThrowsException() {
            String agentName = "Warren";
            String symbol = "AAPL";
            Integer quantity = 10;
            Long runId = null;

            IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
                tradeService.sellShares(agentName, symbol, quantity, runId);
            });

            assertEquals(
                    "runId is required - every transaction must be linked to an agent run", exception.getMessage());

            verify(tradingAccountRepository, never()).findByAgentName(any());
            verify(holdingRepository, never()).findByAccountAndSymbol(any(), any());
            verify(marketService, never()).getSharePrice(any());
            verify(tradingAccountRepository, never()).save(any());
            verify(transactionRepository, never()).save(any());
            verify(holdingRepository, never()).save(any());
            verify(holdingRepository, never()).delete(any());
            verifyNoInteractions(portfolioSnapshotService);
        }

        // ========== EDGE CASES ==========

        @Test
        @DisplayName("Should handle selling exactly all remaining shares")
        void testExecuteSell_ExactShareDepletion_Success() {
            Integer exactQuantity = 10;

            AccountHolding existingHolding = new AccountHolding(testAccount, "AAPL", exactQuantity, 100.0);

            when(tradingAccountRepository.findByAgentName("Warren")).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findByAccountAndSymbol(testAccount, "AAPL")).thenReturn(existingHolding);
            when(marketService.getSharePrice("AAPL"))
                    .thenReturn(new MarketService.PriceData(150.0, true, Instant.now(), "Finnhub"));
            when(tradingAccountRepository.save(any(TradingAccount.class))).thenReturn(testAccount);
            when(transactionRepository.save(any(AccountTransaction.class))).thenReturn(new AccountTransaction());

            TradeResult result = tradeService.sellShares("Warren", "AAPL", exactQuantity, 1L);

            assertNotNull(result);
            assertEquals("AAPL", result.symbol());

            verify(holdingRepository).delete(existingHolding);
            verify(holdingRepository, never()).save(any());

            ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
            verify(transactionRepository).save(transactionCaptor.capture());

            AccountTransaction savedTransaction = transactionCaptor.getValue();
            assertAll(
                    "Transaction should have correct fields for exact share depletion",
                    () -> assertEquals(testAccount, savedTransaction.getAccount()),
                    () -> assertEquals("AAPL", savedTransaction.getSymbol()),
                    () -> assertEquals(TransactionType.SELL, savedTransaction.getTransactionType()),
                    () -> assertEquals(exactQuantity, savedTransaction.getQuantity()),
                    () -> assertEquals(150.0, savedTransaction.getPrice()));
        }

        @Test
        @DisplayName("Should handle fractional dollar amounts correctly")
        void testExecuteSell_FractionalDollars_CorrectCalculation() {
            Double initialBalance = 10000.25;
            Double price = 150.75;
            Integer quantity = 10;
            Double expectedBalance = 11507.75;

            testAccount.setBalance(initialBalance);

            AccountHolding existingHolding = new AccountHolding(testAccount, "AAPL", 20, 100.0);

            when(tradingAccountRepository.findByAgentName("Warren")).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findByAccountAndSymbol(testAccount, "AAPL")).thenReturn(existingHolding);
            when(marketService.getSharePrice("AAPL"))
                    .thenReturn(new MarketService.PriceData(price, true, Instant.now(), "Finnhub"));
            when(tradingAccountRepository.save(any(TradingAccount.class))).thenReturn(testAccount);
            when(transactionRepository.save(any(AccountTransaction.class))).thenReturn(new AccountTransaction());
            when(holdingRepository.save(any(AccountHolding.class))).thenReturn(existingHolding);

            TradeResult result = tradeService.sellShares("Warren", "AAPL", quantity, 1L);

            assertEquals(expectedBalance, result.newBalance(), 0.01);
            assertEquals(expectedBalance, testAccount.getBalance(), 0.01);

            ArgumentCaptor<AccountTransaction> transactionCaptor = ArgumentCaptor.forClass(AccountTransaction.class);
            verify(transactionRepository).save(transactionCaptor.capture());

            AccountTransaction savedTransaction = transactionCaptor.getValue();
            assertAll(
                    "Transaction should have correct fields for fractional dollars",
                    () -> assertEquals(testAccount, savedTransaction.getAccount()),
                    () -> assertEquals("AAPL", savedTransaction.getSymbol()),
                    () -> assertEquals(TransactionType.SELL, savedTransaction.getTransactionType()),
                    () -> assertEquals(quantity, savedTransaction.getQuantity()),
                    () -> assertEquals(
                            price, savedTransaction.getPrice(), 0.01, "Price should match fractional value"));
        }

        @Test
        @DisplayName("Should keep average price unchanged after selling shares")
        void testExecuteSell_AveragePriceUnchanged_AfterSell() {
            String symbol = "AAPL";
            Integer existingQuantity = 50;
            Double originalAveragePrice = 100.0;
            Integer sellQuantity = 20;
            Integer expectedQuantity = 30;

            AccountHolding existingHolding =
                    new AccountHolding(testAccount, symbol, existingQuantity, originalAveragePrice);

            when(tradingAccountRepository.findByAgentName("Warren")).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findByAccountAndSymbol(testAccount, symbol)).thenReturn(existingHolding);
            when(marketService.getSharePrice(symbol))
                    .thenReturn(new MarketService.PriceData(150.0, true, Instant.now(), "Finnhub"));
            when(tradingAccountRepository.save(any(TradingAccount.class))).thenReturn(testAccount);
            when(transactionRepository.save(any(AccountTransaction.class))).thenReturn(new AccountTransaction());
            when(holdingRepository.save(any(AccountHolding.class))).thenReturn(existingHolding);

            tradeService.sellShares("Warren", symbol, sellQuantity, 1L);

            ArgumentCaptor<AccountHolding> holdingCaptor = ArgumentCaptor.forClass(AccountHolding.class);
            verify(holdingRepository).save(holdingCaptor.capture());

            AccountHolding updatedHolding = holdingCaptor.getValue();
            assertEquals(expectedQuantity, updatedHolding.getQuantity(), "Quantity should be reduced");
            assertEquals(
                    originalAveragePrice, updatedHolding.getAveragePrice(), "Average price should remain unchanged");
        }
    }
}
