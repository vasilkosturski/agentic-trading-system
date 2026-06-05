package com.trading.controller;

import com.trading.config.TradingPublicProperties;
import com.trading.dto.request.CompleteRunRequest;
import com.trading.dto.request.CreateRunRequest;
import com.trading.dto.request.RunQueryFilter;
import com.trading.dto.request.UpdatePhaseRequest;
import com.trading.dto.response.DecisionPhaseDto;
import com.trading.dto.response.ExecutionPhaseDto;
import com.trading.dto.response.ResearchPhaseDto;
import com.trading.dto.response.RunListResponseDto;
import com.trading.dto.response.TradingRunDetailDto;
import com.trading.dto.response.TradingRunDto;
import com.trading.enums.RunStatus;
import com.trading.enums.TradeDecision;
import com.trading.service.TradingRunService;
import jakarta.validation.Valid;
import java.net.URI;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

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
    private final TradingPublicProperties tradingPublicProperties;

    public TradingRunController(TradingRunService tradingRunService, TradingPublicProperties tradingPublicProperties) {
        this.tradingRunService = tradingRunService;
        this.tradingPublicProperties = tradingPublicProperties;
    }

    /**
     * Create a new trading run for an agent.
     * POST /api/runs
     *
     * @param request CreateRunRequest with agentId
     * @return TradingRunDto with 201 Created and Location header
     */
    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<TradingRunDto> createRun(@Valid @RequestBody CreateRunRequest request) {
        TradingRunDto result = tradingRunService.createRun(request.getAgentId());
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
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
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Void> updatePhase(@PathVariable Long id, @Valid @RequestBody UpdatePhaseRequest request) {
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
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Void> completeRun(@PathVariable Long id, @Valid @RequestBody CompleteRunRequest request) {
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
     * Returns only runs from the last 7 days (legal data protection).
     * For unrestricted access to all runs, use the admin endpoint (requires authentication).
     * GET /api/runs?agentId=&status=&decision=&symbol=&page=&size=&sort=
     *
     * @param agentId optional filter by agent ID
     * @param status optional filter by run status
     * @param decision optional filter by trade decision
     * @param symbol optional filter by symbol
     * @param page page number (0-based, default 0)
     * @param size page size (default 20)
     * @param sort sort field (default "startedAt")
     * @param direction sort direction (default "desc")
     * @return RunListResponseDto with 200 OK (limited to last 7 days)
     */
    @GetMapping
    public ResponseEntity<RunListResponseDto> listRuns(
            @RequestParam(required = false) Long agentId,
            @RequestParam(required = false) RunStatus status,
            @RequestParam(required = false) TradeDecision decision,
            @RequestParam(required = false) String symbol,
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
        Sort.Direction sortDirection = "asc".equalsIgnoreCase(direction) ? Sort.Direction.ASC : Sort.Direction.DESC;
        Pageable pageable = PageRequest.of(page, size, Sort.by(sortDirection, sort));

        // Always enforce display delay for legal data protection on public endpoint
        Instant cutoffDate = Instant.now().minus(tradingPublicProperties.getDisplayDelayDays(), ChronoUnit.DAYS);
        RunListResponseDto result = tradingRunService.listRuns(filter, cutoffDate, pageable);
        return ResponseEntity.ok(result);
    }

    /**
     * List all trading runs for admin users (no date filter).
     * Requires HTTP Basic Auth with ADMIN role.
     * GET /api/runs/admin?agentId=&status=&decision=&symbol=&page=&size=&sort=&direction=
     *
     * <p>Unlike the public endpoint which enforces a 7-day filter for legal data protection,
     * this endpoint returns ALL runs regardless of age. Use with caution - this bypasses
     * the 7-day public display delay for live trading decisions.</p>
     *
     * <p>Authentication: This endpoint requires HTTP Basic Auth. The browser will show
     * a native authentication popup when accessing this URL. Enter admin credentials
     * to access.</p>
     *
     * @param agentId optional filter by agent ID
     * @param status optional filter by run status
     * @param decision optional filter by trade decision
     * @param symbol optional filter by symbol
     * @param page page number (0-based, default 0)
     * @param size page size (default 20)
     * @param sort sort field (default "startedAt")
     * @param direction sort direction (default "desc")
     * @return RunListResponseDto with 200 OK (includes all runs, no 7-day filter)
     * @throws org.springframework.security.access.AccessDeniedException if user doesn't have ADMIN role (returns 403 Forbidden)
     */
    @GetMapping("/admin")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<RunListResponseDto> listAllRuns(
            @RequestParam(required = false) Long agentId,
            @RequestParam(required = false) RunStatus status,
            @RequestParam(required = false) TradeDecision decision,
            @RequestParam(required = false) String symbol,
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
        Sort.Direction sortDirection = "asc".equalsIgnoreCase(direction) ? Sort.Direction.ASC : Sort.Direction.DESC;
        Pageable pageable = PageRequest.of(page, size, Sort.by(sortDirection, sort));

        // Admin endpoint: pass null cutoff so the service skips the date predicate
        RunListResponseDto result = tradingRunService.listRuns(filter, null, pageable);
        return ResponseEntity.ok(result);
    }
}
