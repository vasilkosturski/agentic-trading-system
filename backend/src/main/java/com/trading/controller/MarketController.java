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
    public ResponseEntity<ToolResponse<MarketService.PriceData>> getSharePrice(@PathVariable String symbol) {
        try {
            MarketService.PriceData priceData = marketService.getSharePrice(symbol);
            return ResponseEntity.ok(ToolResponse.success(priceData));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    // Backward compatibility endpoint - returns just the price value
    @GetMapping("/price/{symbol}/value")
    public ResponseEntity<ToolResponse<Double>> getSharePriceValue(@PathVariable String symbol) {
        try {
            MarketService.PriceData priceData = marketService.getSharePrice(symbol);
            return ResponseEntity.ok(ToolResponse.success(priceData.getPrice()));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @GetMapping("/historical/{symbol}")
    public ResponseEntity<ToolResponse<MarketService.HistoricalPriceData>> getHistoricalPrices(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "30") int days) {
        try {
            MarketService.HistoricalPriceData historicalData = marketService.getHistoricalPrices(symbol, days);
            return ResponseEntity.ok(ToolResponse.success(historicalData));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    // Backward compatibility endpoint - returns just the price list
    @GetMapping("/historical/{symbol}/prices")
    public ResponseEntity<ToolResponse<List<MarketService.HistoricalPrice>>> getHistoricalPricesList(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "30") int days) {
        try {
            MarketService.HistoricalPriceData historicalData = marketService.getHistoricalPrices(symbol, days);
            return ResponseEntity.ok(ToolResponse.success(historicalData.getPrices()));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @GetMapping("/indicators/{symbol}")
    public ResponseEntity<ToolResponse<MarketService.MarketIndicatorsData>> getMarketIndicators(@PathVariable String symbol) {
        try {
            MarketService.MarketIndicatorsData indicatorsData = marketService.getMarketIndicators(symbol);
            return ResponseEntity.ok(ToolResponse.success(indicatorsData));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    // Backward compatibility endpoint - returns just the indicators
    @GetMapping("/indicators/{symbol}/values")
    public ResponseEntity<ToolResponse<MarketService.MarketIndicators>> getMarketIndicatorsValues(@PathVariable String symbol) {
        try {
            MarketService.MarketIndicatorsData indicatorsData = marketService.getMarketIndicators(symbol);
            return ResponseEntity.ok(ToolResponse.success(indicatorsData.getIndicators()));
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