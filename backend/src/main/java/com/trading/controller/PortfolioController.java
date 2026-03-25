package com.trading.controller;

import com.trading.dto.response.PortfolioSnapshotDto;
import com.trading.service.PortfolioService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;

/**
 * REST controller for portfolio snapshot operations.
 * Provides endpoints to retrieve historical portfolio data for charting.
 */
@RestController
@RequestMapping("/api/portfolio")
public class PortfolioController {

    private final PortfolioService portfolioService;

    public PortfolioController(PortfolioService portfolioService) {
        this.portfolioService = portfolioService;
    }

    /**
     * Get portfolio snapshots with optional filtering.
     * GET /api/portfolio/snapshots?agentName=&startDate=&endDate=&limit=
     *
     * @param agentName optional agent name filter
     * @param startDate optional start date (ISO 8601 instant)
     * @param endDate   optional end date (ISO 8601 instant)
     * @param limit     optional maximum number of snapshots to return
     * @return list of portfolio snapshots with 200 OK
     */
    @GetMapping("/snapshots")
    public ResponseEntity<List<PortfolioSnapshotDto>> getSnapshots(
            @RequestParam(required = false) String agentName,
            @RequestParam(required = false) String startDate,
            @RequestParam(required = false) String endDate,
            @RequestParam(required = false) Integer limit) {

        Instant start = startDate != null ? Instant.parse(startDate) : null;
        Instant end = endDate != null ? Instant.parse(endDate) : null;

        List<PortfolioSnapshotDto> snapshots = portfolioService.getSnapshots(agentName, start, end, limit);
        return ResponseEntity.ok(snapshots);
    }
}
