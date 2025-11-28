package com.trading.service;

import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.repository.TradingAccountRepository;
import com.trading.repository.TradingAgentRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("AccountService.initializeAgent Tests")
@SuppressWarnings("null")
class AccountServiceTest {

    @Mock
    private TradingAgentRepository agentRepository;

    @Mock
    private TradingAccountRepository tradingAccountRepository;

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
        RuntimeException exception = assertThrows(RuntimeException.class, () -> {
            accountService.getBalance(agentName);
        });

        assertEquals("Trading account not found for agent: " + agentName +
            ". Agent must be initialized before trading operations.", exception.getMessage());
    }
}

