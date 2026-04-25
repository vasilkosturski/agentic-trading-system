package com.trading.controller;

import com.trading.dto.request.CompleteRunRequest;
import com.trading.dto.request.CreateRunRequest;
import com.trading.dto.request.RunQueryFilter;
import com.trading.dto.request.UpdatePhaseRequest;
import com.trading.dto.response.*;
import com.trading.enums.RunPhase;
import com.trading.enums.RunStatus;
import com.trading.enums.TradeDecision;
import com.trading.service.TradingRunService;
import jakarta.validation.Valid;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

import java.net.URI;

/**
 * REST controller for trading run operations.
 * Manages the lifecycle of trading runs from creation through completion.
 *
 * Endpoints:
 * - POST /api/runs - Create a new run
 * - PATCH /api/runs/{id}/phase - Update run phase
 * - PUT /api/runs/{id}/complete - Complete a run with all phase data
 * - GET /api/runs/{id} - Get run with all phases
 * - GET /api/runs/{id}/research - Get research phase
 * - GET /api/runs/{id}/decision - Get decision phase
 * - GET /api/runs/{id}/execution - Get execution phase
 * - GET /api/runs - List runs with filters and pagination
 */
@RestController
@RequestMapping("/api/runs")
public class TradingRunController {

    private final TradingRunService tradingRunService;

    public TradingRunController(TradingRunService tradingRunService) {
        this.tradingRunService = tradingRunService;
    }

    /**
     * Create a new trading run for an agent.
     * POST /api/runs
     *
     * @param request CreateRunRequest with agentId
     * @return TradingRunDto with 201 Created and Location header
     */
    @PostMapping
    public ResponseEntity<TradingRunDto> createRun(@Valid @RequestBody CreateRunRequest request) {
        TradingRunDto result = tradingRunService.createRun(request.getAgentId());
        URI location = ServletUriComponentsBuilder
            .fromCurrentRequest()
            .path("/{id}")
            .buildAndExpand(result.getRunId())
            .toUri();
        return ResponseEntity.created(location).body(result);
    }

    /**
     * Update the phase of a trading run.
     * PATCH /api/runs/{id}/phase
     *
     * @param id the run ID
     * @param request UpdatePhaseRequest with new phase
     * @return 200 OK on success
     */
    @PatchMapping("/{id}/phase")
    public ResponseEntity<Void> updatePhase(
            @PathVariable Long id,
            @Valid @RequestBody UpdatePhaseRequest request) {
        tradingRunService.updatePhase(id, request.getPhase(), request.getErrorMessage());
        return ResponseEntity.ok().build();
    }

    /**
     * Complete a trading run with all phase data.
     * PUT /api/runs/{id}/complete
     *
     * @param id the run ID
     * @param request CompleteRunRequest with all phase data
     * @return 200 OK on success
     */
    @PutMapping("/{id}/complete")
    public ResponseEntity<Void> completeRun(
            @PathVariable Long id,
            @Valid @RequestBody CompleteRunRequest request) {
        tradingRunService.completeRun(id, request);
        return ResponseEntity.ok().build();
    }

    /**
     * Get a trading run with all its phases.
     * GET /api/runs/{id}
     *
     * @param id the run ID
     * @return TradingRunDetailDto with 200 OK
     */
    @GetMapping("/{id}")
    public ResponseEntity<TradingRunDetailDto> getRunWithAllPhases(@PathVariable Long id) {
        TradingRunDetailDto result = tradingRunService.getRunWithAllPhases(id);
        return ResponseEntity.ok(result);
    }

    /**
     * Get the research phase for a run.
     * GET /api/runs/{id}/research
     *
     * @param id the run ID
     * @return ResearchPhaseDto with 200 OK
     */
    @GetMapping("/{id}/research")
    public ResponseEntity<ResearchPhaseDto> getResearchPhase(@PathVariable Long id) {
        ResearchPhaseDto result = tradingRunService.getResearchPhase(id);
        return ResponseEntity.ok(result);
    }

    /**
     * Get the decision phase for a run.
     * GET /api/runs/{id}/decision
     *
     * @param id the run ID
     * @return DecisionPhaseDto with 200 OK
     */
    @GetMapping("/{id}/decision")
    public ResponseEntity<DecisionPhaseDto> getDecisionPhase(@PathVariable Long id) {
        DecisionPhaseDto result = tradingRunService.getDecisionPhase(id);
        return ResponseEntity.ok(result);
    }

    /**
     * Get the execution phase for a run.
     * GET /api/runs/{id}/execution
     *
     * @param id the run ID
     * @return ExecutionPhaseDto with 200 OK, or 404 if HOLD decision
     */
    @GetMapping("/{id}/execution")
    public ResponseEntity<ExecutionPhaseDto> getExecutionPhase(@PathVariable Long id) {
        ExecutionPhaseDto result = tradingRunService.getExecutionPhase(id);
        return ResponseEntity.ok(result);
    }

    /**
     * List trading runs with optional filters and pagination.
     * GET /api/runs?agentId=&status=&decision=&symbol=&page=&size=&sort=&showAll=
     *
     * @param agentId optional filter by agent ID
     * @param status optional filter by run status
     * @param decision optional filter by trade decision
     * @param symbol optional filter by symbol
     * @param showAll optional flag to bypass 7-day delay filter (for debugging)
     * @param page page number (0-based, default 0)
     * @param size page size (default 20)
     * @param sort sort field (default "startedAt")
     * @param direction sort direction (default "desc")
     * @return RunListResponseDto with 200 OK
     */
    @GetMapping
    public ResponseEntity<RunListResponseDto> listRuns(
            @RequestParam(required = false) Long agentId,
            @RequestParam(required = false) RunStatus status,
            @RequestParam(required = false) TradeDecision decision,
            @RequestParam(required = false) String symbol,
            @RequestParam(required = false, defaultValue = "false") boolean showAll,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(defaultValue = "startedAt") String sort,
            @RequestParam(defaultValue = "desc") String direction) {

        // Build filter
        RunQueryFilter filter = null;
        if (agentId != null || status != null || decision != null || symbol != null) {
            filter = new RunQueryFilter(agentId, status, decision, symbol);
        }

        // Build pageable
        Sort.Direction sortDirection = "asc".equalsIgnoreCase(direction)
            ? Sort.Direction.ASC
            : Sort.Direction.DESC;
        Pageable pageable = PageRequest.of(page, size, Sort.by(sortDirection, sort));

        RunListResponseDto result = tradingRunService.listRuns(filter, pageable, showAll);
        return ResponseEntity.ok(result);
    }
}
