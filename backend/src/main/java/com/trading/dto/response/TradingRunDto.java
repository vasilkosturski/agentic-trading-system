package com.trading.dto.response;

import com.trading.entity.DecisionPhase;
import com.trading.entity.TradingRun;
import com.trading.enums.RunPhase;
import com.trading.enums.RunStatus;
import com.trading.enums.TradeDecision;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * Minimal DTO for trading run list views.
 * Per design.md: Optimized for list endpoints, includes joined decision data.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TradingRunDto {
    private Long runId;
    private Long agentId;
    private RunStatus status;
    private RunPhase phase;
    private TradeDecision decision;  // from joined decision_phases
    private String symbol;           // from joined decision_phases
    private Instant startedAt;
    private Instant completedAt;

    /**
     * Factory method to create DTO from TradingRun entity.
     * Decision and symbol fields remain null (populated via join in listRuns).
     */
    public static TradingRunDto fromEntity(TradingRun run) {
        return new TradingRunDto(
            run.getId(),
            run.getAgent().getId(),
            run.getStatus(),
            run.getPhase(),
            null,  // decision populated via join
            null,  // symbol populated via join
            run.getStartedAt(),
            run.getCompletedAt()
        );
    }

    /**
     * Factory method to create DTO from TradingRun with joined DecisionPhase.
     * Used in listRuns() queries with join.
     */
    public static TradingRunDto fromEntityWithDecision(TradingRun run, DecisionPhase decisionPhase) {
        return new TradingRunDto(
            run.getId(),
            run.getAgent().getId(),
            run.getStatus(),
            run.getPhase(),
            decisionPhase != null ? decisionPhase.getDecision() : null,
            decisionPhase != null ? decisionPhase.getSymbol() : null,
            run.getStartedAt(),
            run.getCompletedAt()
        );
    }
}
