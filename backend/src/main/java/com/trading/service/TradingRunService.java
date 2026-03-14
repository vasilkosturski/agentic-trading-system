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
import com.trading.repository.*;
import com.trading.specification.TradingRunSpecification;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

/**
 * Service for managing trading runs and their phases.
 * Handles the complete trading cycle lifecycle:
 * INITIALIZING -> RESEARCHING -> DECIDING -> TRADING -> COMPLETED
 */
@Service
@Transactional
public class TradingRunService {

    private static final Logger logger = LoggerFactory.getLogger(TradingRunService.class);

    // WebSocket destinations
    private static final String TOPIC_PHASES = "/topic/runs/phases";
    private static final String TOPIC_DECISIONS = "/topic/runs/decisions";

    private final TradingRunRepository tradingRunRepository;
    private final ResearchPhaseRepository researchPhaseRepository;
    private final DecisionPhaseRepository decisionPhaseRepository;
    private final ExecutionPhaseRepository executionPhaseRepository;
    private final TradingAgentRepository tradingAgentRepository;
    private final AccountTransactionRepository accountTransactionRepository;
    private final SimpMessagingTemplate messagingTemplate;

    /**
     * Constructor injection for all dependencies.
     */
    public TradingRunService(
            TradingRunRepository tradingRunRepository,
            ResearchPhaseRepository researchPhaseRepository,
            DecisionPhaseRepository decisionPhaseRepository,
            ExecutionPhaseRepository executionPhaseRepository,
            TradingAgentRepository tradingAgentRepository,
            AccountTransactionRepository accountTransactionRepository,
            SimpMessagingTemplate messagingTemplate) {
        this.tradingRunRepository = tradingRunRepository;
        this.researchPhaseRepository = researchPhaseRepository;
        this.decisionPhaseRepository = decisionPhaseRepository;
        this.executionPhaseRepository = executionPhaseRepository;
        this.tradingAgentRepository = tradingAgentRepository;
        this.accountTransactionRepository = accountTransactionRepository;
        this.messagingTemplate = messagingTemplate;
    }

    // ========== 3.2 createRun ==========

    /**
     * Create a new trading run for an agent.
     * Initializes run with status=IN_PROGRESS, phase=INITIALIZING.
     * Broadcasts phase_update via WebSocket.
     *
     * @param agentId ID of the trading agent
     * @return TradingRunDto for the created run
     * @throws ResourceNotFoundException if agent not found
     */
    public TradingRunDto createRun(Long agentId) {
        logger.info("Creating trading run for agent ID: {}", agentId);

        TradingAgent agent = tradingAgentRepository.findById(agentId)
            .orElseThrow(() -> new ResourceNotFoundException("Agent not found with ID: " + agentId));

        TradingRun run = new TradingRun(agent);
        run = tradingRunRepository.save(run);

        logger.info("Created run ID: {} for agent: {} with phase: {}",
            run.getId(), agent.getName(), run.getPhase());

        // Broadcast phase update
        broadcastPhaseUpdate(run);

        return TradingRunDto.fromEntity(run);
    }

    // ========== 3.3 updatePhase ==========

    /**
     * Update the phase of a trading run.
     * Validates phase transitions according to workflow:
     * INITIALIZING -> RESEARCHING -> DECIDING -> TRADING -> COMPLETED
     * Broadcasts phase_update via WebSocket.
     *
     * @param runId ID of the trading run
     * @param newPhase New phase to transition to
     * @throws ResourceNotFoundException if run not found
     * @throws IllegalArgumentException if transition is invalid
     */
    public void updatePhase(Long runId, RunPhase newPhase) {
        logger.info("Updating phase for run ID: {} to: {}", runId, newPhase);

        TradingRun run = getRun(runId);
        RunPhase currentPhase = run.getPhase();

        validatePhaseTransition(currentPhase, newPhase);

        run.updatePhase(newPhase);
        run = tradingRunRepository.save(run);

        logger.info("Run {} phase updated: {} -> {}", runId, currentPhase, newPhase);

        // Broadcast phase update
        broadcastPhaseUpdate(run);
    }

    // ========== 3.4 completeRun ==========

    /**
     * Complete a trading run with all phase data.
     * Persists ResearchPhase, DecisionPhase, and ExecutionPhase (if BUY/SELL) atomically.
     * Broadcasts decision_completed via WebSocket.
     *
     * @param runId ID of the trading run
     * @param request Complete run request with all phase data
     * @throws ResourceNotFoundException if run not found
     * @throws IllegalArgumentException if validation fails
     */
    @Transactional
    public void completeRun(Long runId, CompleteRunRequest request) {
        // Validate request first
        request.validate();

        // Extract nested DTOs (using request package - different from response DTOs)
        com.trading.dto.request.ResearchPhaseDto researchDto = request.getResearch();
        com.trading.dto.request.DecisionPhaseDto decisionDto = request.getDecision();
        com.trading.dto.request.ExecutionPhaseDto executionDto = request.getExecution();

        TradeDecision tradeDecision = decisionDto.getDecision();
        logger.info("Completing run ID: {} with decision: {}", runId, tradeDecision);

        TradingRun run = getRun(runId);

        // Create and persist research phase (if provided)
        if (researchDto != null) {
            ResearchPhase researchPhase = new ResearchPhase(run);
            researchPhase.setCandidates(researchDto.getCandidates());
            researchPhase.setSources(researchDto.getSources());
            researchPhase.setResearchNotes(researchDto.getNotes());
            researchPhase.setToolCalls(researchDto.getToolCalls());
            researchPhase.setLatencyMs(researchDto.getLatencyMs());
            researchPhaseRepository.save(researchPhase);
        }

        // Create and persist decision phase
        DecisionPhase decisionPhase = new DecisionPhase(run);
        decisionPhase.setDecision(tradeDecision);
        decisionPhase.setSymbol(decisionDto.getSymbol());
        decisionPhase.setQuantity(decisionDto.getQuantity());
        decisionPhase.setReasoning(decisionDto.getReasoning());
        decisionPhase.setSources(decisionDto.getSources());
        decisionPhase.setToolCalls(decisionDto.getToolCalls());
        decisionPhase.setLatencyMs(decisionDto.getLatencyMs());
        decisionPhaseRepository.save(decisionPhase);

        // Create execution phase only for BUY/SELL decisions
        Long tradeId = null;
        if (tradeDecision != TradeDecision.HOLD) {
            ExecutionPhase executionPhase = createExecutionPhase(run, decisionPhase, executionDto);
            executionPhaseRepository.save(executionPhase);
            if (executionPhase.getTrade() != null) {
                tradeId = executionPhase.getTrade().getId();
            }
        }

        // Mark run as completed
        run.markAsCompleted();
        tradingRunRepository.save(run);

        logger.info("Run {} completed with decision: {}, trade ID: {}",
            runId, tradeDecision, tradeId);

        // Broadcast decision completed
        broadcastDecisionCompleted(run, tradeDecision, tradeId);
    }

    // ========== 3.5 getRunWithAllPhases ==========

    /**
     * Get complete run details with all phases.
     *
     * @param runId ID of the trading run
     * @return TradingRunDetailDto with all phase data
     * @throws ResourceNotFoundException if run not found
     */
    @Transactional(readOnly = true)
    public TradingRunDetailDto getRunWithAllPhases(Long runId) {
        logger.debug("Getting run details for ID: {}", runId);

        TradingRun run = getRun(runId);

        // Load phase data
        ResearchPhaseDto researchDto = researchPhaseRepository.findByRunId(runId)
            .map(ResearchPhaseDto::fromEntity)
            .orElse(null);

        DecisionPhaseDto decisionDto = decisionPhaseRepository.findByRunId(runId)
            .map(DecisionPhaseDto::fromEntity)
            .orElse(null);

        ExecutionPhaseDto executionDto = executionPhaseRepository.findByRunId(runId)
            .map(ExecutionPhaseDto::fromEntity)
            .orElse(null);

        // Create run DTO with decision data if available
        TradingRunDto runDto;
        if (decisionDto != null) {
            Optional<DecisionPhase> decisionPhase = decisionPhaseRepository.findByRunId(runId);
            runDto = TradingRunDto.fromEntityWithDecision(run, decisionPhase.orElse(null));
        } else {
            runDto = TradingRunDto.fromEntity(run);
        }

        return new TradingRunDetailDto(runDto, researchDto, decisionDto, executionDto);
    }

    // ========== 3.6 getResearchPhase ==========

    /**
     * Get research phase data for a run.
     *
     * @param runId ID of the trading run
     * @return ResearchPhaseDto
     * @throws ResourceNotFoundException if run or research phase not found
     */
    @Transactional(readOnly = true)
    public ResearchPhaseDto getResearchPhase(Long runId) {
        logger.debug("Getting research phase for run ID: {}", runId);

        // Verify run exists
        if (!tradingRunRepository.existsById(runId)) {
            throw new ResourceNotFoundException("Trading run not found with ID: " + runId);
        }

        return researchPhaseRepository.findByRunId(runId)
            .map(ResearchPhaseDto::fromEntity)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Research phase not found for run ID: " + runId));
    }

    // ========== 3.7 getDecisionPhase ==========

    /**
     * Get decision phase data for a run.
     *
     * @param runId ID of the trading run
     * @return DecisionPhaseDto
     * @throws ResourceNotFoundException if run or decision phase not found
     */
    @Transactional(readOnly = true)
    public DecisionPhaseDto getDecisionPhase(Long runId) {
        logger.debug("Getting decision phase for run ID: {}", runId);

        // Verify run exists
        if (!tradingRunRepository.existsById(runId)) {
            throw new ResourceNotFoundException("Trading run not found with ID: " + runId);
        }

        return decisionPhaseRepository.findByRunId(runId)
            .map(DecisionPhaseDto::fromEntity)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Decision phase not found for run ID: " + runId));
    }

    // ========== 3.8 getExecutionPhase ==========

    /**
     * Get execution phase data for a run.
     * Returns 404 if not found (HOLD decisions don't have execution phase).
     *
     * @param runId ID of the trading run
     * @return ExecutionPhaseDto
     * @throws ResourceNotFoundException if run or execution phase not found
     */
    @Transactional(readOnly = true)
    public ExecutionPhaseDto getExecutionPhase(Long runId) {
        logger.debug("Getting execution phase for run ID: {}", runId);

        // Verify run exists
        if (!tradingRunRepository.existsById(runId)) {
            throw new ResourceNotFoundException("Trading run not found with ID: " + runId);
        }

        return executionPhaseRepository.findByRunId(runId)
            .map(ExecutionPhaseDto::fromEntity)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Execution phase not found for run ID: " + runId +
                " (HOLD decisions do not have an execution phase)"));
    }

    // ========== 3.9 listRuns ==========

    /**
     * List trading runs with optional filtering and pagination.
     * Supports filtering by agentId, status, decision, and symbol.
     *
     * @param filter Optional filter criteria
     * @param pageable Pagination settings
     * @return RunListResponseDto with paginated results
     */
    @Transactional(readOnly = true)
    public RunListResponseDto listRuns(RunQueryFilter filter, Pageable pageable) {
        logger.debug("Listing runs with filter: {}, pageable: {}", filter, pageable);

        Page<TradingRun> page;

        if (filter != null && filter.hasFilters()) {
            page = tradingRunRepository.findAll(
                TradingRunSpecification.fromFilter(filter),
                pageable
            );
        } else {
            page = tradingRunRepository.findAll(pageable);
        }

        // Map to DTOs with decision data
        List<TradingRunDto> runDtos = page.getContent().stream()
            .map(run -> {
                DecisionPhase decisionPhase = decisionPhaseRepository.findByRunId(run.getId())
                    .orElse(null);
                return TradingRunDto.fromEntityWithDecision(run, decisionPhase);
            })
            .toList();

        return new RunListResponseDto(
            runDtos,
            page.getTotalElements(),
            page.getNumber(),
            page.getSize()
        );
    }

    // ========== Helper Methods ==========

    /**
     * Get trading run by ID or throw ResourceNotFoundException.
     */
    private TradingRun getRun(Long runId) {
        return tradingRunRepository.findById(runId)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Trading run not found with ID: " + runId));
    }

    /**
     * Validate phase transition is allowed.
     * Delegates to {@link RunPhase#canTransitionTo(RunPhase)} which encodes the state machine.
     */
    private void validatePhaseTransition(RunPhase currentPhase, RunPhase newPhase) {
        if (!currentPhase.canTransitionTo(newPhase)) {
            throw new IllegalArgumentException(
                "Invalid phase transition: " + currentPhase + " -> " + newPhase);
        }
    }

    /**
     * Create execution phase based on execution DTO.
     */
    private ExecutionPhase createExecutionPhase(TradingRun run, DecisionPhase decisionPhase,
                                                com.trading.dto.request.ExecutionPhaseDto executionDto) {
        ExecutionPhase executionPhase = new ExecutionPhase();
        executionPhase.setRun(run);
        executionPhase.setDecision(decisionPhase);

        if (executionDto != null) {
            Long tradeId = executionDto.getTradeId();
            if (tradeId != null) {
                // Trade was executed - link to transaction
                AccountTransaction trade = accountTransactionRepository.findById(tradeId)
                    .orElse(null);
                executionPhase.setTrade(trade);
            }

            if (executionDto.getStatus() != null) {
                executionPhase.setStatus(executionDto.getStatus());
            } else {
                // Default based on whether trade was successful
                executionPhase.setStatus(tradeId != null
                    ? PhaseStatus.COMPLETED
                    : PhaseStatus.FAILED);
            }

            executionPhase.setErrorDetails(executionDto.getErrorDetails());
        } else {
            // No execution DTO provided - default to failed
            executionPhase.setStatus(PhaseStatus.FAILED);
        }

        return executionPhase;
    }

    /**
     * Broadcast phase update via WebSocket.
     */
    private void broadcastPhaseUpdate(TradingRun run) {
        PhaseUpdateMessage message = new PhaseUpdateMessage(
            run.getAgent().getId(),
            run.getId(),
            run.getPhase().name()
        );

        messagingTemplate.convertAndSend(TOPIC_PHASES, message);
        logger.debug("Broadcast phase_update for run {}: {}", run.getId(), run.getPhase());
    }

    /**
     * Broadcast decision completed via WebSocket.
     */
    private void broadcastDecisionCompleted(TradingRun run, TradeDecision decision, Long tradeId) {
        DecisionCompletedMessage message = new DecisionCompletedMessage(
            run.getAgent().getId(),
            run.getId(),
            decision.name(),
            tradeId
        );

        messagingTemplate.convertAndSend(TOPIC_DECISIONS, message);
        logger.debug("Broadcast decision_completed for run {}: {} (trade: {})",
            run.getId(), decision, tradeId);
    }
}
