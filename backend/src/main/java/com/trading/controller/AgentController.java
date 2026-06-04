package com.trading.controller;

import com.trading.dto.response.AgentSummaryDto;
import com.trading.repository.TradingAgentRepository;
import com.trading.service.PromptLoader;
import java.io.IOException;
import java.util.List;
import java.util.stream.Collectors;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/agents")
public class AgentController {

    @Autowired
    private TradingAgentRepository agentRepository;

    @Autowired
    private PromptLoader promptLoader;

    @GetMapping
    @SuppressWarnings("checkstyle:IllegalCatch") // controller boundary maps any downstream failure to HTTP 400
    public ResponseEntity<List<AgentSummaryDto>> listAgents() {
        try {
            List<AgentSummaryDto> summaries = agentRepository.findAll().stream()
                    .map(agent -> new AgentSummaryDto(
                            agent.getId(),
                            agent.getName(),
                            agent.getStyle(),
                            agent.getDescription(),
                            agent.getIsActive() != null && agent.getIsActive(),
                            agent.getLastActivity() != null
                                    ? agent.getLastActivity().toString()
                                    : null,
                            composePromptSafely(agent.getName())))
                    .collect(Collectors.toList());

            return ResponseEntity.ok(summaries);
        } catch (Exception e) {
            return ResponseEntity.badRequest().build();
        }
    }

    private String composePromptSafely(String agentName) {
        try {
            return promptLoader.composePrompt("decision_maker", agentName);
        } catch (IOException e) {
            return null;
        }
    }
}
