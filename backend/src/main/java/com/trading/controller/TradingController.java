package com.trading.controller;

import com.trading.config.AgentsClient;
import com.trading.dto.response.AgentStatusResponse;
import com.trading.dto.response.AgentTradeResponse;
import com.trading.dto.response.ToolResponse;
import com.trading.dto.response.TradingStatsResponse;
import com.trading.dto.response.TriggerCycleResponse;
import com.trading.service.TradingService;
import com.trading.service.AgentIdentityService;
import com.trading.service.AgentMonitoringService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestClient;
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

    private final TradingService tradingService;
    private final AgentMonitoringService agentMonitoringService;
    private final AgentIdentityService agentIdentityService;
    private final RestClient agentsRestClient;

    /**
     * Constructor injection for all dependencies.
     *
     * Uses type-safe @AgentsClient qualifier for REST client injection.
     * With Virtual Threads enabled, this synchronous client provides
     * async-like performance automatically!
     *
     * @param tradingService Service for trading operations
     * @param agentMonitoringService Service for agent monitoring
     * @param agentIdentityService Service for agent identity management
     * @param agentsRestClient RestClient for agents service (type-safe injection)
     */
    public TradingController(
            TradingService tradingService,
            AgentMonitoringService agentMonitoringService,
            AgentIdentityService agentIdentityService,
            @AgentsClient RestClient agentsRestClient
    ) {
        this.tradingService = tradingService;
        this.agentMonitoringService = agentMonitoringService;
        this.agentIdentityService = agentIdentityService;
        this.agentsRestClient = agentsRestClient;
    }
    
    
    // Agent Status Endpoints (Real Data from PostgreSQL)
    @GetMapping("/agents/status")
    public ResponseEntity<ToolResponse<List<AgentStatusResponse>>> getAllAgentsStatus() {
        List<AgentStatusResponse> statuses = agentMonitoringService.getRealAgentStatuses();
        return ResponseEntity.ok(ToolResponse.success(statuses));
    }


    @GetMapping("/agents/{agentId}/status")
    public ResponseEntity<ToolResponse<AgentStatusResponse>> getAgentStatus(@PathVariable Long agentId) {
        AgentStatusResponse status = agentMonitoringService.getRealAgentStatus(agentId);
        return ResponseEntity.ok(ToolResponse.success(status));
    }


    @PostMapping("/agents/{agentId}/start")
    public ResponseEntity<ToolResponse<String>> startAgent(@PathVariable Long agentId) {
        String agentName = agentIdentityService.requireAgentName(agentId);
        agentMonitoringService.startAgent(agentName);
        return ResponseEntity.ok(ToolResponse.success("Agent " + agentName + " started successfully"));
    }

    @PostMapping("/agents/{agentId}/stop")
    public ResponseEntity<ToolResponse<String>> stopAgent(@PathVariable Long agentId) {
        String agentName = agentIdentityService.requireAgentName(agentId);
        agentMonitoringService.stopAgent(agentName);
        return ResponseEntity.ok(ToolResponse.success("Agent " + agentName + " stopped successfully"));
    }

    // Agent Trades Endpoints
    @GetMapping("/agent-trades")
    public ResponseEntity<ToolResponse<List<AgentTradeResponse>>> getAgentTrades(@RequestParam(required = false) Long agentId) {
        String agentName = agentId != null ? agentIdentityService.requireAgentName(agentId) : null;
        List<AgentTradeResponse> trades = tradingService.getAgentTrades(agentName);
        return ResponseEntity.ok(ToolResponse.success(trades));
    }

    @GetMapping("/activity")
    public ResponseEntity<ToolResponse<List<AgentTradeResponse>>> getRecentActivity(@RequestParam(defaultValue = "50") int limit) {
        List<AgentTradeResponse> activity = tradingService.getRecentActivity(limit);
        return ResponseEntity.ok(ToolResponse.success(activity));
    }

    // Trading Statistics Endpoints
    @GetMapping("/stats")
    public ResponseEntity<ToolResponse<TradingStatsResponse>> getTradingStats(
            @RequestParam(required = false) String accountId,
            @RequestParam(required = false) Long agentId) {
        String agentName = agentId != null ? agentIdentityService.requireAgentName(agentId) : null;
        TradingStatsResponse stats = tradingService.getTradingStats(accountId, agentName);
        return ResponseEntity.ok(ToolResponse.success(stats));
    }

    // Real Data Monitoring Endpoints - Temporarily disabled due to missing service
    @GetMapping("/agents/{agentId}/logs")
    public ResponseEntity<ToolResponse<List<String>>> getAgentLogs(
            @PathVariable Long agentId,
            @RequestParam(defaultValue = "10") int limit) {
        // Verify agent exists
        agentIdentityService.requireAgentName(agentId);
        // List<String> logs = agentMonitoringService.getAgentLogs(agentName, limit);
        // Fallback until PostgreSQLAgentMonitoringService is implemented
        List<String> logs = List.of("Log functionality temporarily unavailable");
        return ResponseEntity.ok(ToolResponse.success(logs));
    }

    @GetMapping("/system/status")
    public ResponseEntity<ToolResponse<Map<String, Object>>> getSystemStatus() {
        Map<String, Object> status = Map.of(
            "pythonTradingSystemActive", false, // agentMonitoringService.isPythonTradingSystemActive(),
            "timestamp", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
            "databaseConnected", true // Could add actual database health check
        );
        return ResponseEntity.ok(ToolResponse.success(status));
    }
    
    /**
     * Triggers a manual trading cycle via the agents service.
     *
     * With Virtual Threads enabled, this synchronous-looking code actually
     * runs asynchronously! The virtual thread yields during the HTTP call,
     * allowing other requests to be processed on the same OS thread.
     *
     * NOTE: This method keeps endpoint-specific exception handling for business logic:
     * - 409 Conflict: Specific to this endpoint (cycle already running)
     * - 503 Service Unavailable: Custom message specific to agents service
     *
     * @return 202 Accepted if cycle triggered, 409 if already running, 503 if service unavailable
     */
    @PostMapping("/run-cycle")
    public ResponseEntity<ToolResponse<TriggerCycleResponse>> triggerManualCycle() {
        logger.info("Manual trading cycle requested via API");

        try {
            // RestClient's fluent API (modern, clean!)
            // Virtual threads make this non-blocking under the hood
            TriggerCycleResponse response = agentsRestClient.post()
                    .uri("/api/trigger-cycle")
                    .retrieve()
                    .body(TriggerCycleResponse.class);

            logger.info("Manual cycle triggered successfully");
            return ResponseEntity.accepted().body(ToolResponse.success(response));

        } catch (org.springframework.web.client.HttpClientErrorException.Conflict e) {
            // Endpoint-specific business logic: cycle already running
            logger.info("Manual cycle not triggered: cycle already running");
            return ResponseEntity.status(409).body(
                ToolResponse.error("A trading cycle is already in progress. Please wait for it to complete.")
            );
        } catch (org.springframework.web.client.RestClientException e) {
            // Endpoint-specific error message for agents service
            logger.error("Failed to connect to agents service: {}", e.getMessage());
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
