package com.trading.service;

import com.trading.dto.response.HoldingDto;
import com.trading.dto.response.TradeResult;
import com.trading.dto.websocket.TradeExecutedMessage;
import com.trading.dto.websocket.TradeRejectedMessage;
import com.trading.entity.AccountHolding;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.entity.TradingRun;
import com.trading.enums.TradeRejectionType;
import com.trading.enums.WebSocketMessageType;
import com.trading.exception.BusinessRuleException;
import com.trading.repository.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.messaging.simp.SimpMessagingTemplate;
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
    private AccountPortfolioSnapshotRepository snapshotRepository;

    @Mock
    private TradingRunRepository tradingRunRepository;

    @Mock
    private MarketService marketService;

    @Mock
    private BuyTradeExecutor buyTradeExecutor;

    @Mock
    private SellTradeExecutor sellTradeExecutor;

    @Mock
    private SimpMessagingTemplate messagingTemplate;

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

        // Verify agent was saved with correct properties
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

    // ==================== WebSocket Broadcast Tests ====================

    @Nested
    @DisplayName("buyShares WebSocket Broadcasts")
    class BuySharesBroadcastTests {

        private TradingRun testRun;

        @BeforeEach
        void setUp() {
            testRun = new TradingRun();
            testRun.setId(100L);
            testRun.setAgent(testAgent);
        }

        @Test
        @DisplayName("Successful buy broadcasts trade_executed message")
        void buyShares_Success_BroadcastsTradeExecuted() {
            // Arrange
            String agentName = "TestAgent";
            String symbol = "AAPL";
            Integer quantity = 10;
            Long runId = 100L;
            TradeResult tradeResult = new TradeResult(symbol, quantity, 150.0, 98500.0);

            when(tradingRunRepository.findById(runId)).thenReturn(Optional.of(testRun));
            when(buyTradeExecutor.executeBuy(agentName, symbol, quantity, runId)).thenReturn(tradeResult);
            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findByAccount(testAccount)).thenReturn(Collections.emptyList());

            // Act
            accountService.buyShares(agentName, symbol, quantity, runId);

            // Assert - verify broadcast was sent
            ArgumentCaptor<TradeExecutedMessage> messageCaptor = ArgumentCaptor.forClass(TradeExecutedMessage.class);
            verify(messagingTemplate).convertAndSend(eq("/topic/runs/trades"), messageCaptor.capture());

            TradeExecutedMessage message = messageCaptor.getValue();
            assertEquals(WebSocketMessageType.TRADE_EXECUTED, message.getType());
            assertEquals(testAgent.getId(), message.getAgentId());
            assertEquals(runId, message.getRunId());
            assertEquals("buy", message.getTrade().getSide());
            assertEquals(symbol, message.getTrade().getSymbol());
            assertEquals(quantity, message.getTrade().getQuantity());
            assertEquals(150.0, message.getTrade().getPrice());
        }

        @Test
        @DisplayName("Failed buy (insufficient funds) broadcasts trade_rejected message")
        void buyShares_InsufficientFunds_BroadcastsTradeRejected() {
            // Arrange
            String agentName = "TestAgent";
            String symbol = "AAPL";
            Integer quantity = 1000;
            Long runId = 100L;

            when(tradingRunRepository.findById(runId)).thenReturn(Optional.of(testRun));
            when(buyTradeExecutor.executeBuy(agentName, symbol, quantity, runId))
                .thenThrow(new BusinessRuleException(TradeRejectionType.INSUFFICIENT_FUNDS, "Insufficient funds to buy 1000 shares of AAPL"));

            // Act & Assert
            assertThrows(BusinessRuleException.class, () -> {
                accountService.buyShares(agentName, symbol, quantity, runId);
            });

            // Verify broadcast was sent
            ArgumentCaptor<TradeRejectedMessage> messageCaptor = ArgumentCaptor.forClass(TradeRejectedMessage.class);
            verify(messagingTemplate).convertAndSend(eq("/topic/runs/trades"), messageCaptor.capture());

            TradeRejectedMessage message = messageCaptor.getValue();
            assertEquals(WebSocketMessageType.TRADE_REJECTED, message.getType());
            assertEquals(testAgent.getId(), message.getAgentId());
            assertEquals(runId, message.getRunId());
            assertEquals(TradeRejectionType.INSUFFICIENT_FUNDS, message.getRejectionType());
            assertTrue(message.getRejectionMessage().contains("Insufficient funds"));
        }
    }

    @Nested
    @DisplayName("sellShares WebSocket Broadcasts")
    class SellSharesBroadcastTests {

        private TradingRun testRun;

        @BeforeEach
        void setUp() {
            testRun = new TradingRun();
            testRun.setId(100L);
            testRun.setAgent(testAgent);
        }

        @Test
        @DisplayName("Successful sell broadcasts trade_executed message")
        void sellShares_Success_BroadcastsTradeExecuted() {
            // Arrange
            String agentName = "TestAgent";
            String symbol = "AAPL";
            Integer quantity = 5;
            Long runId = 100L;
            TradeResult tradeResult = new TradeResult(symbol, quantity, 155.0, 100775.0);

            when(tradingRunRepository.findById(runId)).thenReturn(Optional.of(testRun));
            when(sellTradeExecutor.executeSell(agentName, symbol, quantity, runId)).thenReturn(tradeResult);
            when(tradingAccountRepository.findByAgentName(agentName)).thenReturn(Optional.of(testAccount));
            when(holdingRepository.findByAccount(testAccount)).thenReturn(Collections.emptyList());

            // Act
            accountService.sellShares(agentName, symbol, quantity, runId);

            // Assert - verify broadcast was sent
            ArgumentCaptor<TradeExecutedMessage> messageCaptor = ArgumentCaptor.forClass(TradeExecutedMessage.class);
            verify(messagingTemplate).convertAndSend(eq("/topic/runs/trades"), messageCaptor.capture());

            TradeExecutedMessage message = messageCaptor.getValue();
            assertEquals(WebSocketMessageType.TRADE_EXECUTED, message.getType());
            assertEquals(testAgent.getId(), message.getAgentId());
            assertEquals(runId, message.getRunId());
            assertEquals("sell", message.getTrade().getSide());
            assertEquals(symbol, message.getTrade().getSymbol());
            assertEquals(quantity, message.getTrade().getQuantity());
            assertEquals(155.0, message.getTrade().getPrice());
        }

        @Test
        @DisplayName("Failed sell (insufficient shares) broadcasts trade_rejected message")
        void sellShares_InsufficientShares_BroadcastsTradeRejected() {
            // Arrange
            String agentName = "TestAgent";
            String symbol = "AAPL";
            Integer quantity = 100;
            Long runId = 100L;

            when(tradingRunRepository.findById(runId)).thenReturn(Optional.of(testRun));
            when(sellTradeExecutor.executeSell(agentName, symbol, quantity, runId))
                .thenThrow(new BusinessRuleException(TradeRejectionType.INSUFFICIENT_SHARES, "Insufficient shares to sell 100 of AAPL"));

            // Act & Assert
            assertThrows(BusinessRuleException.class, () -> {
                accountService.sellShares(agentName, symbol, quantity, runId);
            });

            // Verify broadcast was sent
            ArgumentCaptor<TradeRejectedMessage> messageCaptor = ArgumentCaptor.forClass(TradeRejectedMessage.class);
            verify(messagingTemplate).convertAndSend(eq("/topic/runs/trades"), messageCaptor.capture());

            TradeRejectedMessage message = messageCaptor.getValue();
            assertEquals(WebSocketMessageType.TRADE_REJECTED, message.getType());
            assertEquals(testAgent.getId(), message.getAgentId());
            assertEquals(runId, message.getRunId());
            assertEquals(TradeRejectionType.INSUFFICIENT_SHARES, message.getRejectionType());
            assertTrue(message.getRejectionMessage().contains("Insufficient shares"));
        }
    }
}

