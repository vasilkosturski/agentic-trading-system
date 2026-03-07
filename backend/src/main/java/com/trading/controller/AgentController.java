package com.trading.controller;

import com.trading.dto.response.AgentSummaryDto;
import com.trading.repository.TradingAgentRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/agents")
public class AgentController {

    @Autowired
    private TradingAgentRepository agentRepository;

    @GetMapping
    public ResponseEntity<List<AgentSummaryDto>> listAgents() {
        try {
            List<AgentSummaryDto> summaries = agentRepository.findAll().stream()
                    .map(agent -> new AgentSummaryDto(
                            agent.getId(),
                            agent.getName(),
                            agent.getStyle(),
                            agent.getDescription(),
                            agent.getIsActive() != null && agent.getIsActive(),
                            agent.getLastActivity() != null ? agent.getLastActivity().toString() : null
                    ))
                    .collect(Collectors.toList());

            return ResponseEntity.ok(summaries);
        } catch (Exception e) {
            return ResponseEntity.badRequest().build();
        }
    }
}
