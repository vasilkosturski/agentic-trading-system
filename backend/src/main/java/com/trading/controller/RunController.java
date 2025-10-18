package com.trading.controller;

import com.trading.dto.AgentRunDto;
import com.trading.dto.ToolResponse;
import com.trading.entity.AgentRun;
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
@CrossOrigin(origins = {"http://localhost:3000", "http://localhost:5173"})
public class RunController {

    private static final Logger logger = LoggerFactory.getLogger(RunController.class);

    @Autowired
    private RunService runService;

    /**
     * Start a new agent run
     * POST /api/runs/start
     * Body: { "agentName": "Warren", "runType": "TRADING", "agentContext": "{...}", "marketConditions": "{...}" }
     */
    @PostMapping("/start")
    public ResponseEntity<ToolResponse<Long>> startRun(@RequestBody Map<String, String> request) {
        try {
            String agentName = request.get("agentName");
            String runType = request.get("runType");
            String agentContext = request.get("agentContext");
            String marketConditions = request.get("marketConditions");

            AgentRun run = runService.startRun(agentName, runType, agentContext, marketConditions);
            return ResponseEntity.ok(new ToolResponse<>(true, run.getId(), null));
        } catch (Exception e) {
            logger.error("Error starting run", e);
            return ResponseEntity.ok(new ToolResponse<>(false, null, e.getMessage()));
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

            return ResponseEntity.ok(new ToolResponse<>(true,
                    "Run " + runId + " ended with outcome: " + run.getOutcome(), null));
        } catch (Exception e) {
            logger.error("Error ending run", e);
            return ResponseEntity.ok(new ToolResponse<>(false, null, e.getMessage()));
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
            return ResponseEntity.ok(new ToolResponse<>(true, "Run " + runId + " marked as error", null));
        } catch (Exception e) {
            logger.error("Error marking run as error", e);
            return ResponseEntity.ok(new ToolResponse<>(false, null, e.getMessage()));
        }
    }

    /**
     * Get a specific run by ID
     * GET /api/runs/{id}
     */
    @GetMapping("/{id}")
    public ResponseEntity<AgentRunDto> getRun(@PathVariable Long id) {
        try {
            AgentRun run = runService.getRun(id);
            return ResponseEntity.ok(AgentRunDto.fromEntity(run));
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
                    .map(AgentRunDto::fromEntity)
                    .collect(Collectors.toList());
            return ResponseEntity.ok(dtos);
        } catch (Exception e) {
            logger.error("Error getting recent runs", e);
            return ResponseEntity.internalServerError().build();
        }
    }

    /**
     * Get recent runs for a specific agent
     * GET /api/runs/agent/{agentName}?limit=20
     */
    @GetMapping("/agent/{agentName}")
    public ResponseEntity<List<AgentRunDto>> getRecentRunsByAgent(
            @PathVariable String agentName,
            @RequestParam(defaultValue = "20") int limit) {
        try {
            List<AgentRun> runs = runService.getRecentRunsByAgent(agentName, limit);
            List<AgentRunDto> dtos = runs.stream()
                    .map(AgentRunDto::fromEntity)
                    .collect(Collectors.toList());
            return ResponseEntity.ok(dtos);
        } catch (Exception e) {
            logger.error("Error getting runs for agent {}", agentName, e);
            return ResponseEntity.internalServerError().build();
        }
    }

    /**
     * Get run statistics for an agent
     * GET /api/runs/agent/{agentName}/stats
     */
    @GetMapping("/agent/{agentName}/stats")
    public ResponseEntity<RunService.RunStatistics> getRunStatistics(@PathVariable String agentName) {
        try {
            RunService.RunStatistics stats = runService.getRunStatistics(agentName);
            return ResponseEntity.ok(stats);
        } catch (Exception e) {
            logger.error("Error getting statistics for agent {}", agentName, e);
            return ResponseEntity.internalServerError().build();
        }
    }
}
