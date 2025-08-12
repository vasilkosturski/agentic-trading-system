package com.trading.controller;

import com.trading.dto.ToolResponse;
import com.trading.service.PostgreSQLAccountService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/accounts")
@CrossOrigin(origins = "http://localhost:3000")
public class AccountController {

    @Autowired
    private PostgreSQLAccountService accountService;

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

    @PostMapping("/tools/change_strategy")
    public ResponseEntity<ToolResponse<String>> changeStrategy(@RequestBody Map<String, String> request) {
        try {
            String name = request.get("name");
            String strategy = request.get("strategy");
            
            String result = accountService.changeStrategy(name, strategy);
            return ResponseEntity.ok(new ToolResponse<>(true, result, null));
        } catch (Exception e) {
            return ResponseEntity.ok(new ToolResponse<>(false, null, e.getMessage()));
        }
    }

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

    @GetMapping("/resources/strategy/{name}")
    public ResponseEntity<String> getStrategyResource(@PathVariable String name) {
        try {
            String strategy = accountService.getStrategy(name);
            return ResponseEntity.ok(strategy);
        } catch (Exception e) {
            return ResponseEntity.badRequest().body("Error: " + e.getMessage());
        }
    }
}