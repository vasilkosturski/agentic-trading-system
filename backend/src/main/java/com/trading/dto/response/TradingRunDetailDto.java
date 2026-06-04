package com.trading.dto.response;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Complete DTO for trading run with all phases.
 * Per design.md: Used by GET /api/runs/{id} to return joined data.
 * Execution phase may be null for HOLD decisions.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TradingRunDetailDto {
    private TradingRunDto run;
    private ResearchPhaseDto research;
    private DecisionPhaseDto decision;
    private ExecutionPhaseDto execution; // may be null
}
