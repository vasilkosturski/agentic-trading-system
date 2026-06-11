package com.trading.service;

import com.trading.dto.request.CompleteRunRequest;
import com.trading.dto.request.PhaseFailureRequest;
import com.trading.dto.request.RunQueryFilter;
import com.trading.dto.response.DecisionPhaseDto;
import com.trading.dto.response.ExecutionPhaseDto;
import com.trading.dto.response.ResearchPhaseDto;
import com.trading.dto.response.RunListResponseDto;
import com.trading.dto.response.TradingRunDetailDto;
import com.trading.dto.response.TradingRunDto;
import com.trading.entity.AccountTransaction;
import com.trading.entity.DecisionPhase;
import com.trading.entity.ExecutionPhase;
import com.trading.entity.ResearchPhase;
import com.trading.entity.TradingAgent;
import com.trading.entity.TradingRun;
import com.trading.enums.PhaseStatus;
import com.trading.enums.RunPhase;
import com.trading.enums.TradeDecision;
import com.trading.exception.ResourceNotFoundException;
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.DecisionPhaseRepository;
import com.trading.repository.ExecutionPhaseRepository;
import com.trading.repository.ResearchPhaseRepository;
import com.trading.repository.TradingAgentRepository;
import com.trading.repository.TradingRunRepository;
import java.time.Instant;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class TradingRunService {

    private static final Logger logger = LoggerFactory.getLogger(TradingRunService.class);

    private final TradingRunRepository tradingRunRepository;
    private final ResearchPhaseRepository researchPhaseRepository;
    private final DecisionPhaseRepository decisionPhaseRepository;
    private final ExecutionPhaseRepository executionPhaseRepository;
    private final TradingAgentRepository tradingAgentRepository;
    private final AccountTransactionRepository accountTransactionRepository;
    private final RunDtoMapper runDtoMapper;
    private final RunSpecificationFactory runSpecificationFactory;

    public TradingRunService(
            TradingRunRepository tradingRunRepository,
            ResearchPhaseRepository researchPhaseRepository,
            DecisionPhaseRepository decisionPhaseRepository,
            ExecutionPhaseRepository executionPhaseRepository,
            TradingAgentRepository tradingAgentRepository,
            AccountTransactionRepository accountTransactionRepository,
            RunDtoMapper runDtoMapper,
            RunSpecificationFactory runSpecificationFactory) {
        this.tradingRunRepository = tradingRunRepository;
        this.researchPhaseRepository = researchPhaseRepository;
        this.decisionPhaseRepository = decisionPhaseRepository;
        this.executionPhaseRepository = executionPhaseRepository;
        this.tradingAgentRepository = tradingAgentRepository;
        this.accountTransactionRepository = accountTransactionRepository;
        this.runDtoMapper = runDtoMapper;
        this.runSpecificationFactory = runSpecificationFactory;
    }

    @Transactional
    public TradingRunDto createRun(Long agentId) {
        logger.info("Creating trading run for agent ID: {}", agentId);

        TradingAgent agent = tradingAgentRepository
                .findById(agentId)
                .orElseThrow(() -> new ResourceNotFoundException("Agent not found with ID: " + agentId));

        TradingRun run = new TradingRun(agent);
        run = tradingRunRepository.save(run);

        logger.info("Created run ID: {} for agent: {} with phase: {}", run.getId(), agent.getName(), run.getPhase());

        return TradingRunDto.fromEntity(run);
    }

    @Transactional
    public void updatePhase(Long runId, RunPhase newPhase) {
        updatePhase(runId, newPhase, null);
    }

    @Transactional
    public void updatePhase(Long runId, RunPhase newPhase, String errorMessage) {
        logger.info("Updating phase for run ID: {} to: {}", runId, newPhase);

        TradingRun run = getRun(runId);
        RunPhase currentPhase = run.getPhase();

        RunStateMachine.requireValidTransition(currentPhase, newPhase);

        if (newPhase == RunPhase.FAILED) {
            run.markAsError(errorMessage);
        } else {
            run.updatePhase(newPhase);
        }
        run = tradingRunRepository.save(run);

        logger.info("Run {} phase updated: {} -> {}", runId, currentPhase, newPhase);
    }

    @Transactional
    public void completeRun(Long runId, CompleteRunRequest request) {
        request.validate();

        com.trading.dto.request.ResearchPhaseDto researchDto = request.getResearch();
        com.trading.dto.request.DecisionPhaseDto decisionDto = request.getDecision();
        com.trading.dto.request.ExecutionPhaseDto executionDto = request.getExecution();

        TradeDecision tradeDecision = decisionDto.getDecision();
        logger.info("Completing run ID: {} with decision: {}", runId, tradeDecision);

        TradingRun run = getRun(runId);

        if (researchDto != null) {
            researchPhaseRepository.save(researchDto.toEntity(run));
        }

        DecisionPhase decisionPhase = decisionPhaseRepository.save(decisionDto.toEntity(run));

        Long tradeId = null;
        if (tradeDecision != TradeDecision.HOLD) {
            AccountTransaction trade = null;
            if (executionDto != null && executionDto.getTradeId() != null) {
                trade = accountTransactionRepository
                        .findById(executionDto.getTradeId())
                        .orElse(null);
            }
            ExecutionPhase executionPhase = (executionDto != null)
                    ? executionDto.toEntity(run, decisionPhase, trade)
                    : failedExecution(run, decisionPhase);
            executionPhaseRepository.save(executionPhase);
            if (executionPhase.getTrade() != null) {
                tradeId = executionPhase.getTrade().getId();
            }
        }

        // Guard against silent completion from an illegitimate phase. RunPhase's
        // transition table only permits DECIDING (HOLD path) and TRADING (BUY/SELL
        // path) to reach COMPLETED — any other source phase is a malformed cycle
        // and must fail loud rather than silently flipping the run to COMPLETED.
        RunStateMachine.requireValidTransition(run.getPhase(), RunPhase.COMPLETED);
        run.markAsCompleted();
        tradingRunRepository.save(run);

        logger.info("Run {} completed with decision: {}, trade ID: {}", runId, tradeDecision, tradeId);
    }

    /**
     * Persist a stub research or decision phase row populated with the guardrail
     * outcome columns. Called from the agent orchestrator when the guardrail-retry
     * loop exhausts and the normal {@link #completeRun} pathway is skipped — so
     * {@code outcome='exhausted'} rows still appear in the audit DB.
     *
     * <p>Only the guardrail_* columns carry meaning; other required-not-null fields
     * (latency_ms, candidates, decision) are set to stub defaults to satisfy schema
     * constraints. The run itself is moved to FAILED via the separate
     * {@code updatePhase} call in the lifecycle's fail path.
     *
     * <p><b>Single-writer contract:</b> Callers MUST NOT fire concurrent
     * {@code recordPhaseFailure} POSTs for the same {@code runId}. Both
     * {@code research_phases} and {@code decision_phases} declare a unique
     * constraint on {@code run_id}; the {@code findByRunId(...).orElseGet(new entity)}
     * upsert below is a read-modify-write that races under concurrent fires —
     * two transactions can both read {@code Optional.empty()}, both build a fresh
     * stub, and one will fail the unique constraint on {@code save()}. The
     * canonical FAILED-then-FINALIZE path is single-fire per phase boundary
     * (one agents pod per run), so the race is structurally impossible today.
     * If a future caller violates that contract, escalate to a pessimistic-write
     * lock ({@code @Lock(LockModeType.PESSIMISTIC_WRITE)} on a dedicated
     * {@code findByRunIdForUpdate} repository method).
     */
    @Transactional
    public void recordPhaseFailure(Long runId, PhaseFailureRequest request) {
        logger.info(
                "Recording phase failure for run ID: {} kind: {} outcome: {}",
                runId,
                request.getPhaseKind(),
                request.getGuardrailOutcome());

        TradingRun run = getRun(runId);
        String outcomeWireValue = request.getGuardrailOutcome().getWireValue();

        if (request.getPhaseKind() == PhaseFailureRequest.PhaseKind.RESEARCH) {
            // Both research_phases and decision_phases declare a unique constraint
            // on run_id. Fall back to upserting the existing row (its guardrail
            // columns get overwritten) instead of blind-saving a fresh entity —
            // a fresh entity would raise DataIntegrityViolationException once a
            // research/decision row has already been written for the run.
            ResearchPhase phase = researchPhaseRepository.findByRunId(runId).orElseGet(() -> {
                ResearchPhase stub = new ResearchPhase(run);
                stub.setCandidates(Collections.emptyList());
                stub.setLatencyMs(0L);
                return stub;
            });
            phase.setGuardrailAttempts(request.getGuardrailAttempts());
            phase.setGuardrailIssues(request.getGuardrailIssues());
            phase.setGuardrailOutcome(outcomeWireValue);
            phase.setGuardrailFailedOutput(request.getGuardrailFailedOutput());
            researchPhaseRepository.save(phase);
        } else {
            DecisionPhase phase = decisionPhaseRepository.findByRunId(runId).orElseGet(() -> {
                DecisionPhase stub = new DecisionPhase(run);
                // HOLD is the schema-safe stub: symbol/quantity are nullable
                // for HOLD, and decision itself is non-nullable so it must
                // carry SOME value.
                stub.setDecision(TradeDecision.HOLD);
                stub.setLatencyMs(0L);
                return stub;
            });
            phase.setGuardrailAttempts(request.getGuardrailAttempts());
            phase.setGuardrailIssues(request.getGuardrailIssues());
            phase.setGuardrailOutcome(outcomeWireValue);
            phase.setGuardrailFailedOutput(request.getGuardrailFailedOutput());
            decisionPhaseRepository.save(phase);
        }

        logger.info("Recorded phase failure stub row for run {} ({})", runId, request.getPhaseKind());
    }

    private ExecutionPhase failedExecution(TradingRun run, DecisionPhase decisionPhase) {
        ExecutionPhase phase = new ExecutionPhase();
        phase.setRun(run);
        phase.setDecision(decisionPhase);
        phase.setStatus(PhaseStatus.FAILED);
        return phase;
    }

    public TradingRunDetailDto getRunWithAllPhases(Long runId) {
        logger.debug("Getting run details for ID: {}", runId);

        TradingRun run = getRun(runId);

        Optional<ResearchPhase> research = researchPhaseRepository.findByRunId(runId);
        Optional<DecisionPhase> decision = decisionPhaseRepository.findByRunId(runId);
        Optional<ExecutionPhase> execution = executionPhaseRepository.findByRunId(runId);

        return runDtoMapper.assembleDetail(run, research, decision, execution);
    }

    public ResearchPhaseDto getResearchPhase(Long runId) {
        logger.debug("Getting research phase for run ID: {}", runId);

        if (!tradingRunRepository.existsById(runId)) {
            throw new ResourceNotFoundException("Trading run not found with ID: " + runId);
        }

        return researchPhaseRepository
                .findByRunId(runId)
                .map(ResearchPhaseDto::fromEntity)
                .orElseThrow(() -> new ResourceNotFoundException("Research phase not found for run ID: " + runId));
    }

    public DecisionPhaseDto getDecisionPhase(Long runId) {
        logger.debug("Getting decision phase for run ID: {}", runId);

        if (!tradingRunRepository.existsById(runId)) {
            throw new ResourceNotFoundException("Trading run not found with ID: " + runId);
        }

        return decisionPhaseRepository
                .findByRunId(runId)
                .map(DecisionPhaseDto::fromEntity)
                .orElseThrow(() -> new ResourceNotFoundException("Decision phase not found for run ID: " + runId));
    }

    public ExecutionPhaseDto getExecutionPhase(Long runId) {
        logger.debug("Getting execution phase for run ID: {}", runId);

        if (!tradingRunRepository.existsById(runId)) {
            throw new ResourceNotFoundException("Trading run not found with ID: " + runId);
        }

        return executionPhaseRepository
                .findByRunId(runId)
                .map(ExecutionPhaseDto::fromEntity)
                .orElseThrow(
                        () -> new ResourceNotFoundException("Execution phase not found for run ID: " + runId + ""));
    }

    private TradingRun getRun(Long runId) {
        return tradingRunRepository
                .findById(runId)
                .orElseThrow(() -> new ResourceNotFoundException("Trading run not found with ID: " + runId));
    }

    public RunListResponseDto listRuns(RunQueryFilter filter, Instant cutoffDate, Pageable pageable) {
        logger.debug("Listing runs with filter: {}, cutoffDate: {}, pageable: {}", filter, cutoffDate, pageable);

        Page<TradingRun> page =
                tradingRunRepository.findAll(runSpecificationFactory.build(filter, cutoffDate), pageable);

        List<TradingRunDto> runDtos = page.getContent().stream()
                .map(run -> {
                    DecisionPhase decisionPhase =
                            decisionPhaseRepository.findByRunId(run.getId()).orElse(null);
                    return runDtoMapper.assembleListRow(run, decisionPhase);
                })
                .toList();

        return new RunListResponseDto(runDtos, page.getTotalElements(), page.getNumber(), page.getSize());
    }
}
