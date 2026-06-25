package com.trading.service;

import com.trading.entity.TradingAgent;
import com.trading.repository.TradingAgentRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AgentIdentityService {

    @Autowired
    private TradingAgentRepository tradingAgentRepository;

    public TradingAgent requireAgent(Long agentId) {
        return tradingAgentRepository
                .findById(agentId)
                .orElseThrow(
                        () -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Agent not found with id: " + agentId));
    }

    public String requireAgentName(Long agentId) {
        return requireAgent(agentId).getName();
    }
}
