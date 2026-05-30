package com.trading.service;

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
import com.trading.specification.TradingRunSpecification;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;

/**
 * Service for managing trading runs and their phases.
 * Handles the complete trading cycle lifecycle:
 * INITIALIZING -> RESEARCHING -> DECIDING -> TRADING -> COMPLETED
 */
@Service
public class TradingRunService {

    private static final Logger logger = LoggerFactory.getLogger(TradingRunService.class);

    @Value("${trading.public-display-delay-days:7}")
    private int publicDisplayDelayDays;

    private final TradingRunRepository tradingRunRepository;
    private final ResearchPhaseRepository researchPhaseRepository;
    private final DecisionPhaseRepository decisionPhaseRepository;
    private final ExecutionPhaseRepository executionPhaseRepository;
    private final TradingAgentRepository tradingAgentRepository;
    private final AccountTransactionRepository accountTransactionRepository;
    private final RunEventPublisher runEventPublisher;
    private final RunDtoMapper runDtoMapper;

    public TradingRunService(
            TradingRunRepository tradingRunRepository,
            ResearchPhaseRepository researchPhaseRepository,
            DecisionPhaseRepository decisionPhaseRepository,
            ExecutionPhaseRepository executionPhaseRepository,
            TradingAgentRepository tradingAgentRepository,
            AccountTransactionRepository accountTransactionRepository,
            RunEventPublisher runEventPublisher,
            RunDtoMapper runDtoMapper) {
        this.tradingRunRepository = tradingRunRepository;
        this.researchPhaseRepository = researchPhaseRepository;
        this.decisionPhaseRepository = decisionPhaseRepository;
        this.executionPhaseRepository = executionPhaseRepository;
        this.tradingAgentRepository = tradingAgentRepository;
        this.accountTransactionRepository = accountTransactionRepository;
        this.runEventPublisher = runEventPublisher;
        this.runDtoMapper = runDtoMapper;
    }

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

    public void updatePhase(Long runId, RunPhase newPhase) {
        updatePhase(runId, newPhase, null);
    }

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
            ResearchPhase researchPhase = new ResearchPhase(run);
            researchPhase.setCandidates(researchDto.getCandidates());
            researchPhase.setSources(researchDto.getSources());
            researchPhase.setResearchNotes(researchDto.getNotes());
            researchPhase.setToolCalls(researchDto.getToolCalls());
            researchPhase.setLatencyMs(researchDto.getLatencyMs());
            if (researchDto.getMetrics() != null) {
                researchPhase.setMetrics(researchDto.getMetrics().toEntity());
            }
            researchPhase.setSystemPrompt(researchDto.getSystemPrompt());
            researchPhase.setTaskPrompt(researchDto.getTaskPrompt());
            researchPhaseRepository.save(researchPhase);
        }

        DecisionPhase decisionPhase = new DecisionPhase(run);
        decisionPhase.setDecision(tradeDecision);
        decisionPhase.setSymbol(decisionDto.getSymbol());
        decisionPhase.setQuantity(decisionDto.getQuantity());
        decisionPhase.setReasoning(decisionDto.getReasoning());
        decisionPhase.setSources(decisionDto.getSources());
        decisionPhase.setToolCalls(decisionDto.getToolCalls());
        decisionPhase.setLatencyMs(decisionDto.getLatencyMs());
        if (decisionDto.getMetrics() != null) {
            decisionPhase.setMetrics(decisionDto.getMetrics().toEntity());
        }
        decisionPhase.setSystemPrompt(decisionDto.getSystemPrompt());
        decisionPhase.setTaskPrompt(decisionDto.getTaskPrompt());
        decisionPhaseRepository.save(decisionPhase);

        Long tradeId = null;
        if (tradeDecision != TradeDecision.HOLD) {
            ExecutionPhase executionPhase = createExecutionPhase(run, decisionPhase, executionDto);
            executionPhaseRepository.save(executionPhase);
            if (executionPhase.getTrade() != null) {
                tradeId = executionPhase.getTrade().getId();
            }
        }

        run.markAsCompleted();
        tradingRunRepository.save(run);

        logger.info("Run {} completed with decision: {}, trade ID: {}",
            runId, tradeDecision, tradeId);

        broadcastDecisionCompleted(run, tradeDecision, tradeId);
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

    private ExecutionPhase createExecutionPhase(TradingRun run, DecisionPhase decisionPhase,
                                                com.trading.dto.request.ExecutionPhaseDto executionDto) {
        ExecutionPhase executionPhase = new ExecutionPhase();
        executionPhase.setRun(run);
        executionPhase.setDecision(decisionPhase);

        if (executionDto != null) {
            Long tradeId = executionDto.getTradeId();
            if (tradeId != null) {
                AccountTransaction trade = accountTransactionRepository.findById(tradeId)
                    .orElse(null);
                executionPhase.setTrade(trade);
            }

            if (executionDto.getStatus() != null) {
                executionPhase.setStatus(executionDto.getStatus());
            } else {
                executionPhase.setStatus(tradeId != null
                    ? PhaseStatus.COMPLETED
                    : PhaseStatus.FAILED);
            }

            executionPhase.setErrorDetails(executionDto.getErrorDetails());
        } else {
            executionPhase.setStatus(PhaseStatus.FAILED);
        }

        return executionPhase;
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
     * List trading runs with optional filtering and pagination (public endpoint).
     * Always applies 7-day delay filter.
     */
    public RunListResponseDto listRuns(RunQueryFilter filter, Pageable pageable) {
        return listRuns(filter, pageable, false);
    }

    /**
     * List trading runs with optional filtering and pagination.
     * @param showAll If true, bypass 7-day delay filter for debugging
     */
    public RunListResponseDto listRuns(RunQueryFilter filter, Pageable pageable, boolean showAll) {
        logger.debug("Listing runs with filter: {}, pageable: {}, showAll: {}", filter, pageable, showAll);

        Page<TradingRun> page;
        Instant cutoffDate = Instant.now().minus(publicDisplayDelayDays, ChronoUnit.DAYS);

        if (showAll) {
            // Debug mode - show all runs without delay filter
            if (filter != null && filter.hasFilters()) {
                page = tradingRunRepository.findAll(
                    TradingRunSpecification.fromFilter(filter),
                    pageable
                );
            } else {
                page = tradingRunRepository.findAll(pageable);
            }
        } else {
            // Production mode - apply 7-day delay filter at database level
            if (filter != null && filter.hasFilters()) {
                page = tradingRunRepository.findAll(
                    TradingRunSpecification.fromFilterWithDateCutoff(filter, cutoffDate),
                    pageable
                );
            } else {
                page = tradingRunRepository.findByStartedAtBefore(cutoffDate, pageable);
            }
        }

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
