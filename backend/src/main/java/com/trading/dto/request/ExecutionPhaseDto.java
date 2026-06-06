package com.trading.dto.request;

import com.trading.entity.AccountTransaction;
import com.trading.entity.DecisionPhase;
import com.trading.entity.ExecutionPhase;
import com.trading.entity.TradingRun;
import com.trading.enums.PhaseStatus;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ExecutionPhaseDto {

    private Long tradeId;

    private PhaseStatus status;

    private String errorDetails;

    public ExecutionPhase toEntity(TradingRun run, DecisionPhase decisionPhase, AccountTransaction resolvedTrade) {
        ExecutionPhase phase = new ExecutionPhase();
        phase.setRun(run);
        phase.setDecision(decisionPhase);
        phase.setTrade(resolvedTrade);
        if (status != null) {
            phase.setStatus(status);
        } else {
            phase.setStatus(tradeId != null ? PhaseStatus.COMPLETED : PhaseStatus.FAILED);
        }
        phase.setErrorDetails(errorDetails);
        return phase;
    }
}
