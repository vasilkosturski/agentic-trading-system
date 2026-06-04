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

/**
 * Assembles response DTOs for trading runs by composing the static {@code fromEntity*}
 * factories on the individual DTO classes.
 *
 * Owns the assembly logic that lived inline in {@code TradingRunService}: the
 * choice between {@link TradingRunDto#fromEntity(TradingRun)} and
 * {@link TradingRunDto#fromEntityWithDecision(TradingRun, DecisionPhase)},
 * and construction of the container DTO {@link TradingRunDetailDto}.
 *
 * Pure assembly: no repository or persistence dependencies. Phase data is supplied
 * pre-loaded by the caller, which keeps each public service method's query count fixed.
 */
@Component
public class RunDtoMapper {

    /**
     * Build the detail view for a single trading run.
     *
     * @param run       the trading run (required)
     * @param research  the run's research phase, if any
     * @param decision  the run's decision phase, if any — when present, the
     *                  inner run DTO carries the joined {@code decision} and
     *                  {@code symbol} fields
     * @param execution the run's execution phase, if any
     * @return assembled detail DTO with nested phase DTOs left null when absent
     */
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

    /**
     * Build a list-row DTO for a single trading run, joining the decision phase
     * when one is supplied.
     *
     * @param run      the trading run (required)
     * @param decision the run's decision phase, or {@code null} when no decision
     *                 has been recorded yet
     * @return list-row DTO with {@code decision}/{@code symbol} populated iff
     *         {@code decision != null}
     */
    public TradingRunDto assembleListRow(TradingRun run, DecisionPhase decision) {
        if (decision != null) {
            return TradingRunDto.fromEntityWithDecision(run, decision);
        }
        return TradingRunDto.fromEntity(run);
    }
}
