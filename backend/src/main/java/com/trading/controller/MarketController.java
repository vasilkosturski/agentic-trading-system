package com.trading.controller;

import com.trading.dto.ToolResponse;
import com.trading.service.MarketService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

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
    
    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("Market service is running");
    }
}