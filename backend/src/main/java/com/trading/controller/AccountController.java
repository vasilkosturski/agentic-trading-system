package com.trading.controller;

import com.trading.dto.PortfolioHistoryPoint;
import com.trading.dto.RecentTradeDto;
import com.trading.dto.ToolResponse;
import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.entity.AccountTransaction;
import com.trading.repository.AccountPortfolioSnapshotRepository;
import com.trading.repository.AccountTransactionRepository;
import com.trading.service.PostgreSQLAccountService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/accounts")
@CrossOrigin(origins = {"http://localhost:3000", "http://localhost:5173"})
public class AccountController {

    @Autowired
    private PostgreSQLAccountService accountService;
    
    @Autowired
    private AccountPortfolioSnapshotRepository snapshotRepository;
    
    @Autowired
    private AccountTransactionRepository transactionRepository;

    // Agent initialization endpoint
    @PostMapping("/tools/initialize_agent")
    public ResponseEntity<ToolResponse<String>> initializeAgent(@RequestBody Map<String, Object> request) {
        try {
            String name = (String) request.get("name");
            Double initialBalance = request.get("initialBalance") != null ?
                ((Number) request.get("initialBalance")).doubleValue() : 100000.0;
            
            accountService.initializeAgent(name, initialBalance);
            return ResponseEntity.ok(new ToolResponse<>(true,
                "Successfully initialized agent " + name, null));
        } catch (Exception e) {
            return ResponseEntity.ok(new ToolResponse<>(false, null, e.getMessage()));
        }
    }

    // MCP Tool endpoints
    @PostMapping("/tools/get_balance")
    public ResponseEntity<ToolResponse<Double>> getBalance(@RequestBody Map<String, String> request) {
        try {
            String name = request.get("name");
            Double balance = accountService.getBalance(name);
            return ResponseEntity.ok(new ToolResponse<>(true, balance, null));
        } catch (Exception e) {
            return ResponseEntity.ok(new ToolResponse<>(false, null, e.getMessage()));
        }
    }

    @PostMapping("/tools/get_holdings")
    public ResponseEntity<ToolResponse<Map<String, Integer>>> getHoldings(@RequestBody Map<String, String> request) {
        try {
            String name = request.get("name");
            Map<String, Integer> holdings = accountService.getHoldings(name);
            return ResponseEntity.ok(new ToolResponse<>(true, holdings, null));
        } catch (Exception e) {
            return ResponseEntity.ok(new ToolResponse<>(false, null, e.getMessage()));
        }
    }

    @PostMapping("/tools/buy_shares")
    public ResponseEntity<ToolResponse<String>> buyShares(@RequestBody Map<String, Object> request) {
        try {
            String name = (String) request.get("name");
            String symbol = (String) request.get("symbol");
            Integer quantity = (Integer) request.get("quantity");
            String rationale = (String) request.get("rationale");
            
            String result = accountService.buyShares(name, symbol, quantity, rationale);
            return ResponseEntity.ok(new ToolResponse<>(true, result, null));
        } catch (Exception e) {
            return ResponseEntity.ok(new ToolResponse<>(false, null, e.getMessage()));
        }
    }

    @PostMapping("/tools/sell_shares")
    public ResponseEntity<ToolResponse<String>> sellShares(@RequestBody Map<String, Object> request) {
        try {
            String name = (String) request.get("name");
            String symbol = (String) request.get("symbol");
            Integer quantity = (Integer) request.get("quantity");
            String rationale = (String) request.get("rationale");
            
            String result = accountService.sellShares(name, symbol, quantity, rationale);
            return ResponseEntity.ok(new ToolResponse<>(true, result, null));
        } catch (Exception e) {
            return ResponseEntity.ok(new ToolResponse<>(false, null, e.getMessage()));
        }
    }

    // change_strategy endpoint removed - using hardcoded strategies only

    // MCP Resource endpoints
    @GetMapping("/resources/accounts/{name}")
    public ResponseEntity<String> getAccountResource(@PathVariable String name) {
        try {
            String accountReport = accountService.getAccountReport(name);
            return ResponseEntity.ok(accountReport);
        } catch (Exception e) {
            return ResponseEntity.badRequest().body("Error: " + e.getMessage());
        }
    }

    // strategy resource endpoint removed - using hardcoded strategies only
    
    // Portfolio history endpoint for charts
    @GetMapping("/portfolio/{agentName}/history")
    public ResponseEntity<List<PortfolioHistoryPoint>> getPortfolioHistory(
            @PathVariable String agentName,
            @RequestParam(defaultValue = "7") int days) {
        try {
            LocalDateTime fromDate = LocalDateTime.now().minusDays(days);
            List<AccountPortfolioSnapshot> snapshots = snapshotRepository
                    .getPortfolioPerformance(agentName, fromDate);
            
            // Convert to simple DTO
            List<PortfolioHistoryPoint> history = snapshots.stream()
                    .map(s -> new PortfolioHistoryPoint(s.getTimestamp(), s.getTotalValue()))
                    .collect(Collectors.toList());
            
            return ResponseEntity.ok(history);
        } catch (Exception e) {
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
                            t.getAccount().getName(),
                            t.getTransactionType(),
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
}