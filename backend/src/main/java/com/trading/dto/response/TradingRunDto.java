package com.trading.dto.response;

import com.trading.entity.DecisionPhase;
import com.trading.entity.TradingRun;
import com.trading.enums.RunPhase;
import com.trading.enums.RunStatus;
import com.trading.enums.TradeDecision;
import java.time.Instant;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

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
    private TradeDecision decision; // from joined decision_phases
    private String symbol; // from joined decision_phases
    private Instant startedAt;
    private Instant completedAt;
    private String errorMessage;

    /**
     * Factory method to create DTO from TradingRun entity.
     * Decision and symbol fields remain null (populated via join in listRuns).
     */
    public static TradingRunDto fromEntity(TradingRun run) {
        TradingRunDto dto = new TradingRunDto();
        dto.setRunId(run.getId());
        dto.setAgentId(run.getAgent().getId());
        dto.setStatus(run.getStatus());
        dto.setPhase(run.getPhase());
        dto.setStartedAt(run.getStartedAt());
        dto.setCompletedAt(run.getCompletedAt());
        dto.setErrorMessage(run.getErrorMessage());
        return dto;
    }

    /**
     * Factory method to create DTO from TradingRun with joined DecisionPhase.
     * Used in listRuns() queries with join.
     */
    public static TradingRunDto fromEntityWithDecision(TradingRun run, DecisionPhase decisionPhase) {
        TradingRunDto dto = fromEntity(run);
        if (decisionPhase != null) {
            dto.setDecision(decisionPhase.getDecision());
            dto.setSymbol(decisionPhase.getSymbol());
        }
        return dto;
    }
}
