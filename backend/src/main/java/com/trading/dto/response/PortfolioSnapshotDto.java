package com.trading.dto.response;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * DTO for portfolio snapshot returned by API.
 * Used by GET /api/portfolio/snapshots to return historical portfolio data.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PortfolioSnapshotDto {
    private String agentName;
    private Instant timestamp;
    private Double totalValue;
    private Double cashBalance;
    private Double holdingsValue;
    private Double totalPnl;
    private Double totalReturnPercent;
}
