package com.trading.service;

import com.trading.config.AgentProperties;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.exception.ResourceNotFoundException;
import com.trading.repository.TradingAccountRepository;
import com.trading.repository.TradingAgentRepository;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * Lifecycle operations for trading agents: initial provisioning of an agent +
 * account pair, and activity-timestamp updates. The lifecycle paths are the
 * only writes against the agent/account aggregates in this part of the system.
 */
@Service
public class AccountProvisioner {

    private static final Logger logger = LoggerFactory.getLogger(AccountProvisioner.class);

    private final TradingAgentRepository agentRepository;
    private final TradingAccountRepository tradingAccountRepository;
    private final AgentProperties agentProperties;

    public AccountProvisioner(
            TradingAgentRepository agentRepository,
            TradingAccountRepository tradingAccountRepository,
            AgentProperties agentProperties) {
        this.agentRepository = agentRepository;
        this.tradingAccountRepository = tradingAccountRepository;
        this.agentProperties = agentProperties;
    }

    /**
     * Initialize agent and create trading account - should be called when agent starts.
     * @param agentName Name of the agent (validated at controller layer)
     * @param initialBalance Initial cash balance (validated at controller layer)
     * @return TradingAccount for the agent
     */
    public TradingAccount initializeAgent(String agentName, Double initialBalance) {
        Optional<TradingAgent> agentOpt = agentRepository.findByName(agentName);

        if (agentOpt.isPresent()) {
            TradingAgent agent = agentOpt.get();
            populateStyle(agent);

            Optional<TradingAccount> accountOpt = tradingAccountRepository.findByAgentName(agentName);
            if (accountOpt.isPresent()) {
                return accountOpt.get();
            }
            return tradingAccountRepository.save(new TradingAccount(agent, initialBalance));
        }

        // Agent doesn't exist - create agent and account
        TradingAgent agent = new TradingAgent(agentName, "Autonomous trading agent");
        agent.setInitialCapital(initialBalance);
        populateStyle(agent);
        agent = agentRepository.save(agent);

        return tradingAccountRepository.save(new TradingAccount(agent, initialBalance));
    }

    /**
     * Update agent activity timestamp (called on every cycle check via trading_system.py).
     * Single source of truth for lastActivity updates.
     */
    public void updateAgentActivity(String agentName) {
        Optional<TradingAgent> agentOpt = agentRepository.findByName(agentName);
        if (agentOpt.isPresent()) {
            TradingAgent agent = agentOpt.get();
            agent.updateActivity();
            agentRepository.save(agent);
            logger.debug("Updated activity timestamp for agent: {}", agentName);
        } else {
            throw new ResourceNotFoundException("Agent not found: " + agentName);
        }
    }

    private void populateStyle(TradingAgent agent) {
        if (agent.getStyle() == null || agent.getStyle().isEmpty()) {
            agentProperties.getStyle(agent.getName()).ifPresent(agent::setStyle);
        }
    }
}
