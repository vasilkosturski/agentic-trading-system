package com.trading.controller;

import com.trading.dto.response.AgentStatusResponse;
import com.trading.dto.response.AgentTradeResponse;
import com.trading.dto.response.ToolResponse;
import com.trading.dto.response.TradingStatsResponse;
import com.trading.dto.response.TriggerCycleResponse;
import com.trading.service.TradingService;
import com.trading.service.AgentIdentityService;
import com.trading.service.AgentMonitoringService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.RestClientException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/trading")
public class TradingController {
    
    private static final Logger logger = LoggerFactory.getLogger(TradingController.class);
    
    @Autowired
    private TradingService tradingService;
    
    @Autowired
    private AgentMonitoringService agentMonitoringService;

    @Autowired
    private AgentIdentityService agentIdentityService;
    
    @Value("${agents.api.url:http://agents-service:8000}")
    private String agentsApiUrl;
    
    private final RestTemplate restTemplate;
    
    public TradingController() {
        // Configure RestTemplate with longer timeouts for agents service
        this.restTemplate = new RestTemplate();
        this.restTemplate.setRequestFactory(new org.springframework.http.client.SimpleClientHttpRequestFactory() {{
            setConnectTimeout(30000); // 30 seconds
            setReadTimeout(60000);    // 60 seconds
        }});
    }
    
    
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
    
    
    @GetMapping("/agents/{agentId}/status")
    public ResponseEntity<ToolResponse<AgentStatusResponse>> getAgentStatus(@PathVariable Long agentId) {
        try {
            AgentStatusResponse status = agentMonitoringService.getRealAgentStatus(agentId);
            return ResponseEntity.ok(ToolResponse.success(status));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    
    @PostMapping("/agents/{agentId}/start")
    public ResponseEntity<ToolResponse<String>> startAgent(@PathVariable Long agentId) {
        try {
            String agentName = agentIdentityService.requireAgentName(agentId);
            agentMonitoringService.startAgent(agentName);
            return ResponseEntity.ok(ToolResponse.success("Agent " + agentName + " started successfully"));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    @PostMapping("/agents/{agentId}/stop")
    public ResponseEntity<ToolResponse<String>> stopAgent(@PathVariable Long agentId) {
        try {
            String agentName = agentIdentityService.requireAgentName(agentId);
            agentMonitoringService.stopAgent(agentName);
            return ResponseEntity.ok(ToolResponse.success("Agent " + agentName + " stopped successfully"));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    // Agent Trades Endpoints
    @GetMapping("/agent-trades")
    public ResponseEntity<ToolResponse<List<AgentTradeResponse>>> getAgentTrades(@RequestParam(required = false) Long agentId) {
        try {
            String agentName = agentId != null ? agentIdentityService.requireAgentName(agentId) : null;
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
            @RequestParam(required = false) Long agentId) {
        try {
            String agentName = agentId != null ? agentIdentityService.requireAgentName(agentId) : null;
            TradingStatsResponse stats = tradingService.getTradingStats(accountId, agentName);
            return ResponseEntity.ok(ToolResponse.success(stats));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage() != null ? e.getMessage() : "Unknown error"));
        }
    }
    
    // Real Data Monitoring Endpoints - Temporarily disabled due to missing service
    @GetMapping("/agents/{agentId}/logs")
    public ResponseEntity<ToolResponse<List<String>>> getAgentLogs(
            @PathVariable Long agentId,
            @RequestParam(defaultValue = "10") int limit) {
        try {
            // Verify agent exists
            agentIdentityService.requireAgentName(agentId);
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
    
    @PostMapping("/run-cycle")
    public ResponseEntity<ToolResponse<TriggerCycleResponse>> triggerManualCycle() {
        logger.info("Manual trading cycle requested via API");
        String url = agentsApiUrl + "/api/trigger-cycle";
        
        try {
            ResponseEntity<TriggerCycleResponse> response = restTemplate.postForEntity(
                url, null, TriggerCycleResponse.class
            );
            logger.info("Manual cycle triggered successfully");
            return ResponseEntity.accepted().body(ToolResponse.success(response.getBody()));
            
        } catch (org.springframework.web.client.HttpClientErrorException.Conflict e) {
            logger.info("Manual cycle not triggered: cycle already running");
            return ResponseEntity.status(409).body(
                ToolResponse.error("A trading cycle is already in progress. Please wait for it to complete.")
            );
        } catch (RestClientException e) {
            logger.error("Failed to connect to agents service at {}: {}", url, e.getMessage());
            return ResponseEntity.status(503).body(
                ToolResponse.error("Agents service unavailable. Please ensure the trading system is running.")
            );
        }
    }
    
    // Health Check Endpoint
    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("Trading service is running");
    }
}
