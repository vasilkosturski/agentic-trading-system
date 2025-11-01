package com.trading.service;

import com.trading.entity.TradingAgent;
import com.trading.repository.TradingAgentRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class AgentIdentityService {

    @Autowired
    private TradingAgentRepository tradingAgentRepository;

    public TradingAgent requireAgent(Long agentId) {
        return tradingAgentRepository.findById(agentId)
                .orElseThrow(() -> new RuntimeException("Agent not found with id: " + agentId));
    }

    public String requireAgentName(Long agentId) {
        return requireAgent(agentId).getName();
    }

    public Long requireAgentIdByName(String agentName) {
        return tradingAgentRepository.findByName(agentName)
                .map(TradingAgent::getId)
                .orElseThrow(() -> new RuntimeException("Agent not found with name: " + agentName));
    }
}

