package com.trading.controller;

import com.trading.dto.request.*;
import com.trading.dto.response.AgentRunDto;
import com.trading.dto.response.RunDetailDto;
import com.trading.dto.response.ToolResponse;
import com.trading.entity.AccountTransaction;
import com.trading.entity.AgentRun;
import com.trading.entity.AgentToolCall;
import com.trading.entity.AgentReasoningStep;
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.AgentToolCallRepository;
import com.trading.repository.AgentReasoningStepRepository;
import com.trading.service.AgentIdentityService;
import com.trading.service.RunService;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
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
    private AgentToolCallRepository toolCallRepository;

    @Autowired
    private AgentReasoningStepRepository reasoningStepRepository;

    @Autowired
    private AgentIdentityService agentIdentityService;

    /**
     * Start a new agent run
     * POST /api/runs/start
     */
    @PostMapping("/start")
    public ResponseEntity<ToolResponse<Long>> startRun(@Valid @RequestBody StartRunRequest request) {
        String agentName = agentIdentityService.requireAgentName(request.getAgentId());
        AgentRun run = runService.startRun(
            agentName,
            request.getRunType(),
            request.getMarketConditions()
        );
        return ResponseEntity.status(201).body(ToolResponse.success(run.getId()));
    }

    /**
     * End an agent run
     * POST /api/runs/end
     */
    @PostMapping("/end")
    public ResponseEntity<ToolResponse<String>> endRun(@Valid @RequestBody EndRunRequest request) {
        Integer tradeCount = request.getTradeCount() != null ? request.getTradeCount() : 0;

        AgentRun run;
        if (tradeCount > 0) {
            run = runService.endRunWithTrades(
                request.getRunId(),
                request.getSummary(),
                request.getFullReasoning(),
                request.getResearchSources(),
                request.getHistoricalContext(),
                tradeCount
            );
        } else {
            run = runService.endRunWithNoTrade(
                request.getRunId(),
                request.getSummary(),
                request.getFullReasoning(),
                request.getResearchSources(),
                request.getHistoricalContext()
            );
        }

        return ResponseEntity.ok(ToolResponse.success(
            "Run " + request.getRunId() + " ended with outcome: " + run.getOutcome()));
    }

    /**
     * Mark a run as error
     * POST /api/runs/error
     */
    @PostMapping("/error")
    public ResponseEntity<ToolResponse<String>> markRunAsError(@Valid @RequestBody MarkRunAsErrorRequest request) {
        runService.markRunAsError(request.getRunId(), request.getErrorMessage());
        return ResponseEntity.ok(ToolResponse.success("Run " + request.getRunId() + " marked as error"));
    }

    /**
     * Log a tool call for a run
     * POST /api/runs/{runId}/tool-call
     */
    @PostMapping("/{runId}/tool-call")
    public ResponseEntity<ToolResponse<Long>> logToolCall(
            @PathVariable Long runId,
            @Valid @RequestBody LogToolCallRequest request) {

        Long durationMs = request.getDurationMs();
        Boolean success = request.getSuccess() != null ? request.getSuccess() : true;
        java.time.Instant timestamp = java.time.Instant.parse(request.getTimestamp());

        AgentToolCall toolCall = new AgentToolCall(
            runId,
            request.getToolName(),
            request.getInputParams(),
            request.getOutputResult(),
            timestamp,
            durationMs,
            success,
            request.getErrorMessage(),
            request.getSequenceNumber()
        );
        AgentToolCall saved = toolCallRepository.save(toolCall);

        return ResponseEntity.status(201).body(ToolResponse.success(saved.getId()));
    }

    /**
     * Log a reasoning step for a run
     * POST /api/runs/{runId}/reasoning-step
     */
    @PostMapping("/{runId}/reasoning-step")
    public ResponseEntity<ToolResponse<Long>> logReasoningStep(
            @PathVariable Long runId,
            @Valid @RequestBody LogReasoningStepRequest request) {

        java.time.Instant timestamp = java.time.Instant.parse(request.getTimestamp());

        AgentReasoningStep reasoningStep = new AgentReasoningStep(
            runId,
            request.getStepType(),
            request.getStepDescription(),
            request.getReasoningText(),
            timestamp,
            request.getSequenceNumber()
        );
        AgentReasoningStep saved = reasoningStepRepository.save(reasoningStep);

        return ResponseEntity.status(201).body(ToolResponse.success(saved.getId()));
    }

    /**
     * Get a specific run by ID with trades, tool calls, and reasoning steps
     * GET /api/runs/{id}
     */
    @GetMapping("/{id}")
    public ResponseEntity<RunDetailDto> getRun(@PathVariable Long id) {
        AgentRun run = runService.getRun(id);
        List<AccountTransaction> transactions = transactionRepository.findByAgentRunId(id);
        List<AgentToolCall> toolCalls = toolCallRepository.findByAgentRunIdOrderBySequenceNumberAsc(id);
        List<AgentReasoningStep> reasoningSteps = reasoningStepRepository.findByAgentRunIdOrderBySequenceNumberAsc(id);
        Long agentId = agentIdentityService.requireAgentIdByName(run.getAgentName());
        return ResponseEntity.ok(RunDetailDto.fromEntity(run, transactions, toolCalls, reasoningSteps, agentId));
    }

    /**
     * Get recent runs (all agents)
     * GET /api/runs/recent?limit=50
     */
    @GetMapping("/recent")
    public ResponseEntity<List<AgentRunDto>> getRecentRuns(
            @RequestParam(defaultValue = "50") int limit) {
        List<AgentRun> runs = runService.getRecentRuns(limit);
        List<AgentRunDto> dtos = runs.stream()
                .map(run -> AgentRunDto.fromEntity(run, agentIdentityService.requireAgentIdByName(run.getAgentName())))
                .collect(Collectors.toList());
        return ResponseEntity.ok(dtos);
    }

    /**
     * Get recent runs for a specific agent
     * GET /api/runs/agent/{agentId}?limit=20
     */
    @GetMapping("/agent/{agentId}")
    public ResponseEntity<List<AgentRunDto>> getRecentRunsByAgent(
            @PathVariable Long agentId,
            @RequestParam(defaultValue = "20") int limit) {
        String agentName = agentIdentityService.requireAgentName(agentId);
        List<AgentRun> runs = runService.getRecentRunsByAgent(agentName, limit);
        List<AgentRunDto> dtos = runs.stream()
                .map(run -> AgentRunDto.fromEntity(run, agentId))
                .collect(Collectors.toList());
        return ResponseEntity.ok(dtos);
    }

    /**
     * Get run statistics for an agent
     * GET /api/runs/agent/{agentId}/stats
     */
    @GetMapping("/agent/{agentId}/stats")
    public ResponseEntity<RunService.RunStatistics> getRunStatistics(@PathVariable Long agentId) {
        String agentName = agentIdentityService.requireAgentName(agentId);
        RunService.RunStatistics stats = runService.getRunStatistics(agentName);
        return ResponseEntity.ok(stats);
    }
}
