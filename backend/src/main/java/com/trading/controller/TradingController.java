package com.trading.controller;

import com.trading.dto.ToolResponse;
import com.trading.service.TradingService;
import com.trading.service.TradingService.*;
import com.trading.service.AgentMonitoringService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/trading")
@CrossOrigin(origins = {"http://localhost:3000", "http://localhost:5173"})
public class TradingController {
    
    @Autowired
    private TradingService tradingService;
    
    @Autowired
    private AgentMonitoringService agentMonitoringService;
    
    
    // Agent Status Endpoints (Real Data from PostgreSQL)
    @GetMapping("/agents/status")
    public ResponseEntity<ToolResponse<List<AgentStatusResponse>>> getAllAgentsStatus() {
        try {
            List<AgentStatusResponse> statuses = agentMonitoringService.getRealAgentStatuses();
            return ResponseEntity.ok(ToolResponse.success(statuses));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    
    @GetMapping("/agents/{agentName}/status")
    public ResponseEntity<ToolResponse<AgentStatusResponse>> getAgentStatus(@PathVariable String agentName) {
        try {
            AgentStatusResponse status = agentMonitoringService.getRealAgentStatus(agentName);
            return ResponseEntity.ok(ToolResponse.success(status));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    
    @PostMapping("/agents/{agentName}/start")
    public ResponseEntity<ToolResponse<String>> startAgent(@PathVariable String agentName) {
        try {
            agentMonitoringService.startAgent(agentName);
            return ResponseEntity.ok(ToolResponse.success("Agent " + agentName + " started successfully"));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @PostMapping("/agents/{agentName}/stop")
    public ResponseEntity<ToolResponse<String>> stopAgent(@PathVariable String agentName) {
        try {
            agentMonitoringService.stopAgent(agentName);
            return ResponseEntity.ok(ToolResponse.success("Agent " + agentName + " stopped successfully"));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    // Order Management Endpoints
    @GetMapping("/orders")
    public ResponseEntity<ToolResponse<List<TradeOrderResponse>>> getOrders(@RequestParam(required = false) String accountId) {
        try {
            List<TradeOrderResponse> orders = tradingService.getOrders(accountId);
            return ResponseEntity.ok(ToolResponse.success(orders));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @GetMapping("/orders/{orderId}")
    public ResponseEntity<ToolResponse<TradeOrderResponse>> getOrder(@PathVariable String orderId) {
        try {
            TradeOrderResponse order = tradingService.getOrder(orderId);
            return ResponseEntity.ok(ToolResponse.success(order));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @PostMapping("/orders")
    public ResponseEntity<ToolResponse<TradeOrderResponse>> createOrder(@RequestBody CreateOrderRequest request) {
        try {
            TradeOrderResponse order = tradingService.createOrder(request);
            return ResponseEntity.ok(ToolResponse.success(order));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @DeleteMapping("/orders/{orderId}")
    public ResponseEntity<ToolResponse<String>> cancelOrder(@PathVariable String orderId) {
        try {
            tradingService.cancelOrder(orderId);
            return ResponseEntity.ok(ToolResponse.success("Order " + orderId + " cancelled successfully"));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    // Agent Trades Endpoints
    @GetMapping("/agent-trades")
    public ResponseEntity<ToolResponse<List<AgentTradeResponse>>> getAgentTrades(@RequestParam(required = false) String agentName) {
        try {
            List<AgentTradeResponse> trades = tradingService.getAgentTrades(agentName);
            return ResponseEntity.ok(ToolResponse.success(trades));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @GetMapping("/activity")
    public ResponseEntity<ToolResponse<List<AgentTradeResponse>>> getRecentActivity(@RequestParam(defaultValue = "50") int limit) {
        try {
            List<AgentTradeResponse> activity = tradingService.getRecentActivity(limit);
            return ResponseEntity.ok(ToolResponse.success(activity));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    // Trading Statistics Endpoints
    @GetMapping("/stats")
    public ResponseEntity<ToolResponse<TradingStatsResponse>> getTradingStats(
            @RequestParam(required = false) String accountId,
            @RequestParam(required = false) String agentName) {
        try {
            TradingStatsResponse stats = tradingService.getTradingStats(accountId, agentName);
            return ResponseEntity.ok(ToolResponse.success(stats));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    // Portfolio Performance Endpoints
    @GetMapping("/performance/{accountId}")
    public ResponseEntity<ToolResponse<PortfolioPerformanceResponse>> getPortfolioPerformance(
            @PathVariable String accountId,
            @RequestParam(defaultValue = "1m") String period) {
        try {
            PortfolioPerformanceResponse performance = tradingService.getPortfolioPerformance(accountId, period);
            return ResponseEntity.ok(ToolResponse.success(performance));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    // Risk Metrics Endpoints
    @GetMapping("/risk/{accountId}")
    public ResponseEntity<ToolResponse<RiskMetricsResponse>> getRiskMetrics(@PathVariable String accountId) {
        try {
            RiskMetricsResponse riskMetrics = tradingService.getRiskMetrics(accountId);
            return ResponseEntity.ok(ToolResponse.success(riskMetrics));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    // Real Data Monitoring Endpoints - Temporarily disabled due to missing service
    @GetMapping("/agents/{agentName}/logs")
    public ResponseEntity<ToolResponse<List<String>>> getAgentLogs(
            @PathVariable String agentName,
            @RequestParam(defaultValue = "10") int limit) {
        try {
            // List<String> logs = agentMonitoringService.getAgentLogs(agentName, limit);
            // Fallback until PostgreSQLAgentMonitoringService is implemented
            List<String> logs = List.of("Log functionality temporarily unavailable");
            return ResponseEntity.ok(ToolResponse.success(logs));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @GetMapping("/system/status")
    public ResponseEntity<ToolResponse<Map<String, Object>>> getSystemStatus() {
        try {
            Map<String, Object> status = Map.of(
                "pythonTradingSystemActive", false, // agentMonitoringService.isPythonTradingSystemActive(),
                "timestamp", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
                "databaseConnected", true // Could add actual database health check
            );
            return ResponseEntity.ok(ToolResponse.success(status));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    // Health Check Endpoint
    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("Trading service is running");
    }
}