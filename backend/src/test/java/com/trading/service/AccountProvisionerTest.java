package com.trading.service;

import com.trading.config.AgentProperties;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.exception.ResourceNotFoundException;
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
@DisplayName("AccountProvisioner Tests")
@SuppressWarnings("null")
class AccountProvisionerTest {

    @Mock
    private TradingAgentRepository agentRepository;

    @Mock
    private TradingAccountRepository tradingAccountRepository;

    @Mock
    private AgentProperties agentProperties;

    @InjectMocks
    private AccountProvisioner accountProvisioner;

    private TradingAgent testAgent;
    private TradingAccount testAccount;

    @BeforeEach
    void setUp() {
        testAgent = new TradingAgent("TestAgent", "Test trading agent");
        testAgent.setId(1L);

        testAccount = new TradingAccount(testAgent, 100000.0);
        testAccount.setId(1L);
    }

    // ==================== initializeAgent ====================

    @Test
    @DisplayName("Should return existing account when both agent and account exist")
    void testInitializeAgent_AgentExistsAccountExists_ReturnsExisting() {
        String agentName = "TestAgent";
        Double initialBalance = 100000.0;

        when(agentRepository.findByName(agentName))
            .thenReturn(Optional.of(testAgent));
        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));

        TradingAccount result = accountProvisioner.initializeAgent(agentName, initialBalance);

        assertNotNull(result);
        assertEquals(testAccount.getId(), result.getId());
        assertEquals(testAccount.getBalance(), result.getBalance());

        verify(tradingAccountRepository, never()).save(any());
        verify(agentRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should create new account when agent exists but account does not")
    void testInitializeAgent_AgentExistsAccountMissing_CreatesNewAccount() {
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

        TradingAccount result = accountProvisioner.initializeAgent(agentName, initialBalance);

        assertNotNull(result);
        assertEquals(initialBalance, result.getBalance());
        assertEquals(testAgent.getId(), result.getAgent().getId());

        ArgumentCaptor<TradingAccount> accountCaptor = ArgumentCaptor.forClass(TradingAccount.class);
        verify(tradingAccountRepository, times(1)).save(accountCaptor.capture());

        TradingAccount capturedAccount = accountCaptor.getValue();
        assertEquals(testAgent.getId(), capturedAccount.getAgent().getId());
        assertEquals(initialBalance, capturedAccount.getBalance());

        verify(agentRepository, never()).save(any());
    }

    @Test
    @DisplayName("Should create new agent and account when neither exist")
    void testInitializeAgent_AgentMissing_CreatesNewAgentAndAccount() {
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

        TradingAccount result = accountProvisioner.initializeAgent(agentName, initialBalance);

        assertNotNull(result);
        assertEquals(initialBalance, result.getBalance());
        assertEquals(newAgent.getId(), result.getAgent().getId());

        ArgumentCaptor<TradingAgent> agentCaptor = ArgumentCaptor.forClass(TradingAgent.class);
        verify(agentRepository, times(1)).save(agentCaptor.capture());

        TradingAgent capturedAgent = agentCaptor.getValue();
        assertEquals(agentName, capturedAgent.getName());
        assertEquals("Autonomous trading agent", capturedAgent.getDescription());
        assertEquals(initialBalance, capturedAgent.getInitialCapital());

        ArgumentCaptor<TradingAccount> accountCaptor = ArgumentCaptor.forClass(TradingAccount.class);
        verify(tradingAccountRepository, times(1)).save(accountCaptor.capture());

        TradingAccount capturedAccount = accountCaptor.getValue();
        assertEquals(newAgent.getId(), capturedAccount.getAgent().getId());
        assertEquals(initialBalance, capturedAccount.getBalance());
    }

    @Test
    @DisplayName("Should set style for known agent on creation")
    void testInitializeAgent_KnownAgent_SetsStyle() {
        String agentName = "Warren";
        Double initialBalance = 100000.0;

        when(agentRepository.findByName(agentName))
            .thenReturn(Optional.empty());
        when(agentProperties.getStyle(agentName))
            .thenReturn(Optional.of("Value Investor"));

        TradingAgent savedAgent = new TradingAgent(agentName, "Autonomous trading agent");
        savedAgent.setId(1L);
        savedAgent.setStyle("Value Investor");
        when(agentRepository.save(any(TradingAgent.class)))
            .thenReturn(savedAgent);

        TradingAccount newAccount = new TradingAccount(savedAgent, initialBalance);
        newAccount.setId(1L);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(newAccount);

        accountProvisioner.initializeAgent(agentName, initialBalance);

        ArgumentCaptor<TradingAgent> agentCaptor = ArgumentCaptor.forClass(TradingAgent.class);
        verify(agentRepository, times(1)).save(agentCaptor.capture());

        TradingAgent saved = agentCaptor.getValue();
        assertEquals("Value Investor", saved.getStyle());
    }

    @Test
    @DisplayName("Should backfill style for existing agent with missing style")
    void testInitializeAgent_ExistingAgentMissingStyle_BackfillsStyle() {
        String agentName = "Warren";
        Double initialBalance = 100000.0;

        TradingAgent existingAgent = new TradingAgent(agentName, "Autonomous trading agent");
        existingAgent.setId(1L);
        existingAgent.setStyle(null);

        when(agentRepository.findByName(agentName))
            .thenReturn(Optional.of(existingAgent));
        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));
        when(agentProperties.getStyle(agentName))
            .thenReturn(Optional.of("Value Investor"));

        accountProvisioner.initializeAgent(agentName, initialBalance);

        verify(agentRepository, never()).save(any());
        assertEquals("Value Investor", existingAgent.getStyle());
    }

    @Test
    @DisplayName("Should leave style unset when AgentProperties returns Optional.empty")
    void testInitializeAgent_UnknownAgentStyle_LeavesStyleUnset() {
        String agentName = "Mystery";
        Double initialBalance = 100000.0;

        when(agentRepository.findByName(agentName))
            .thenReturn(Optional.empty());
        when(agentProperties.getStyle(agentName))
            .thenReturn(Optional.empty());

        TradingAgent savedAgent = new TradingAgent(agentName, "Autonomous trading agent");
        savedAgent.setId(5L);
        when(agentRepository.save(any(TradingAgent.class)))
            .thenReturn(savedAgent);

        TradingAccount newAccount = new TradingAccount(savedAgent, initialBalance);
        newAccount.setId(5L);
        when(tradingAccountRepository.save(any(TradingAccount.class)))
            .thenReturn(newAccount);

        accountProvisioner.initializeAgent(agentName, initialBalance);

        ArgumentCaptor<TradingAgent> agentCaptor = ArgumentCaptor.forClass(TradingAgent.class);
        verify(agentRepository, times(1)).save(agentCaptor.capture());

        TradingAgent saved = agentCaptor.getValue();
        assertNull(saved.getStyle());
    }

    @Test
    @DisplayName("Should not overwrite a pre-existing style even when AgentProperties has a value")
    void testInitializeAgent_AgentAlreadyHasStyle_DoesNotOverwrite() {
        String agentName = "Warren";
        Double initialBalance = 100000.0;

        TradingAgent existingAgent = new TradingAgent(agentName, "Autonomous trading agent");
        existingAgent.setId(1L);
        existingAgent.setStyle("Pre-existing Style");

        when(agentRepository.findByName(agentName))
            .thenReturn(Optional.of(existingAgent));
        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));

        accountProvisioner.initializeAgent(agentName, initialBalance);

        assertEquals("Pre-existing Style", existingAgent.getStyle());
        verify(agentProperties, never()).getStyle(any());
    }

    @Test
    @DisplayName("Should preserve existing balance when calling initialize again on existing agent")
    void testInitializeAgent_MultipleCallsSameAgent_PreservesOriginalBalance() {
        String agentName = "TestAgent";
        Double originalBalance = 100000.0;
        Double newBalance = 500000.0;

        when(agentRepository.findByName(agentName))
            .thenReturn(Optional.of(testAgent));
        when(tradingAccountRepository.findByAgentName(agentName))
            .thenReturn(Optional.of(testAccount));

        TradingAccount result = accountProvisioner.initializeAgent(agentName, newBalance);

        assertNotNull(result);
        assertEquals(originalBalance, result.getBalance());

        verify(tradingAccountRepository, never()).save(any());
        verify(agentRepository, never()).save(any());
    }

    // ==================== updateAgentActivity ====================

    @Test
    @DisplayName("updateAgentActivity finds agent, calls updateActivity, and saves")
    void testUpdateAgentActivity_AgentExists_SavesUpdatedActivity() {
        String agentName = "TestAgent";

        when(agentRepository.findByName(agentName))
            .thenReturn(Optional.of(testAgent));

        accountProvisioner.updateAgentActivity(agentName);

        verify(agentRepository, times(1)).save(testAgent);
    }

    @Test
    @DisplayName("updateAgentActivity throws ResourceNotFoundException when agent is missing")
    void testUpdateAgentActivity_AgentMissing_ThrowsResourceNotFoundException() {
        String agentName = "NonExistent";

        when(agentRepository.findByName(agentName))
            .thenReturn(Optional.empty());

        ResourceNotFoundException ex = assertThrows(
            ResourceNotFoundException.class,
            () -> accountProvisioner.updateAgentActivity(agentName)
        );
        assertTrue(ex.getMessage().contains(agentName));
        verify(agentRepository, never()).save(any());
    }
}
