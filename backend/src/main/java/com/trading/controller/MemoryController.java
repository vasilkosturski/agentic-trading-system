package com.trading.controller;

import com.trading.dto.response.RecentActivityResponse;
import com.trading.dto.response.TradingHistoryResponse;
import com.trading.service.MemoryService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Memory API endpoints for agents to query their past decisions and reasoning.
 * Returns DTOs that Jackson automatically serializes to JSON.
 */
@RestController
@RequestMapping("/api/memory")
public class MemoryController {

    @Autowired
    private MemoryService memoryService;

    /**
     * Get complete trading history for a specific stock
     * GET /api/memory/trading-history?agentName=Warren&symbol=NVDA&days=30
     */
    @GetMapping("/trading-history")
    public ResponseEntity<?> getTradingHistory(
            @RequestParam String agentName,
            @RequestParam String symbol,
            @RequestParam(defaultValue = "30") int days) {
        try {
            TradingHistoryResponse history = memoryService.getTradingHistory(agentName, symbol, days);
            return ResponseEntity.ok(history);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(
                Map.of("error", "Failed to retrieve trading history: " + e.getMessage())
            );
        }
    }

    /**
     * Get recent trading activity across all stocks
     * GET /api/memory/recent-activity?agentName=Warren&days=7
     */
    @GetMapping("/recent-activity")
    public ResponseEntity<?> getRecentActivity(
            @RequestParam String agentName,
            @RequestParam(defaultValue = "7") int days) {
        try {
            RecentActivityResponse activity = memoryService.getRecentActivity(agentName, days);
            return ResponseEntity.ok(activity);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(
                Map.of("error", "Failed to retrieve recent activity: " + e.getMessage())
            );
        }
    }
}

