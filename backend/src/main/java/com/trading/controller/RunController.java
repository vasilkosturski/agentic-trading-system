package com.trading.controller;

import com.trading.dto.AgentRunDto;
import com.trading.dto.RunDetailDto;
import com.trading.dto.ToolResponse;
import com.trading.entity.AccountTransaction;
import com.trading.entity.AgentRun;
import com.trading.repository.AccountTransactionRepository;
import com.trading.service.AgentIdentityService;
import com.trading.service.RunService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/runs")
public class RunController {

    private static final Logger logger = LoggerFactory.getLogger(RunController.class);

    @Autowired
    private RunService runService;

    @Autowired
    private AccountTransactionRepository transactionRepository;

    @Autowired
    private AgentIdentityService agentIdentityService;

    /**
     * Start a new agent run
     * POST /api/runs/start
     * Body: { "agentId": 1, "runType": "TRADING", "agentContext": "{...}", "marketConditions": "{...}" }
     */
    @PostMapping("/start")
    public ResponseEntity<ToolResponse<Long>> startRun(@RequestBody Map<String, Object> request) {
        try {
            Long agentId = ((Number) request.get("agentId")).longValue();
            String agentName = agentIdentityService.requireAgentName(agentId);
            String runType = (String) request.get("runType");
            String agentContext = (String) request.get("agentContext");
            String marketConditions = (String) request.get("marketConditions");

            AgentRun run = runService.startRun(agentName, runType, agentContext, marketConditions);
            return ResponseEntity.status(201).body(ToolResponse.success(run.getId()));
        } catch (IllegalArgumentException e) {
            logger.error("Invalid request to start run", e);
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage()));
        } catch (Exception e) {
            logger.error("Error starting run", e);
            return ResponseEntity.status(500).body(ToolResponse.error("Failed to start run"));
        }
    }

    /**
     * End an agent run
     * POST /api/runs/end
     * Body: { "runId": 1, "fullReasoning": "...", "researchSources": "[...]", "summary": "...", "tradeCount": 2 }
     */
    @PostMapping("/end")
    public ResponseEntity<ToolResponse<String>> endRun(@RequestBody Map<String, Object> request) {
        try {
            Long runId = ((Number) request.get("runId")).longValue();
            String fullReasoning = (String) request.get("fullReasoning");
            String researchSources = (String) request.get("researchSources");
            String summary = (String) request.get("summary");
            Integer tradeCount = request.get("tradeCount") != null ?
                    ((Number) request.get("tradeCount")).intValue() : 0;

            AgentRun run;
            if (tradeCount > 0) {
                run = runService.endRunWithTrades(runId, fullReasoning, researchSources, summary, tradeCount);
            } else {
                run = runService.endRunWithNoTrade(runId, fullReasoning, researchSources, summary);
            }

            return ResponseEntity.ok(ToolResponse.success(
                    "Run " + runId + " ended with outcome: " + run.getOutcome()));
        } catch (IllegalArgumentException e) {
            logger.error("Invalid request to end run", e);
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage()));
        } catch (RuntimeException e) {
            if (e.getMessage() != null && e.getMessage().contains("not found")) {
                return ResponseEntity.status(404).body(ToolResponse.error(e.getMessage()));
            }
            logger.error("Error ending run", e);
            return ResponseEntity.status(500).body(ToolResponse.error("Failed to end run"));
        }
    }

    /**
     * Mark a run as error
     * POST /api/runs/error
     * Body: { "runId": 1, "errorMessage": "..." }
     */
    @PostMapping("/error")
    public ResponseEntity<ToolResponse<String>> markRunAsError(@RequestBody Map<String, Object> request) {
        try {
            Long runId = ((Number) request.get("runId")).longValue();
            String errorMessage = (String) request.get("errorMessage");

            runService.markRunAsError(runId, errorMessage);
            return ResponseEntity.ok(ToolResponse.success("Run " + runId + " marked as error"));
        } catch (IllegalArgumentException e) {
            logger.error("Invalid request to mark run as error", e);
            return ResponseEntity.badRequest().body(ToolResponse.error(e.getMessage()));
        } catch (RuntimeException e) {
            if (e.getMessage() != null && e.getMessage().contains("not found")) {
                return ResponseEntity.status(404).body(ToolResponse.error(e.getMessage()));
            }
            logger.error("Error marking run as error", e);
            return ResponseEntity.status(500).body(ToolResponse.error("Failed to mark run as error"));
        }
    }

    /**
     * Get a specific run by ID with trades
     * GET /api/runs/{id}
     */
    @GetMapping("/{id}")
    public ResponseEntity<RunDetailDto> getRun(@PathVariable Long id) {
        try {
            AgentRun run = runService.getRun(id);
            List<AccountTransaction> transactions = transactionRepository.findByAgentRunId(id);
            Long agentId = agentIdentityService.requireAgentIdByName(run.getAgentName());
            return ResponseEntity.ok(RunDetailDto.fromEntity(run, transactions, agentId));
        } catch (Exception e) {
            logger.error("Error getting run {}", id, e);
            return ResponseEntity.notFound().build();
        }
    }

    /**
     * Get recent runs (all agents)
     * GET /api/runs/recent?limit=50
     */
    @GetMapping("/recent")
    public ResponseEntity<List<AgentRunDto>> getRecentRuns(
            @RequestParam(defaultValue = "50") int limit) {
        try {
            List<AgentRun> runs = runService.getRecentRuns(limit);
            List<AgentRunDto> dtos = runs.stream()
                    .map(run -> AgentRunDto.fromEntity(run, agentIdentityService.requireAgentIdByName(run.getAgentName())))
                    .collect(Collectors.toList());
            return ResponseEntity.ok(dtos);
        } catch (Exception e) {
            logger.error("Error getting recent runs", e);
            return ResponseEntity.internalServerError().build();
        }
    }

    /**
     * Get recent runs for a specific agent
     * GET /api/runs/agent/{agentId}?limit=20
     */
    @GetMapping("/agent/{agentId}")
    public ResponseEntity<List<AgentRunDto>> getRecentRunsByAgent(
            @PathVariable Long agentId,
            @RequestParam(defaultValue = "20") int limit) {
        try {
            String agentName = agentIdentityService.requireAgentName(agentId);
            List<AgentRun> runs = runService.getRecentRunsByAgent(agentName, limit);
            List<AgentRunDto> dtos = runs.stream()
                    .map(run -> AgentRunDto.fromEntity(run, agentId))
                    .collect(Collectors.toList());
            return ResponseEntity.ok(dtos);
        } catch (Exception e) {
            logger.error("Error getting runs for agent {}", agentId, e);
            return ResponseEntity.internalServerError().build();
        }
    }

    /**
     * Get run statistics for an agent
     * GET /api/runs/agent/{agentId}/stats
     */
    @GetMapping("/agent/{agentId}/stats")
    public ResponseEntity<RunService.RunStatistics> getRunStatistics(@PathVariable Long agentId) {
        try {
            String agentName = agentIdentityService.requireAgentName(agentId);
            RunService.RunStatistics stats = runService.getRunStatistics(agentName);
            return ResponseEntity.ok(stats);
        } catch (Exception e) {
            logger.error("Error getting statistics for agent {}", agentId, e);
            return ResponseEntity.internalServerError().build();
        }
    }
}
