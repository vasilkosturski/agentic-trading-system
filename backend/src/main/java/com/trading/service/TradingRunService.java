package com.trading.service;

import com.trading.config.TradingPublicProperties;
import com.trading.dto.request.CompleteRunRequest;
import com.trading.dto.request.RunQueryFilter;
import com.trading.dto.response.*;
import com.trading.dto.websocket.DecisionCompletedMessage;
import com.trading.dto.websocket.PhaseUpdateMessage;
import com.trading.entity.*;
import com.trading.enums.PhaseStatus;
import com.trading.enums.RunPhase;
import com.trading.enums.TradeDecision;
import com.trading.exception.ResourceNotFoundException;
import com.trading.messaging.RunEventPublisher;
import com.trading.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

/**
 * Service for managing trading runs and their phases.
 * Handles the complete trading cycle lifecycle:
 * INITIALIZING -> RESEARCHING -> DECIDING -> TRADING -> COMPLETED
 *
 * <p>Read-only by default; write operations override with their own
 * {@code @Transactional} so the read-only flag does not silently drop saves.
 */
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
    private final RunEventPublisher runEventPublisher;
    private final RunDtoMapper runDtoMapper;
    private final RunSpecificationFactory runSpecificationFactory;

    public TradingRunService(
            TradingRunRepository tradingRunRepository,
            ResearchPhaseRepository researchPhaseRepository,
            DecisionPhaseRepository decisionPhaseRepository,
            ExecutionPhaseRepository executionPhaseRepository,
            TradingAgentRepository tradingAgentRepository,
            AccountTransactionRepository accountTransactionRepository,
            RunEventPublisher runEventPublisher,
            RunDtoMapper runDtoMapper,
            RunSpecificationFactory runSpecificationFactory) {
        this.tradingRunRepository = tradingRunRepository;
        this.researchPhaseRepository = researchPhaseRepository;
        this.decisionPhaseRepository = decisionPhaseRepository;
        this.executionPhaseRepository = executionPhaseRepository;
        this.tradingAgentRepository = tradingAgentRepository;
        this.accountTransactionRepository = accountTransactionRepository;
        this.runEventPublisher = runEventPublisher;
        this.runDtoMapper = runDtoMapper;
        this.runSpecificationFactory = runSpecificationFactory;
    }

    @Transactional
    public TradingRunDto createRun(Long agentId) {
        logger.info("Creating trading run for agent ID: {}", agentId);

        TradingAgent agent = tradingAgentRepository.findById(agentId)
            .orElseThrow(() -> new ResourceNotFoundException("Agent not found with ID: " + agentId));

        TradingRun run = new TradingRun(agent);
        run = tradingRunRepository.save(run);

        logger.info("Created run ID: {} for agent: {} with phase: {}",
            run.getId(), agent.getName(), run.getPhase());

        broadcastPhaseUpdate(run);

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

        broadcastPhaseUpdate(run);
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
                trade = accountTransactionRepository.findById(executionDto.getTradeId()).orElse(null);
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

        logger.info("Run {} completed with decision: {}, trade ID: {}",
            runId, tradeDecision, tradeId);

        broadcastDecisionCompleted(run, tradeDecision, tradeId);
    }

    /**
     * Builds the synthetic FAILED execution phase used when {@code completeRun}
     * receives a BUY/SELL decision without an execution DTO. Matches the
     * fallback the previous inline binding produced.
     */
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

        return researchPhaseRepository.findByRunId(runId)
            .map(ResearchPhaseDto::fromEntity)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Research phase not found for run ID: " + runId));
    }

    public DecisionPhaseDto getDecisionPhase(Long runId) {
        logger.debug("Getting decision phase for run ID: {}", runId);

        if (!tradingRunRepository.existsById(runId)) {
            throw new ResourceNotFoundException("Trading run not found with ID: " + runId);
        }

        return decisionPhaseRepository.findByRunId(runId)
            .map(DecisionPhaseDto::fromEntity)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Decision phase not found for run ID: " + runId));
    }

    public ExecutionPhaseDto getExecutionPhase(Long runId) {
        logger.debug("Getting execution phase for run ID: {}", runId);

        if (!tradingRunRepository.existsById(runId)) {
            throw new ResourceNotFoundException("Trading run not found with ID: " + runId);
        }

        return executionPhaseRepository.findByRunId(runId)
            .map(ExecutionPhaseDto::fromEntity)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Execution phase not found for run ID: " + runId +
                ""));
    }

    private TradingRun getRun(Long runId) {
        return tradingRunRepository.findById(runId)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Trading run not found with ID: " + runId));
    }

    private void broadcastPhaseUpdate(TradingRun run) {
        PhaseUpdateMessage message = new PhaseUpdateMessage(
            run.getAgent().getId(),
            run.getId(),
            run.getPhase().name()
        );

        runEventPublisher.publishPhaseUpdate(message);
        logger.debug("Broadcast phase_update for run {}: {}", run.getId(), run.getPhase());
    }

    private void broadcastDecisionCompleted(TradingRun run, TradeDecision decision, Long tradeId) {
        DecisionCompletedMessage message = new DecisionCompletedMessage(
            run.getAgent().getId(),
            run.getId(),
            decision.name(),
            tradeId
        );

        runEventPublisher.publishDecisionCompleted(message);
        logger.debug("Broadcast decision_completed for run {}: {} (trade: {})",
            run.getId(), decision, tradeId);
    }

    /**
     * List trading runs with optional filtering, pagination, and a cutoff date
     * for legal display-delay enforcement.
     *
     * @param filter     optional filter criteria; {@code null} or
     *                   {@code !filter.hasFilters()} skips the filter predicates.
     * @param cutoffDate ceiling for {@code TradingRun.startedAt}; {@code null}
     *                   means "no cutoff" (admin mode — see all runs regardless
     *                   of age). Callers wishing to enforce the public
     *                   display-delay should compute the cutoff from
     *                   {@link TradingPublicProperties#getDisplayDelayDays()}
     *                   and pass it in.
     * @param pageable   page request.
     */
    public RunListResponseDto listRuns(RunQueryFilter filter, Instant cutoffDate, Pageable pageable) {
        logger.debug("Listing runs with filter: {}, cutoffDate: {}, pageable: {}", filter, cutoffDate, pageable);

        Page<TradingRun> page = tradingRunRepository.findAll(
            runSpecificationFactory.build(filter, cutoffDate),
            pageable);

        // Map to DTOs with decision data
        List<TradingRunDto> runDtos = page.getContent().stream()
            .map(run -> {
                DecisionPhase decisionPhase = decisionPhaseRepository.findByRunId(run.getId())
                    .orElse(null);
                return runDtoMapper.assembleListRow(run, decisionPhase);
            })
            .toList();

        return new RunListResponseDto(
            runDtos,
            page.getTotalElements(),
            page.getNumber(),
            page.getSize()
        );
    }
}
