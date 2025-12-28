package com.trading.controller;

import com.trading.config.AgentsClient;
import com.trading.dto.response.AgentStatusResponse;
import com.trading.dto.response.AgentTradeResponse;
import com.trading.dto.response.TriggerCycleResponse;
import com.trading.exception.ProblemDetailFactory;
import com.trading.service.TradingService;
import com.trading.service.AgentIdentityService;
import com.trading.service.AgentMonitoringService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.util.List;

/**
 * REST controller for trading operations.
 * Returns data directly without ToolResponse wrapper.
 * Generic exceptions are handled by GlobalExceptionHandler.
 * Endpoint-specific exceptions are handled inline with ProblemDetail responses.
 */
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


    /**
     * Get status for all agents.
     *
     * @return List of agent statuses from PostgreSQL
     */
    @GetMapping("/agents/status")
    public ResponseEntity<List<AgentStatusResponse>> getAllAgentsStatus() {
        List<AgentStatusResponse> statuses = agentMonitoringService.getRealAgentStatuses();
        return ResponseEntity.ok(statuses);
    }

    /**
     * Get trades for a specific agent or all agents.
     *
     * @param agentId optional agent ID to filter by
     * @return List of agent trades
     */
    @GetMapping("/agent-trades")
    public ResponseEntity<List<AgentTradeResponse>> getAgentTrades(@RequestParam(required = false) Long agentId) {
        String agentName = agentId != null ? agentIdentityService.requireAgentName(agentId) : null;
        List<AgentTradeResponse> trades = tradingService.getAgentTrades(agentName);
        return ResponseEntity.ok(trades);
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
    public ResponseEntity<?> triggerManualCycle() {
        logger.info("Manual trading cycle requested via API");

        try {
            // RestClient's fluent API (modern, clean!)
            // Virtual threads make this non-blocking under the hood
            TriggerCycleResponse response = agentsRestClient.post()
                    .uri("/api/trigger-cycle")
                    .retrieve()
                    .body(TriggerCycleResponse.class);

            logger.info("Manual cycle triggered successfully");
            return ResponseEntity.accepted().body(response);

        } catch (org.springframework.web.client.HttpClientErrorException.Conflict e) {
            // Endpoint-specific business logic: cycle already running
            logger.info("Manual cycle not triggered: cycle already running");
            ProblemDetail problem = ProblemDetailFactory.businessRuleViolation(
                "A trading cycle is already in progress. Please wait for it to complete.",
                "/api/trading/run-cycle"
            );
            return ResponseEntity.status(409).body(problem);

        } catch (org.springframework.web.client.RestClientException e) {
            // Endpoint-specific error message for agents service
            logger.error("Failed to connect to agents service: {}", e.getMessage());
            ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.SERVICE_UNAVAILABLE,
                "Agents service unavailable. Please ensure the trading system is running."
            );
            problem.setTitle("Service Unavailable");
            problem.setInstance(URI.create("/api/trading/run-cycle"));
            return ResponseEntity.status(503).body(problem);
        }
    }

    /**
     * Health check endpoint.
     *
     * @return health status message
     */
    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("Trading service is running");
    }
}
