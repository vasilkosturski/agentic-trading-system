package com.trading.controller;

import com.trading.dto.ToolResponse;
import com.trading.service.MarketService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/market")
public class MarketController {
    
    @Autowired
    private MarketService marketService;
    
    @GetMapping("/price/{symbol}")
    public ResponseEntity<ToolResponse<Double>> getSharePrice(@PathVariable String symbol) {
        try {
            Double price = marketService.getSharePrice(symbol);
            return ResponseEntity.ok(ToolResponse.success(price));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @GetMapping("/historical/{symbol}")
    public ResponseEntity<ToolResponse<List<MarketService.HistoricalPrice>>> getHistoricalPrices(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "30") int days) {
        try {
            List<MarketService.HistoricalPrice> prices = marketService.getHistoricalPrices(symbol, days);
            return ResponseEntity.ok(ToolResponse.success(prices));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @GetMapping("/indicators/{symbol}")
    public ResponseEntity<ToolResponse<MarketService.MarketIndicators>> getMarketIndicators(@PathVariable String symbol) {
        try {
            MarketService.MarketIndicators indicators = marketService.getMarketIndicators(symbol);
            return ResponseEntity.ok(ToolResponse.success(indicators));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @GetMapping("/status")
    public ResponseEntity<ToolResponse<MarketService.MarketStatus>> getMarketStatus() {
        try {
            MarketService.MarketStatus status = marketService.getMarketStatus();
            return ResponseEntity.ok(ToolResponse.success(status));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @GetMapping("/is-open")
    public ResponseEntity<ToolResponse<Boolean>> isMarketOpen() {
        try {
            boolean isOpen = marketService.isMarketOpen();
            return ResponseEntity.ok(ToolResponse.success(isOpen));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @PostMapping("/cache/clear")
    public ResponseEntity<ToolResponse<String>> clearCache() {
        try {
            marketService.clearCache();
            return ResponseEntity.ok(ToolResponse.success("Cache cleared successfully"));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("Market service is running");
    }
}