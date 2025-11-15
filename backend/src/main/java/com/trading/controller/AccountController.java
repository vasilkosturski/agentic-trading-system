package com.trading.controller;

import com.trading.dto.PortfolioHistoryPoint;
import com.trading.dto.RecentTradeDto;
import com.trading.dto.ToolResponse;
import com.trading.dto.TradeDetailResponse;
import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.entity.AccountTransaction;
import com.trading.repository.AccountPortfolioSnapshotRepository;
import com.trading.repository.AccountTransactionRepository;
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
    public ResponseEntity<ToolResponse<String>> initializeAgent(@RequestBody Map<String, Object> request) {
        try {
            String name;
            if (request.containsKey("agentId")) {
                name = resolveAgentName(request.get("agentId"));
            } else {
                Object explicitName = request.get("name");
                if (explicitName == null) {
                    throw new IllegalArgumentException("agentId or name is required");
                }
                name = explicitName.toString();
            }
            Double initialBalance = request.get("initialBalance") != null ?
                ((Number) request.get("initialBalance")).doubleValue() : 100000.0;
            
            accountService.initializeAgent(name, initialBalance);
            return ResponseEntity.status(201).body(ToolResponse.success(
                "Successfully initialized agent " + name));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage()));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(ToolResponse.error("Failed to initialize agent"));
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
    public ResponseEntity<ToolResponse<Map<String, Integer>>> getHoldings(@RequestBody Map<String, Object> request) {
        try {
            String name = resolveAgentName(request.get("agentId"));
            Map<String, Integer> holdings = accountService.getHoldings(name);
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
    public ResponseEntity<ToolResponse<String>> buyShares(@RequestBody Map<String, Object> request) {
        try {
            String name = resolveAgentName(request.get("agentId"));
            String symbol = (String) request.get("symbol");
            Integer quantity = (Integer) request.get("quantity");
            String rationale = (String) request.get("rationale");
            String fullReasoning = (String) request.get("fullReasoning");
            String researchSources = (String) request.get("researchSources");
            String agentContext = (String) request.get("agentContext");
            Long runId = request.get("runId") != null ? ((Number) request.get("runId")).longValue() : null;

            String result = accountService.buyShares(name, symbol, quantity, rationale,
                fullReasoning, researchSources, agentContext, runId);
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
    public ResponseEntity<ToolResponse<String>> sellShares(@RequestBody Map<String, Object> request) {
        try {
            String name = resolveAgentName(request.get("agentId"));
            String symbol = (String) request.get("symbol");
            Integer quantity = (Integer) request.get("quantity");
            String rationale = (String) request.get("rationale");
            String fullReasoning = (String) request.get("fullReasoning");
            String researchSources = (String) request.get("researchSources");
            String agentContext = (String) request.get("agentContext");
            Long runId = request.get("runId") != null ? ((Number) request.get("runId")).longValue() : null;

            String result = accountService.sellShares(name, symbol, quantity, rationale,
                fullReasoning, researchSources, agentContext, runId);
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
                            t.getTimestamp(),
                            t.getRationale()
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
                    transaction.getTimestamp(),
                    transaction.getRationale()
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

            // Get run info if available
            Long runId = null;
            String runSummary = null;
            if (transaction.getAgentRun() != null) {
                runId = transaction.getAgentRun().getId();
                runSummary = transaction.getAgentRun().getSummary();
            }

            // Build response
            TradeDetailResponse response = new TradeDetailResponse(
                    tradeInfo,
                    transaction.getFullReasoning(),
                    transaction.getResearchSources(),
                    transaction.getAgentContext(),
                    relatedTrades,
                    runId,
                    runSummary
            );

            return ResponseEntity.ok(response);
        } catch (Exception e) {
            org.slf4j.LoggerFactory.getLogger(AccountController.class)
                .error("Error fetching trade detail for {}: {}", tradeId, e.getMessage(), e);
            return ResponseEntity.badRequest().build();
        }
    }
}