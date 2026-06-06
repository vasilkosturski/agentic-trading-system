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

@RestController
@RequestMapping("/api/runs")
public class TradingRunController {

    private final TradingRunService tradingRunService;
    private final TradingPublicProperties tradingPublicProperties;

    public TradingRunController(TradingRunService tradingRunService, TradingPublicProperties tradingPublicProperties) {
        this.tradingRunService = tradingRunService;
        this.tradingPublicProperties = tradingPublicProperties;
    }

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

    @PatchMapping("/{id}/phase")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Void> updatePhase(@PathVariable Long id, @Valid @RequestBody UpdatePhaseRequest request) {
        tradingRunService.updatePhase(id, request.getPhase(), request.getErrorMessage());
        return ResponseEntity.ok().build();
    }

    @PutMapping("/{id}/complete")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Void> completeRun(@PathVariable Long id, @Valid @RequestBody CompleteRunRequest request) {
        tradingRunService.completeRun(id, request);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/{id}")
    public ResponseEntity<TradingRunDetailDto> getRunWithAllPhases(@PathVariable Long id) {
        TradingRunDetailDto result = tradingRunService.getRunWithAllPhases(id);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/{id}/research")
    public ResponseEntity<ResearchPhaseDto> getResearchPhase(@PathVariable Long id) {
        ResearchPhaseDto result = tradingRunService.getResearchPhase(id);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/{id}/decision")
    public ResponseEntity<DecisionPhaseDto> getDecisionPhase(@PathVariable Long id) {
        DecisionPhaseDto result = tradingRunService.getDecisionPhase(id);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/{id}/execution")
    public ResponseEntity<ExecutionPhaseDto> getExecutionPhase(@PathVariable Long id) {
        ExecutionPhaseDto result = tradingRunService.getExecutionPhase(id);
        return ResponseEntity.ok(result);
    }

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

        RunQueryFilter filter = null;
        if (agentId != null || status != null || decision != null || symbol != null) {
            filter = new RunQueryFilter(agentId, status, decision, symbol);
        }

        Sort.Direction sortDirection = "asc".equalsIgnoreCase(direction) ? Sort.Direction.ASC : Sort.Direction.DESC;
        Pageable pageable = PageRequest.of(page, size, Sort.by(sortDirection, sort));

        Instant cutoffDate = Instant.now().minus(tradingPublicProperties.getDisplayDelayDays(), ChronoUnit.DAYS);
        RunListResponseDto result = tradingRunService.listRuns(filter, cutoffDate, pageable);
        return ResponseEntity.ok(result);
    }

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

        RunQueryFilter filter = null;
        if (agentId != null || status != null || decision != null || symbol != null) {
            filter = new RunQueryFilter(agentId, status, decision, symbol);
        }

        Sort.Direction sortDirection = "asc".equalsIgnoreCase(direction) ? Sort.Direction.ASC : Sort.Direction.DESC;
        Pageable pageable = PageRequest.of(page, size, Sort.by(sortDirection, sort));

        RunListResponseDto result = tradingRunService.listRuns(filter, null, pageable);
        return ResponseEntity.ok(result);
    }
}
