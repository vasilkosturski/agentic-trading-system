package com.trading.controller;

import com.trading.dto.request.InitializeAgentRequest;
import com.trading.dto.response.HoldingDto;
import com.trading.dto.response.PortfolioHistoryPoint;
import com.trading.dto.response.RecentTradeDto;
import com.trading.dto.response.RunDetailDto;
import com.trading.dto.response.ToolResponse;
import com.trading.dto.response.TradeDetailResponse;
import com.trading.dto.response.TradeResult;
import jakarta.validation.Valid;
import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.entity.AccountTransaction;
import com.trading.entity.AgentRun;
import com.trading.repository.AccountPortfolioSnapshotRepository;
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.AgentReasoningStepRepository;
import com.trading.service.AccountService;
import com.trading.service.AgentIdentityService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/accounts")
public class AccountController {

    @Autowired
    private AccountService accountService;
    
    @Autowired
    private AccountPortfolioSnapshotRepository snapshotRepository;
    
    @Autowired
    private AccountTransactionRepository transactionRepository;

    @Autowired
    private AgentReasoningStepRepository reasoningStepRepository;

    @Autowired
    private AgentIdentityService agentIdentityService;

    private String resolveAgentName(Object agentIdValue) {
        if (agentIdValue == null) {
            throw new IllegalArgumentException("agentId is required");
        }
        Long agentId;
        if (agentIdValue instanceof Number number) {
            agentId = number.longValue();
        } else if (agentIdValue instanceof String stringValue) {
            agentId = Long.parseLong(stringValue);
        } else {
            throw new IllegalArgumentException("Invalid agentId value: " + agentIdValue);
        }
        return agentIdentityService.requireAgentName(agentId);
    }

    // Agent initialization endpoint
    @PostMapping("/tools/initialize_agent")
    public ResponseEntity<ToolResponse<String>> initializeAgent(@RequestBody @Valid InitializeAgentRequest request) {
        try {
            accountService.initializeAgent(request.getName(), request.getInitialBalance());
            return ResponseEntity.status(201).body(ToolResponse.success(
                "Successfully initialized agent " + request.getName()));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage()));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(ToolResponse.error("Failed to initialize agent: " + e.getMessage()));
        }
    }

    // MCP Tool endpoints
    @PostMapping("/tools/get_balance")
    public ResponseEntity<ToolResponse<Double>> getBalance(@RequestBody Map<String, Object> request) {
        try {
            String name = resolveAgentName(request.get("agentId"));
            Double balance = accountService.getBalance(name);
            return ResponseEntity.ok(ToolResponse.success(balance));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage()));
        } catch (RuntimeException e) {
            if (e.getMessage() != null && e.getMessage().contains("not found")) {
                return ResponseEntity.status(404).body(ToolResponse.error(e.getMessage()));
            }
            return ResponseEntity.status(500).body(ToolResponse.error("Failed to get balance"));
        }
    }

    @PostMapping("/tools/get_holdings")
    public ResponseEntity<ToolResponse<List<HoldingDto>>> getHoldings(@RequestBody Map<String, Object> request) {
        try {
            String name = resolveAgentName(request.get("agentId"));
            List<HoldingDto> holdings = accountService.getHoldings(name);
            return ResponseEntity.ok(ToolResponse.success(holdings));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage()));
        } catch (RuntimeException e) {
            if (e.getMessage() != null && e.getMessage().contains("not found")) {
                return ResponseEntity.status(404).body(ToolResponse.error(e.getMessage()));
            }
            return ResponseEntity.status(500).body(ToolResponse.error("Failed to get holdings"));
        }
    }

    @PostMapping("/tools/buy_shares")
    public ResponseEntity<ToolResponse<TradeResult>> buyShares(@RequestBody Map<String, Object> request) {
        try {
            String name = resolveAgentName(request.get("agentId"));
            String symbol = (String) request.get("symbol");
            Integer quantity = (Integer) request.get("quantity");
            Long runId = request.get("runId") != null ? ((Number) request.get("runId")).longValue() : null;

            if (runId == null) {
                return ResponseEntity.badRequest().body(ToolResponse.error("runId is required - every transaction must be linked to an agent run"));
            }

            TradeResult result = accountService.buyShares(name, symbol, quantity, runId);
            return ResponseEntity.status(201).body(ToolResponse.success(result));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage()));
        } catch (RuntimeException e) {
            // Business rule violations (insufficient funds, position limit, etc.)
            if (e.getMessage() != null && (e.getMessage().contains("Insufficient") ||
                e.getMessage().contains("maximum") || e.getMessage().contains("limit"))) {
                return ResponseEntity.status(409).body(ToolResponse.error(e.getMessage()));
            }
            return ResponseEntity.status(500).body(ToolResponse.error("Failed to buy shares"));
        }
    }

    @PostMapping("/tools/sell_shares")
    public ResponseEntity<ToolResponse<TradeResult>> sellShares(@RequestBody Map<String, Object> request) {
        try {
            String name = resolveAgentName(request.get("agentId"));
            String symbol = (String) request.get("symbol");
            Integer quantity = (Integer) request.get("quantity");
            Long runId = request.get("runId") != null ? ((Number) request.get("runId")).longValue() : null;

            if (runId == null) {
                return ResponseEntity.badRequest().body(ToolResponse.error("runId is required - every transaction must be linked to an agent run"));
            }

            TradeResult result = accountService.sellShares(name, symbol, quantity, runId);
            return ResponseEntity.status(201).body(ToolResponse.success(result));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage()));
        } catch (RuntimeException e) {
            // Business rule violations (insufficient shares, etc.)
            if (e.getMessage() != null && e.getMessage().contains("Insufficient")) {
                return ResponseEntity.status(409).body(ToolResponse.error(e.getMessage()));
            }
            return ResponseEntity.status(500).body(ToolResponse.error("Failed to sell shares"));
        }
    }

    @PostMapping("/tools/update_activity")
    public ResponseEntity<Void> updateActivity(@RequestBody Map<String, Object> request) {
        try {
            String name = resolveAgentName(request.get("agentId"));
            accountService.updateAgentActivity(name);
            return ResponseEntity.noContent().build();  // 204 No Content
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        } catch (RuntimeException e) {
            if (e.getMessage() != null && e.getMessage().contains("not found")) {
                return ResponseEntity.notFound().build();
            }
            return ResponseEntity.status(500).build();
        }
    }

    // change_strategy endpoint removed - using hardcoded strategies only

    // MCP Resource endpoints
    @GetMapping("/resources/accounts/{agentId}")
    public ResponseEntity<String> getAccountResource(@PathVariable Long agentId) {
        try {
            String name = agentIdentityService.requireAgentName(agentId);
            String accountReport = accountService.getAccountReport(name);
            return ResponseEntity.ok(accountReport);
        } catch (Exception e) {
            return ResponseEntity.badRequest().body("Error: " + e.getMessage());
        }
    }

    // strategy resource endpoint removed - using hardcoded strategies only
    
    // Portfolio history endpoint for charts
    @GetMapping("/portfolio/{agentId}/history")
    public ResponseEntity<List<PortfolioHistoryPoint>> getPortfolioHistory(
            @PathVariable Long agentId,
            @RequestParam(defaultValue = "7") int days) {
        String agentName = null;
        try {
            agentName = agentIdentityService.requireAgentName(agentId);
            // Use Instant (not LocalDateTime) to match entity field type
            Instant fromDate = Instant.now().minus(days, java.time.temporal.ChronoUnit.DAYS);
            List<AccountPortfolioSnapshot> snapshots = snapshotRepository
                    .getPortfolioPerformance(agentName, fromDate);

            // Convert to simple DTO
            List<PortfolioHistoryPoint> history = snapshots.stream()
                    .map(s -> new PortfolioHistoryPoint(s.getTimestamp(), s.getTotalValue()))
                    .collect(Collectors.toList());

            // Return empty list if no snapshots found (not an error)
            return ResponseEntity.ok(history);
        } catch (Exception e) {
            // Log actual error for debugging
            org.slf4j.LoggerFactory.getLogger(AccountController.class)
                .error("Error fetching portfolio history for {}: {}", agentName != null ? agentName : agentId, e.getMessage(), e);
            return ResponseEntity.badRequest().build();
        }
    }
    
    // Recent trades endpoint for trade log
    @GetMapping("/trades/recent")
    public ResponseEntity<List<RecentTradeDto>> getRecentTrades(
            @RequestParam(defaultValue = "20") int limit) {
        try {
            // Get recent transactions from all agents
            List<AccountTransaction> transactions = transactionRepository
                    .findAll()
                    .stream()
                    .sorted((a, b) -> b.getTimestamp().compareTo(a.getTimestamp()))
                    .limit(limit)
                    .collect(Collectors.toList());
            
            // Convert to DTOs
            List<RecentTradeDto> recentTrades = transactions.stream()
                    .map(t -> new RecentTradeDto(
                            t.getId(),
                            t.getAccount().getAgent().getName(),
                            t.getTransactionType().name(),  // Convert enum to string
                            t.getSymbol(),
                            Math.abs(t.getQuantity()), // Always show positive quantity
                            t.getPrice(),
                            t.getTotalAmount(),
                            t.getTimestamp()
                    ))
                    .collect(Collectors.toList());
            
            return ResponseEntity.ok(recentTrades);
        } catch (Exception e) {
            return ResponseEntity.badRequest().build();
        }
    }

    // Trade detail endpoint
    @GetMapping("/trades/{tradeId}")
    public ResponseEntity<TradeDetailResponse> getTradeDetail(@PathVariable Long tradeId) {
        try {
            // Get the transaction
            AccountTransaction transaction = transactionRepository.findById(tradeId)
                    .orElseThrow(() -> new RuntimeException("Trade not found"));

            // Build trade info
            TradeDetailResponse.TradeInfo tradeInfo = new TradeDetailResponse.TradeInfo(
                    transaction.getId(),
                    transaction.getAccount().getAgent().getName(),
                    transaction.getTransactionType().name(),  // Convert enum to string
                    transaction.getSymbol(),
                    Math.abs(transaction.getQuantity()),
                    transaction.getPrice(),
                    transaction.getTotalAmount(),
                    transaction.getTimestamp()
            );

            // Get related trades (same agent, same symbol, last 5)
            List<TradeDetailResponse.RelatedTrade> relatedTrades = transactionRepository
                    .findAll()
                    .stream()
                    .filter(t -> t.getId() != tradeId &&
                            t.getAccount().getId().equals(transaction.getAccount().getId()) &&
                            t.getSymbol().equals(transaction.getSymbol()))
                    .sorted((a, b) -> b.getTimestamp().compareTo(a.getTimestamp()))
                    .limit(5)
                    .map(t -> new TradeDetailResponse.RelatedTrade(
                            t.getId(),
                            t.getTransactionType().name(),  // Convert enum to string
                            Math.abs(t.getQuantity()),
                            t.getPrice(),
                            t.getTimestamp()
                    ))
                    .collect(Collectors.toList());

            // Get run info and reasoning steps if available
            Long runId = null;
            String runSummary = null;
            String summary = null;
            String fullReasoning = null;
            String researchSources = null;
            String historicalContext = null;
            List<RunDetailDto.ReasoningStepInfo> reasoningSteps = null;
            
            if (transaction.getAgentRun() != null) {
                AgentRun run = transaction.getAgentRun();
                runId = run.getId();
                runSummary = run.getSummary();
                summary = run.getSummary();
                fullReasoning = run.getFullReasoning();
                researchSources = run.getResearchSources();
                historicalContext = run.getHistoricalContext();
                
                // Fetch reasoning steps from the run
                reasoningSteps = reasoningStepRepository
                        .findByAgentRunIdOrderBySequenceNumberAsc(runId)
                        .stream()
                        .map(RunDetailDto.ReasoningStepInfo::fromEntity)
                        .collect(Collectors.toList());
            }

            // Build response
            TradeDetailResponse response = new TradeDetailResponse(
                    tradeInfo,
                    summary,
                    fullReasoning,
                    researchSources,
                    historicalContext,
                    relatedTrades,
                    runId,
                    runSummary,
                    reasoningSteps
            );

            return ResponseEntity.ok(response);
        } catch (Exception e) {
            org.slf4j.LoggerFactory.getLogger(AccountController.class)
                .error("Error fetching trade detail for {}: {}", tradeId, e.getMessage(), e);
            return ResponseEntity.badRequest().build();
        }
    }
}