package com.trading.controller;

import com.trading.dto.AgentDetailDto;
import com.trading.dto.AgentRunDto;
import com.trading.entity.AgentRun;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.repository.AgentRunRepository;
import com.trading.repository.TradingAccountRepository;
import com.trading.repository.TradingAgentRepository;
import com.trading.service.AccountService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/agents")
@CrossOrigin(origins = {"http://localhost:3000", "http://localhost:5173", "https://agentic-trading.vkontech.com"})
public class AgentController {

    @Autowired
    private TradingAgentRepository agentRepository;

    @Autowired
    private TradingAccountRepository accountRepository;

    @Autowired
    private AccountService accountService;

    @Autowired
    private AgentRunRepository runRepository;

    private static final DateTimeFormatter ISO_FORMATTER = DateTimeFormatter.ISO_INSTANT;

    @GetMapping("/{name}")
    public ResponseEntity<AgentDetailDto> getAgentDetail(@PathVariable String name) {
        try {
            // Get agent
            TradingAgent agent = agentRepository.findByName(name)
                    .orElseThrow(() -> new RuntimeException("Agent not found: " + name));

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

    @GetMapping("/{name}/runs")
    public ResponseEntity<List<AgentRunDto>> getAgentRuns(
            @PathVariable String name,
            @RequestParam(defaultValue = "10") int limit) {
        try {
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
