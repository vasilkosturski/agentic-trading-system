package com.trading.service;

import com.trading.dto.response.DecisionPhaseDto;
import com.trading.dto.response.ExecutionPhaseDto;
import com.trading.dto.response.ResearchPhaseDto;
import com.trading.dto.response.TradingRunDetailDto;
import com.trading.dto.response.TradingRunDto;
import com.trading.entity.DecisionPhase;
import com.trading.entity.ExecutionPhase;
import com.trading.entity.ResearchPhase;
import com.trading.entity.TradingRun;
import java.util.Optional;
import org.springframework.stereotype.Component;

@Component
public class RunDtoMapper {

    public TradingRunDetailDto assembleDetail(
            TradingRun run,
            Optional<ResearchPhase> research,
            Optional<DecisionPhase> decision,
            Optional<ExecutionPhase> execution) {

        TradingRunDto runDto = assembleListRow(run, decision.orElse(null));

        ResearchPhaseDto researchDto =
                research.map(ResearchPhaseDto::fromEntity).orElse(null);
        DecisionPhaseDto decisionDto =
                decision.map(DecisionPhaseDto::fromEntity).orElse(null);
        ExecutionPhaseDto executionDto =
                execution.map(ExecutionPhaseDto::fromEntity).orElse(null);

        return new TradingRunDetailDto(runDto, researchDto, decisionDto, executionDto);
    }

    public TradingRunDto assembleListRow(TradingRun run, DecisionPhase decision) {
        if (decision != null) {
            return TradingRunDto.fromEntityWithDecision(run, decision);
        }
        return TradingRunDto.fromEntity(run);
    }
}
