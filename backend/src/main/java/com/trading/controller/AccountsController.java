package com.trading.controller;

import com.trading.dto.ToolResponse;
import com.trading.service.AccountService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/accounts")
public class AccountsController {
    
    @Autowired
    private AccountService accountService;
    
    @PostMapping("/tools/get_balance")
    public ResponseEntity<ToolResponse<Double>> getBalance(@RequestBody GetBalanceRequest request) {
        try {
            Double balance = accountService.getBalance(request.getName());
            return ResponseEntity.ok(ToolResponse.success(balance));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @PostMapping("/tools/get_holdings")
    public ResponseEntity<ToolResponse<Map<String, Integer>>> getHoldings(@RequestBody GetHoldingsRequest request) {
        try {
            Map<String, Integer> holdings = accountService.getHoldings(request.getName());
            return ResponseEntity.ok(ToolResponse.success(holdings));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @PostMapping("/tools/buy_shares")
    public ResponseEntity<ToolResponse<String>> buyShares(@RequestBody BuySharesRequest request) {
        try {
            String result = accountService.buyShares(request.getName(), request.getSymbol(), request.getQuantity(), request.getRationale());
            return ResponseEntity.ok(ToolResponse.success(result));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @PostMapping("/tools/sell_shares")
    public ResponseEntity<ToolResponse<String>> sellShares(@RequestBody SellSharesRequest request) {
        try {
            String result = accountService.sellShares(request.getName(), request.getSymbol(), request.getQuantity(), request.getRationale());
            return ResponseEntity.ok(ToolResponse.success(result));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @PostMapping("/tools/change_strategy")
    public ResponseEntity<ToolResponse<String>> changeStrategy(@RequestBody ChangeStrategyRequest request) {
        try {
            String result = accountService.changeStrategy(request.getName(), request.getStrategy());
            return ResponseEntity.ok(ToolResponse.success(result));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @GetMapping("/resources/accounts/{name}")
    public ResponseEntity<String> getAccountResource(@PathVariable String name) {
        try {
            String report = accountService.getAccountReport(name);
            return ResponseEntity.ok(report);
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

// Request DTOs
class GetBalanceRequest {
    private String name;
    
    public GetBalanceRequest() {}
    public GetBalanceRequest(String name) { this.name = name; }
    
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
}

class GetHoldingsRequest {
    private String name;
    
    public GetHoldingsRequest() {}
    public GetHoldingsRequest(String name) { this.name = name; }
    
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
}

class BuySharesRequest {
    private String name;
    private String symbol;
    private Integer quantity;
    private String rationale;
    
    public BuySharesRequest() {}
    public BuySharesRequest(String name, String symbol, Integer quantity, String rationale) {
        this.name = name;
        this.symbol = symbol;
        this.quantity = quantity;
        this.rationale = rationale;
    }
    
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { this.quantity = quantity; }
    
    public String getRationale() { return rationale; }
    public void setRationale(String rationale) { this.rationale = rationale; }
}

class SellSharesRequest {
    private String name;
    private String symbol;
    private Integer quantity;
    private String rationale;
    
    public SellSharesRequest() {}
    public SellSharesRequest(String name, String symbol, Integer quantity, String rationale) {
        this.name = name;
        this.symbol = symbol;
        this.quantity = quantity;
        this.rationale = rationale;
    }
    
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { this.quantity = quantity; }
    
    public String getRationale() { return rationale; }
    public void setRationale(String rationale) { this.rationale = rationale; }
}

class ChangeStrategyRequest {
    private String name;
    private String strategy;
    
    public ChangeStrategyRequest() {}
    public ChangeStrategyRequest(String name, String strategy) {
        this.name = name;
        this.strategy = strategy;
    }
    
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public String getStrategy() { return strategy; }
    public void setStrategy(String strategy) { this.strategy = strategy; }
}
