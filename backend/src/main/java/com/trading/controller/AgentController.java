package com.trading.controller;

import com.trading.dto.AgentDetailDto;
import com.trading.dto.AgentRunDto;
import com.trading.dto.AgentSummaryDto;
import com.trading.entity.AgentRun;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.repository.AgentRunRepository;
import com.trading.repository.TradingAccountRepository;
import com.trading.repository.TradingAgentRepository;
import com.trading.service.AccountService;
import com.trading.service.AgentIdentityService;
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

    @Autowired
    private TradingAccountRepository accountRepository;

    @Autowired
    private AccountService accountService;

    @Autowired
    private AgentRunRepository runRepository;

    @Autowired
    private AgentIdentityService agentIdentityService;

    @GetMapping
    public ResponseEntity<List<AgentSummaryDto>> listAgents() {
        try {
            List<AgentSummaryDto> summaries = agentRepository.findAll().stream()
                    .map(agent -> new AgentSummaryDto(
                            agent.getId(),
                            agent.getName(),
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

    @GetMapping("/{agentId}")
    public ResponseEntity<AgentDetailDto> getAgentDetail(@PathVariable Long agentId) {
        try {
            TradingAgent agent = agentIdentityService.requireAgent(agentId);
            String name = agent.getName();

            // Get account for portfolio info
            TradingAccount account = accountRepository.findByName(name);
            if (account == null) {
                throw new RuntimeException("Account not found for agent: " + name);
            }

            // Build portfolio info
            Double cashBalance = account.getBalance();
            var holdings = accountService.getHoldings(name);
            Double totalValue = accountService.getTotalPortfolioValue(name);
            Double initialCapital = agent.getInitialCapital() != null ? agent.getInitialCapital() : 100000.0;
            Double totalReturn = totalValue - initialCapital;
            Double totalReturnPercent = (totalReturn / initialCapital) * 100;

            AgentDetailDto.PortfolioInfo portfolio = new AgentDetailDto.PortfolioInfo(
                    cashBalance,
                    holdings,
                    totalValue,
                    totalReturn,
                    totalReturnPercent
            );

            // Get recent runs (last 10)
            List<AgentRun> runs = runRepository.findByAgentNameOrderByStartTimeDesc(name)
                    .stream()
                    .limit(10)
                    .collect(Collectors.toList());

            List<AgentDetailDto.RunSummary> runSummaries = runs.stream()
                    .map(r -> new AgentDetailDto.RunSummary(
                            r.getId(),
                            r.getRunType(),
                            r.getOutcome(),
                            r.getStartTime().toString(),
                            r.getTradeCount(),
                            r.getSummary()
                    ))
                    .collect(Collectors.toList());

            // Build response (use description as strategy for now)
            String strategy = agent.getDescription() != null ? agent.getDescription() : "No strategy defined";
            AgentDetailDto detail = new AgentDetailDto(
                    agent.getId(),
                    agent.getName(),
                    strategy,
                    initialCapital,
                    portfolio,
                    runSummaries
            );

            return ResponseEntity.ok(detail);
        } catch (Exception e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @GetMapping("/{agentId}/runs")
    public ResponseEntity<List<AgentRunDto>> getAgentRuns(
            @PathVariable Long agentId,
            @RequestParam(defaultValue = "10") int limit) {
        try {
            TradingAgent agent = agentIdentityService.requireAgent(agentId);
            String name = agent.getName();
            List<AgentRun> runs = runRepository.findByAgentNameOrderByStartTimeDesc(name)
                    .stream()
                    .limit(limit)
                    .collect(Collectors.toList());

            List<AgentRunDto> runDtos = runs.stream()
                    .map(AgentRunDto::fromEntity)
                    .collect(Collectors.toList());

            return ResponseEntity.ok(runDtos);
        } catch (Exception e) {
            return ResponseEntity.badRequest().build();
        }
    }
}
