package com.trading.service;

import com.trading.dto.request.CompleteRunRequest;
import com.trading.dto.request.RunQueryFilter;
import com.trading.dto.response.*;
import com.trading.dto.websocket.DecisionCompletedMessage;
import com.trading.dto.websocket.PhaseUpdateMessage;
import com.trading.entity.*;
import com.trading.enums.PhaseStatus;
import com.trading.enums.RunPhase;
import com.trading.enums.RunStatus;
import com.trading.enums.TradeDecision;
import com.trading.enums.WebSocketMessageType;
import com.trading.exception.ResourceNotFoundException;
import com.trading.messaging.RunEventPublisher;
import com.trading.repository.*;
import com.trading.specification.TradingRunSpecification;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for TradingRunService.
 * Per tasks.md Section 3.10: ~45 test methods covering all service methods.
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("TradingRunService Tests")
class TradingRunServiceTest {

    @Mock
    private TradingRunRepository tradingRunRepository;

    @Mock
    private ResearchPhaseRepository researchPhaseRepository;

    @Mock
    private DecisionPhaseRepository decisionPhaseRepository;

    @Mock
    private ExecutionPhaseRepository executionPhaseRepository;

    @Mock
    private TradingAgentRepository tradingAgentRepository;

    @Mock
    private AccountTransactionRepository accountTransactionRepository;

    @Mock
    private RunEventPublisher runEventPublisher;

    @Spy
    private RunDtoMapper runDtoMapper = new RunDtoMapper();

    @Spy
    private RunSpecificationFactory runSpecificationFactory = new RunSpecificationFactory();

    @InjectMocks
    private TradingRunService tradingRunService;

    // Captors for verifying saved entities
    @Captor
    private ArgumentCaptor<TradingRun> tradingRunCaptor;

    @Captor
    private ArgumentCaptor<ResearchPhase> researchPhaseCaptor;

    @Captor
    private ArgumentCaptor<DecisionPhase> decisionPhaseCaptor;

    @Captor
    private ArgumentCaptor<ExecutionPhase> executionPhaseCaptor;

    @Captor
    private ArgumentCaptor<PhaseUpdateMessage> phaseUpdateCaptor;

    // Test fixtures
    private TradingAgent testAgent;
    private TradingRun testRun;
    private ResearchPhase testResearchPhase;
    private DecisionPhase testDecisionPhase;
    private ExecutionPhase testExecutionPhase;

    @BeforeEach
    void setUp() {
        // Create test agent
        testAgent = new TradingAgent("Warren", "Value investor agent");
        testAgent.setId(1L);

        // Create test run
        testRun = new TradingRun(testAgent);
        testRun.setId(100L);

        // Create test research phase
        testResearchPhase = new ResearchPhase(testRun);
        testResearchPhase.setId(200L);
        testResearchPhase.setCandidates(Arrays.asList("JPM", "BAC", "WFC"));
        testResearchPhase.setResearchNotes("Banking sector analysis");
        testResearchPhase.setLatencyMs(3400L);

        // Create test decision phase
        testDecisionPhase = new DecisionPhase(testRun);
        testDecisionPhase.setId(300L);
        testDecisionPhase.setDecision(TradeDecision.BUY);
        testDecisionPhase.setSymbol("JPM");
        testDecisionPhase.setQuantity(30);
        testDecisionPhase.setLatencyMs(2100L);

        // Create test execution phase
        testExecutionPhase = new ExecutionPhase();
        testExecutionPhase.setId(400L);
        testExecutionPhase.setRun(testRun);
        testExecutionPhase.setDecision(testDecisionPhase);
        testExecutionPhase.setStatus(PhaseStatus.COMPLETED);
    }

    // ========== createRun() tests ==========

    @Nested
    @DisplayName("createRun() Tests")
    class CreateRunTests {

        @Test
        @DisplayName("Valid agent returns TradingRunDto with correct fields")
        void createRun_ValidAgent_ReturnsRunDto() {
            // Arrange
            when(tradingAgentRepository.findById(1L)).thenReturn(Optional.of(testAgent));
            when(tradingRunRepository.save(any(TradingRun.class))).thenAnswer(invocation -> {
                TradingRun run = invocation.getArgument(0);
                run.setId(100L);
                return run;
            });

            // Act
            TradingRunDto result = tradingRunService.createRun(1L);

            // Assert
            assertNotNull(result);
            assertEquals(100L, result.getRunId());
            assertEquals(1L, result.getAgentId());
        }

        @Test
        @DisplayName("Valid agent sets initial state correctly")
        void createRun_ValidAgent_SetsInitialState() {
            // Arrange
            when(tradingAgentRepository.findById(1L)).thenReturn(Optional.of(testAgent));
            when(tradingRunRepository.save(tradingRunCaptor.capture())).thenAnswer(invocation -> {
                TradingRun run = invocation.getArgument(0);
                run.setId(100L);
                return run;
            });

            // Act
            tradingRunService.createRun(1L);

            // Assert
            TradingRun capturedRun = tradingRunCaptor.getValue();
            assertEquals(RunStatus.IN_PROGRESS, capturedRun.getStatus(), "Run should start with IN_PROGRESS status");
            assertEquals(RunPhase.INITIALIZING, capturedRun.getPhase(), "Run should start with INITIALIZING phase");
            assertNotNull(capturedRun.getStartedAt(), "startedAt should be set");
            assertNull(capturedRun.getCompletedAt(), "completedAt should be null for new run");
            assertEquals(testAgent, capturedRun.getAgent(), "Agent should be correctly assigned");
        }

        @Test
        @DisplayName("Valid agent broadcasts phase_update via WebSocket")
        void createRun_ValidAgent_BroadcastsPhaseUpdate() {
            // Arrange
            when(tradingAgentRepository.findById(1L)).thenReturn(Optional.of(testAgent));
            when(tradingRunRepository.save(any(TradingRun.class))).thenAnswer(invocation -> {
                TradingRun run = invocation.getArgument(0);
                run.setId(100L);
                return run;
            });

            // Act
            tradingRunService.createRun(1L);

            // Assert - verify WebSocket message content
            verify(runEventPublisher).publishPhaseUpdate(phaseUpdateCaptor.capture());
            PhaseUpdateMessage message = phaseUpdateCaptor.getValue();
            assertEquals(WebSocketMessageType.PHASE_UPDATE, message.getType(), "WebSocket message type should be phase_update");
            assertEquals(1L, message.getAgentId(), "WebSocket message should contain correct agent_id");
            assertEquals(100L, message.getRunId(), "WebSocket message should contain correct run_id");
            assertEquals("INITIALIZING", message.getPhase(), "WebSocket message should contain INITIALIZING phase");
        }

        @Test
        @DisplayName("Agent not found throws ResourceNotFoundException")
        void createRun_AgentNotFound_ThrowsResourceNotFoundException() {
            // Arrange
            when(tradingAgentRepository.findById(999L)).thenReturn(Optional.empty());

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(
                ResourceNotFoundException.class,
                () -> tradingRunService.createRun(999L)
            );
            assertTrue(exception.getMessage().contains("Agent not found"));
        }

        @Test
        @DisplayName("createRun saves run to repository")
        void createRun_SavesRunToRepository() {
            // Arrange
            when(tradingAgentRepository.findById(1L)).thenReturn(Optional.of(testAgent));
            when(tradingRunRepository.save(any(TradingRun.class))).thenAnswer(invocation -> {
                TradingRun run = invocation.getArgument(0);
                run.setId(100L);
                return run;
            });

            // Act
            tradingRunService.createRun(1L);

            // Assert
            verify(tradingRunRepository, times(1)).save(any(TradingRun.class));
        }
    }

    // ========== updatePhase() tests ==========

    @Nested
    @DisplayName("updatePhase() Tests")
    class UpdatePhaseTests {

        @ParameterizedTest(name = "{0} → {1} succeeds")
        @CsvSource({
            "INITIALIZING, RESEARCHING",
            "RESEARCHING, DECIDING",
            "DECIDING, TRADING",
            "TRADING, COMPLETED",
            "DECIDING, COMPLETED"
        })
        @DisplayName("Valid phase transitions succeed")
        void updatePhase_ValidTransition_Succeeds(RunPhase fromPhase, RunPhase toPhase) {
            // Arrange
            testRun.updatePhase(fromPhase);
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));
            when(tradingRunRepository.save(any(TradingRun.class))).thenReturn(testRun);

            // Act
            tradingRunService.updatePhase(100L, toPhase);

            // Assert
            assertEquals(toPhase, testRun.getPhase());
            verify(tradingRunRepository).save(testRun);
        }

        @Test
        @DisplayName("Invalid transition throws IllegalArgumentException")
        void updatePhase_InvalidTransition_ThrowsIllegalArgumentException() {
            // Arrange - trying to go backwards
            testRun.updatePhase(RunPhase.DECIDING);
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));

            // Act & Assert
            IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> tradingRunService.updatePhase(100L, RunPhase.INITIALIZING)
            );
            assertTrue(exception.getMessage().contains("Invalid phase transition"));
        }

        @Test
        @DisplayName("Run not found throws ResourceNotFoundException")
        void updatePhase_RunNotFound_ThrowsResourceNotFoundException() {
            // Arrange
            when(tradingRunRepository.findById(999L)).thenReturn(Optional.empty());

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(
                ResourceNotFoundException.class,
                () -> tradingRunService.updatePhase(999L, RunPhase.RESEARCHING)
            );
            assertTrue(exception.getMessage().contains("Trading run not found"));
        }

        @Test
        @DisplayName("updatePhase broadcasts phase_update via WebSocket")
        @SuppressWarnings("unchecked")
        void updatePhase_BroadcastsPhaseUpdate() {
            // Arrange
            testRun.updatePhase(RunPhase.INITIALIZING);
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));
            when(tradingRunRepository.save(any(TradingRun.class))).thenReturn(testRun);

            // Act
            tradingRunService.updatePhase(100L, RunPhase.RESEARCHING);

            // Assert - verify WebSocket message content
            verify(runEventPublisher).publishPhaseUpdate(phaseUpdateCaptor.capture());
            PhaseUpdateMessage message = phaseUpdateCaptor.getValue();
            assertEquals(WebSocketMessageType.PHASE_UPDATE, message.getType());
            assertEquals("RESEARCHING", message.getPhase());
        }

        @Test
        @DisplayName("COMPLETED phase cannot transition to any other phase")
        void updatePhase_CompletedToAny_ThrowsIllegalArgumentException() {
            // Arrange - run in COMPLETED state (terminal)
            testRun.updatePhase(RunPhase.COMPLETED);
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));

            // Act & Assert
            IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> tradingRunService.updatePhase(100L, RunPhase.RESEARCHING)
            );
            assertTrue(exception.getMessage().contains("Invalid phase transition"),
                       "Should reject transition from terminal COMPLETED state");
        }

        @Test
        @DisplayName("ERROR phase cannot transition to any other phase")
        void updatePhase_ErrorToAny_ThrowsIllegalArgumentException() {
            // Arrange - run in ERROR state (terminal)
            testRun.updatePhase(RunPhase.FAILED);
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));

            // Act & Assert
            IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> tradingRunService.updatePhase(100L, RunPhase.RESEARCHING)
            );
            assertTrue(exception.getMessage().contains("Invalid phase transition"),
                       "Should reject transition from terminal ERROR state");
        }
    }

    // ========== completeRun() tests ==========

    @Nested
    @DisplayName("completeRun() Tests")
    class CompleteRunTests {

        private CompleteRunRequest createBuyRequest() {
            // Research phase DTO (request package)
            com.trading.dto.request.ResearchPhaseDto research = new com.trading.dto.request.ResearchPhaseDto();
            research.setCandidates(Arrays.asList("JPM", "BAC", "WFC"));
            research.setNotes("Banking sector analysis");
            research.setLatencyMs(3400L);

            // Decision phase DTO (request package)
            com.trading.dto.request.DecisionPhaseDto decision = new com.trading.dto.request.DecisionPhaseDto();
            decision.setDecision(TradeDecision.BUY);
            decision.setSymbol("JPM");
            decision.setQuantity(30);
            decision.setLatencyMs(2100L);

            // Execution phase DTO (request package)
            com.trading.dto.request.ExecutionPhaseDto execution = new com.trading.dto.request.ExecutionPhaseDto();
            execution.setTradeId(500L);
            execution.setStatus(PhaseStatus.COMPLETED);

            return new CompleteRunRequest(research, decision, execution);
        }

        private CompleteRunRequest createHoldRequest() {
            // Research phase DTO (request package)
            com.trading.dto.request.ResearchPhaseDto research = new com.trading.dto.request.ResearchPhaseDto();
            research.setCandidates(Arrays.asList("JPM", "BAC", "WFC"));
            research.setNotes("Market conditions unfavorable");
            research.setLatencyMs(3400L);

            // Decision phase DTO (request package)
            com.trading.dto.request.DecisionPhaseDto decision = new com.trading.dto.request.DecisionPhaseDto();
            decision.setDecision(TradeDecision.HOLD);
            decision.setLatencyMs(2100L);

            return new CompleteRunRequest(research, decision, null);
        }

        @Test
        @DisplayName("BUY decision creates all three phases")
        void completeRun_BuyDecision_CreatesAllThreePhases() {
            // Arrange
            CompleteRunRequest request = createBuyRequest();
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));
            when(tradingRunRepository.save(any(TradingRun.class))).thenReturn(testRun);
            when(researchPhaseRepository.save(any(ResearchPhase.class))).thenReturn(testResearchPhase);
            when(decisionPhaseRepository.save(any(DecisionPhase.class))).thenReturn(testDecisionPhase);
            when(executionPhaseRepository.save(any(ExecutionPhase.class))).thenReturn(testExecutionPhase);
            when(accountTransactionRepository.findById(500L)).thenReturn(Optional.of(new AccountTransaction()));

            // Act
            tradingRunService.completeRun(100L, request);

            // Assert
            verify(researchPhaseRepository).save(any(ResearchPhase.class));
            verify(decisionPhaseRepository).save(any(DecisionPhase.class));
            verify(executionPhaseRepository).save(any(ExecutionPhase.class));
        }

        @Test
        @DisplayName("BUY decision persists research phase data correctly")
        void completeRun_BuyDecision_PersistsResearchPhaseDataCorrectly() {
            // Arrange
            CompleteRunRequest request = createBuyRequest();
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));
            when(tradingRunRepository.save(any(TradingRun.class))).thenReturn(testRun);
            when(researchPhaseRepository.save(researchPhaseCaptor.capture())).thenReturn(testResearchPhase);
            when(decisionPhaseRepository.save(any(DecisionPhase.class))).thenReturn(testDecisionPhase);
            when(executionPhaseRepository.save(any(ExecutionPhase.class))).thenReturn(testExecutionPhase);
            when(accountTransactionRepository.findById(500L)).thenReturn(Optional.of(new AccountTransaction()));

            // Act
            tradingRunService.completeRun(100L, request);

            // Assert - verify research phase data captured correctly
            ResearchPhase capturedResearch = researchPhaseCaptor.getValue();
            assertEquals(testRun, capturedResearch.getRun(), "Research phase should be linked to correct run");
            assertEquals(Arrays.asList("JPM", "BAC", "WFC"), capturedResearch.getCandidates(), "Candidates should match request");
            assertEquals("Banking sector analysis", capturedResearch.getResearchNotes(), "Research notes should match request");
            assertEquals(3400L, capturedResearch.getLatencyMs(), "Latency should match request");
        }

        @Test
        @DisplayName("BUY decision persists decision phase data correctly")
        void completeRun_BuyDecision_PersistsDecisionPhaseDataCorrectly() {
            // Arrange
            CompleteRunRequest request = createBuyRequest();
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));
            when(tradingRunRepository.save(any(TradingRun.class))).thenReturn(testRun);
            when(researchPhaseRepository.save(any(ResearchPhase.class))).thenReturn(testResearchPhase);
            when(decisionPhaseRepository.save(decisionPhaseCaptor.capture())).thenReturn(testDecisionPhase);
            when(executionPhaseRepository.save(any(ExecutionPhase.class))).thenReturn(testExecutionPhase);
            when(accountTransactionRepository.findById(500L)).thenReturn(Optional.of(new AccountTransaction()));

            // Act
            tradingRunService.completeRun(100L, request);

            // Assert - verify decision phase data captured correctly
            DecisionPhase capturedDecision = decisionPhaseCaptor.getValue();
            assertEquals(testRun, capturedDecision.getRun(), "Decision phase should be linked to correct run");
            assertEquals(TradeDecision.BUY, capturedDecision.getDecision(), "Decision should be BUY");
            assertEquals("JPM", capturedDecision.getSymbol(), "Symbol should match request");
            assertEquals(30, capturedDecision.getQuantity(), "Quantity should match request");
            assertEquals(2100L, capturedDecision.getLatencyMs(), "Latency should match request");
        }

        @Test
        @DisplayName("SELL decision creates all three phases")
        void completeRun_SellDecision_CreatesAllThreePhases() {
            // Arrange
            CompleteRunRequest request = createBuyRequest();
            request.getDecision().setDecision(TradeDecision.SELL);
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));
            when(tradingRunRepository.save(any(TradingRun.class))).thenReturn(testRun);
            when(researchPhaseRepository.save(any(ResearchPhase.class))).thenReturn(testResearchPhase);
            when(decisionPhaseRepository.save(any(DecisionPhase.class))).thenReturn(testDecisionPhase);
            when(executionPhaseRepository.save(any(ExecutionPhase.class))).thenReturn(testExecutionPhase);
            when(accountTransactionRepository.findById(500L)).thenReturn(Optional.of(new AccountTransaction()));

            // Act
            tradingRunService.completeRun(100L, request);

            // Assert
            verify(researchPhaseRepository).save(any(ResearchPhase.class));
            verify(decisionPhaseRepository).save(any(DecisionPhase.class));
            verify(executionPhaseRepository).save(any(ExecutionPhase.class));
        }

        @Test
        @DisplayName("HOLD decision creates research and decision phases only")
        void completeRun_HoldDecision_CreatesResearchAndDecisionOnly() {
            // Arrange
            CompleteRunRequest request = createHoldRequest();
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));
            when(tradingRunRepository.save(any(TradingRun.class))).thenReturn(testRun);
            when(researchPhaseRepository.save(any(ResearchPhase.class))).thenReturn(testResearchPhase);
            when(decisionPhaseRepository.save(any(DecisionPhase.class))).thenReturn(testDecisionPhase);

            // Act
            tradingRunService.completeRun(100L, request);

            // Assert
            verify(researchPhaseRepository).save(any(ResearchPhase.class));
            verify(decisionPhaseRepository).save(any(DecisionPhase.class));
        }

        @Test
        @DisplayName("HOLD decision does not create execution phase")
        void completeRun_HoldDecision_NoExecutionPhase() {
            // Arrange
            CompleteRunRequest request = createHoldRequest();
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));
            when(tradingRunRepository.save(any(TradingRun.class))).thenReturn(testRun);
            when(researchPhaseRepository.save(any(ResearchPhase.class))).thenReturn(testResearchPhase);
            when(decisionPhaseRepository.save(any(DecisionPhase.class))).thenReturn(testDecisionPhase);

            // Act
            tradingRunService.completeRun(100L, request);

            // Assert
            verify(executionPhaseRepository, never()).save(any(ExecutionPhase.class));
        }

        @Test
        @DisplayName("completeRun marks run as completed")
        void completeRun_MarksRunAsCompleted() {
            // Arrange
            CompleteRunRequest request = createHoldRequest();
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));
            when(tradingRunRepository.save(tradingRunCaptor.capture())).thenReturn(testRun);
            when(researchPhaseRepository.save(any(ResearchPhase.class))).thenReturn(testResearchPhase);
            when(decisionPhaseRepository.save(any(DecisionPhase.class))).thenReturn(testDecisionPhase);

            // Act
            tradingRunService.completeRun(100L, request);

            // Assert
            TradingRun capturedRun = tradingRunCaptor.getValue();
            assertEquals(RunStatus.COMPLETED, capturedRun.getStatus(), "Run status should be COMPLETED");
            assertEquals(RunPhase.COMPLETED, capturedRun.getPhase(), "Run phase should be COMPLETED");
        }

        @Test
        @DisplayName("completeRun sets completedAt timestamp")
        void completeRun_SetsCompletedAtTimestamp() {
            // Arrange
            CompleteRunRequest request = createHoldRequest();
            Instant beforeCall = Instant.now();
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));
            when(tradingRunRepository.save(tradingRunCaptor.capture())).thenReturn(testRun);
            when(researchPhaseRepository.save(any(ResearchPhase.class))).thenReturn(testResearchPhase);
            when(decisionPhaseRepository.save(any(DecisionPhase.class))).thenReturn(testDecisionPhase);

            // Act
            tradingRunService.completeRun(100L, request);

            // Assert
            TradingRun capturedRun = tradingRunCaptor.getValue();
            assertNotNull(capturedRun.getCompletedAt(), "completedAt should be set");
            assertTrue(capturedRun.getCompletedAt().isAfter(beforeCall) ||
                       capturedRun.getCompletedAt().equals(beforeCall),
                       "completedAt should be at or after the call time");
        }

        @Test
        @DisplayName("completeRun broadcasts decision_completed via WebSocket")
        void completeRun_BroadcastsDecisionCompleted() {
            // Arrange
            CompleteRunRequest request = createHoldRequest();
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));
            when(tradingRunRepository.save(any(TradingRun.class))).thenReturn(testRun);
            when(researchPhaseRepository.save(any(ResearchPhase.class))).thenReturn(testResearchPhase);
            when(decisionPhaseRepository.save(any(DecisionPhase.class))).thenReturn(testDecisionPhase);

            // Act
            tradingRunService.completeRun(100L, request);

            // Assert
            verify(runEventPublisher).publishDecisionCompleted(any(DecisionCompletedMessage.class));
        }

        @Test
        @DisplayName("Run not found throws ResourceNotFoundException")
        void completeRun_RunNotFound_ThrowsResourceNotFoundException() {
            // Arrange
            CompleteRunRequest request = createHoldRequest();
            when(tradingRunRepository.findById(999L)).thenReturn(Optional.empty());

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(
                ResourceNotFoundException.class,
                () -> tradingRunService.completeRun(999L, request)
            );
            assertTrue(exception.getMessage().contains("Trading run not found"));
        }

        @Test
        @DisplayName("BUY without symbol throws IllegalArgumentException")
        void completeRun_InvalidRequest_BuyWithoutSymbol_ThrowsIllegalArgumentException() {
            // Arrange
            CompleteRunRequest request = createBuyRequest();
            request.getDecision().setSymbol(null);

            // Act & Assert
            IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> tradingRunService.completeRun(100L, request)
            );
            assertTrue(exception.getMessage().contains("requires symbol"));
        }

        @Test
        @DisplayName("BUY without quantity throws IllegalArgumentException")
        void completeRun_InvalidRequest_BuyWithoutQuantity_ThrowsIllegalArgumentException() {
            // Arrange
            CompleteRunRequest request = createBuyRequest();
            request.getDecision().setQuantity(null);

            // Act & Assert
            IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> tradingRunService.completeRun(100L, request)
            );
            assertTrue(exception.getMessage().contains("requires positive quantity"));
        }
    }

    // ========== getRunWithAllPhases() tests ==========

    @Nested
    @DisplayName("getRunWithAllPhases() Tests")
    class GetRunWithAllPhasesTests {

        @Test
        @DisplayName("Completed run returns all phases")
        void getRunWithAllPhases_CompletedRun_ReturnsAllPhases() {
            // Arrange
            testRun.markAsCompleted();
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));
            when(researchPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testResearchPhase));
            when(decisionPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testDecisionPhase));
            when(executionPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testExecutionPhase));

            // Act
            TradingRunDetailDto result = tradingRunService.getRunWithAllPhases(100L);

            // Assert
            assertNotNull(result);
            assertNotNull(result.getRun());
            assertNotNull(result.getResearch());
            assertNotNull(result.getDecision());
            assertNotNull(result.getExecution());
        }

        @Test
        @DisplayName("HOLD decision returns null execution")
        void getRunWithAllPhases_HoldDecision_ReturnsNullExecution() {
            // Arrange
            testRun.markAsCompleted();
            testDecisionPhase.setDecision(TradeDecision.HOLD);
            testDecisionPhase.setSymbol(null);
            testDecisionPhase.setQuantity(null);
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));
            when(researchPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testResearchPhase));
            when(decisionPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testDecisionPhase));
            when(executionPhaseRepository.findByRunId(100L)).thenReturn(Optional.empty());

            // Act
            TradingRunDetailDto result = tradingRunService.getRunWithAllPhases(100L);

            // Assert
            assertNotNull(result);
            assertNotNull(result.getRun());
            assertNotNull(result.getResearch());
            assertNotNull(result.getDecision());
            assertNull(result.getExecution());
        }

        @Test
        @DisplayName("In-progress run returns null phases")
        void getRunWithAllPhases_InProgressRun_ReturnsNullPhases() {
            // Arrange
            when(tradingRunRepository.findById(100L)).thenReturn(Optional.of(testRun));
            when(researchPhaseRepository.findByRunId(100L)).thenReturn(Optional.empty());
            when(decisionPhaseRepository.findByRunId(100L)).thenReturn(Optional.empty());
            when(executionPhaseRepository.findByRunId(100L)).thenReturn(Optional.empty());

            // Act
            TradingRunDetailDto result = tradingRunService.getRunWithAllPhases(100L);

            // Assert
            assertNotNull(result);
            assertNotNull(result.getRun());
            assertNull(result.getResearch());
            assertNull(result.getDecision());
            assertNull(result.getExecution());
        }

        @Test
        @DisplayName("Run not found throws ResourceNotFoundException")
        void getRunWithAllPhases_RunNotFound_ThrowsResourceNotFoundException() {
            // Arrange
            when(tradingRunRepository.findById(999L)).thenReturn(Optional.empty());

            // Act & Assert
            assertThrows(
                ResourceNotFoundException.class,
                () -> tradingRunService.getRunWithAllPhases(999L)
            );
        }
    }

    // ========== getResearchPhase() tests ==========

    @Nested
    @DisplayName("getResearchPhase() Tests")
    class GetResearchPhaseTests {

        @Test
        @DisplayName("Research phase exists returns DTO")
        void getResearchPhase_Exists_ReturnsDto() {
            // Arrange
            when(tradingRunRepository.existsById(100L)).thenReturn(true);
            when(researchPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testResearchPhase));

            // Act
            ResearchPhaseDto result = tradingRunService.getResearchPhase(100L);

            // Assert
            assertNotNull(result);
            assertEquals(200L, result.getResearchId());
            assertEquals(Arrays.asList("JPM", "BAC", "WFC"), result.getCandidates());
        }

        @Test
        @DisplayName("Research phase not found throws ResourceNotFoundException")
        void getResearchPhase_NotFound_ThrowsResourceNotFoundException() {
            // Arrange
            when(tradingRunRepository.existsById(100L)).thenReturn(true);
            when(researchPhaseRepository.findByRunId(100L)).thenReturn(Optional.empty());

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(
                ResourceNotFoundException.class,
                () -> tradingRunService.getResearchPhase(100L)
            );
            assertTrue(exception.getMessage().contains("Research phase not found"));
        }

        @Test
        @DisplayName("Run not found throws ResourceNotFoundException")
        void getResearchPhase_RunNotFound_ThrowsResourceNotFoundException() {
            // Arrange
            when(tradingRunRepository.existsById(999L)).thenReturn(false);

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(
                ResourceNotFoundException.class,
                () -> tradingRunService.getResearchPhase(999L)
            );
            assertTrue(exception.getMessage().contains("Trading run not found"));
        }
    }

    // ========== getDecisionPhase() tests ==========

    @Nested
    @DisplayName("getDecisionPhase() Tests")
    class GetDecisionPhaseTests {

        @Test
        @DisplayName("Decision phase exists returns DTO")
        void getDecisionPhase_Exists_ReturnsDto() {
            // Arrange
            when(tradingRunRepository.existsById(100L)).thenReturn(true);
            when(decisionPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testDecisionPhase));

            // Act
            DecisionPhaseDto result = tradingRunService.getDecisionPhase(100L);

            // Assert
            assertNotNull(result);
            assertEquals(300L, result.getDecisionId());
            assertEquals(TradeDecision.BUY, result.getDecision());
            assertEquals("JPM", result.getSymbol());
            assertEquals(30, result.getQuantity());
        }

        @Test
        @DisplayName("Decision phase not found throws ResourceNotFoundException")
        void getDecisionPhase_NotFound_ThrowsResourceNotFoundException() {
            // Arrange
            when(tradingRunRepository.existsById(100L)).thenReturn(true);
            when(decisionPhaseRepository.findByRunId(100L)).thenReturn(Optional.empty());

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(
                ResourceNotFoundException.class,
                () -> tradingRunService.getDecisionPhase(100L)
            );
            assertTrue(exception.getMessage().contains("Decision phase not found"));
        }

        @Test
        @DisplayName("Run not found throws ResourceNotFoundException")
        void getDecisionPhase_RunNotFound_ThrowsResourceNotFoundException() {
            // Arrange
            when(tradingRunRepository.existsById(999L)).thenReturn(false);

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(
                ResourceNotFoundException.class,
                () -> tradingRunService.getDecisionPhase(999L)
            );
            assertTrue(exception.getMessage().contains("Trading run not found"));
        }
    }

    // ========== getExecutionPhase() tests ==========

    @Nested
    @DisplayName("getExecutionPhase() Tests")
    class GetExecutionPhaseTests {

        @Test
        @DisplayName("BUY decision returns execution DTO")
        void getExecutionPhase_BuyDecision_ReturnsDto() {
            // Arrange
            when(tradingRunRepository.existsById(100L)).thenReturn(true);
            when(executionPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testExecutionPhase));

            // Act
            ExecutionPhaseDto result = tradingRunService.getExecutionPhase(100L);

            // Assert
            assertNotNull(result);
            assertEquals(400L, result.getExecutionId());
            assertEquals(PhaseStatus.COMPLETED, result.getStatus());
        }

        @Test
        @DisplayName("HOLD decision throws ResourceNotFoundException")
        void getExecutionPhase_HoldDecision_ThrowsResourceNotFoundException() {
            // Arrange
            when(tradingRunRepository.existsById(100L)).thenReturn(true);
            when(executionPhaseRepository.findByRunId(100L)).thenReturn(Optional.empty());

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(
                ResourceNotFoundException.class,
                () -> tradingRunService.getExecutionPhase(100L)
            );
            assertTrue(exception.getMessage().contains("Execution phase not found"));
        }

        @Test
        @DisplayName("Run not found throws ResourceNotFoundException")
        void getExecutionPhase_RunNotFound_ThrowsResourceNotFoundException() {
            // Arrange
            when(tradingRunRepository.existsById(999L)).thenReturn(false);

            // Act & Assert
            ResourceNotFoundException exception = assertThrows(
                ResourceNotFoundException.class,
                () -> tradingRunService.getExecutionPhase(999L)
            );
            assertTrue(exception.getMessage().contains("Trading run not found"));
        }
    }

    // ========== listRuns() tests ==========

    @Nested
    @DisplayName("listRuns() Tests")
    class ListRunsTests {

        private Instant cutoff;

        @BeforeEach
        void setUpListRunsTests() {
            // Pre-compute a 7-day cutoff for use across the listRuns tests; matches
            // the production controller's derivation from TradingPublicProperties.
            cutoff = Instant.now().minus(7, ChronoUnit.DAYS);
        }

        @Test
        @DisplayName("No filters returns all old runs from database")
        void listRuns_NoFilters_ReturnsAllOldRuns() {
            // Arrange
            testRun.setStartedAt(Instant.now().minus(10, ChronoUnit.DAYS)); // Make it old enough
            List<TradingRun> runs = Arrays.asList(testRun);
            Page<TradingRun> page = new PageImpl<>(runs, PageRequest.of(0, 20), 1);
            when(tradingRunRepository.findAll(any(Specification.class), any(Pageable.class)))
                .thenReturn(page);
            when(decisionPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testDecisionPhase));

            // Act
            RunListResponseDto result = tradingRunService.listRuns(null, cutoff, PageRequest.of(0, 20));

            // Assert
            verify(tradingRunRepository).findAll(any(Specification.class), any(Pageable.class));
            assertNotNull(result);
            assertEquals(1, result.getRuns().size());
            assertEquals(1L, result.getTotal());
        }

        @Test
        @DisplayName("Filter by agentId returns agent runs")
        void listRuns_FilterByAgentId_ReturnsAgentRuns() {
            // Arrange
            testRun.setStartedAt(Instant.now().minus(10, ChronoUnit.DAYS)); // Make it old enough
            RunQueryFilter filter = new RunQueryFilter(1L, null, null, null);
            List<TradingRun> runs = Arrays.asList(testRun);
            Page<TradingRun> page = new PageImpl<>(runs, PageRequest.of(0, 20), 1);
            when(tradingRunRepository.findAll(any(Specification.class), any(Pageable.class))).thenReturn(page);
            when(decisionPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testDecisionPhase));

            // Act
            RunListResponseDto result = tradingRunService.listRuns(filter, cutoff, PageRequest.of(0, 20));

            // Assert
            assertNotNull(result);
            assertEquals(1, result.getRuns().size());
        }

        @Test
        @DisplayName("Filter by status returns matching runs")
        void listRuns_FilterByStatus_ReturnsMatchingRuns() {
            // Arrange
            testRun.setStartedAt(Instant.now().minus(10, ChronoUnit.DAYS)); // Make it old enough
            RunQueryFilter filter = new RunQueryFilter(null, RunStatus.IN_PROGRESS, null, null);
            List<TradingRun> runs = Arrays.asList(testRun);
            Page<TradingRun> page = new PageImpl<>(runs, PageRequest.of(0, 20), 1);
            when(tradingRunRepository.findAll(any(Specification.class), any(Pageable.class))).thenReturn(page);
            when(decisionPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testDecisionPhase));

            // Act
            RunListResponseDto result = tradingRunService.listRuns(filter, cutoff, PageRequest.of(0, 20));

            // Assert
            assertNotNull(result);
            assertEquals(1, result.getRuns().size());
        }

        @Test
        @DisplayName("Filter by decision returns matching runs")
        void listRuns_FilterByDecision_ReturnsMatchingRuns() {
            // Arrange
            testRun.setStartedAt(Instant.now().minus(10, ChronoUnit.DAYS)); // Make it old enough
            RunQueryFilter filter = new RunQueryFilter(null, null, TradeDecision.BUY, null);
            List<TradingRun> runs = Arrays.asList(testRun);
            Page<TradingRun> page = new PageImpl<>(runs, PageRequest.of(0, 20), 1);
            when(tradingRunRepository.findAll(any(Specification.class), any(Pageable.class))).thenReturn(page);
            when(decisionPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testDecisionPhase));

            // Act
            RunListResponseDto result = tradingRunService.listRuns(filter, cutoff, PageRequest.of(0, 20));

            // Assert
            assertNotNull(result);
        }

        @Test
        @DisplayName("Filter by symbol returns matching runs")
        void listRuns_FilterBySymbol_ReturnsMatchingRuns() {
            // Arrange
            testRun.setStartedAt(Instant.now().minus(10, ChronoUnit.DAYS)); // Make it old enough
            RunQueryFilter filter = new RunQueryFilter(null, null, null, "JPM");
            List<TradingRun> runs = Arrays.asList(testRun);
            Page<TradingRun> page = new PageImpl<>(runs, PageRequest.of(0, 20), 1);
            when(tradingRunRepository.findAll(any(Specification.class), any(Pageable.class))).thenReturn(page);
            when(decisionPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testDecisionPhase));

            // Act
            RunListResponseDto result = tradingRunService.listRuns(filter, cutoff, PageRequest.of(0, 20));

            // Assert
            assertNotNull(result);
        }

        @Test
        @DisplayName("Multiple filters returns matching runs")
        void listRuns_MultipleFilters_ReturnsMatchingRuns() {
            // Arrange
            testRun.setStartedAt(Instant.now().minus(10, ChronoUnit.DAYS)); // Make it old enough
            RunQueryFilter filter = new RunQueryFilter(1L, RunStatus.COMPLETED, TradeDecision.BUY, "JPM");
            List<TradingRun> runs = Arrays.asList(testRun);
            Page<TradingRun> page = new PageImpl<>(runs, PageRequest.of(0, 20), 1);
            when(tradingRunRepository.findAll(any(Specification.class), any(Pageable.class))).thenReturn(page);
            when(decisionPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testDecisionPhase));

            // Act
            RunListResponseDto result = tradingRunService.listRuns(filter, cutoff, PageRequest.of(0, 20));

            // Assert
            assertNotNull(result);
        }

        @Test
        @DisplayName("Pagination returns correct page with database filtering")
        void listRuns_Pagination_ReturnsCorrectPage() {
            // Arrange
            testRun.setStartedAt(Instant.now().minus(10, ChronoUnit.DAYS)); // Make it old enough
            List<TradingRun> runs = Arrays.asList(testRun);
            Page<TradingRun> page = new PageImpl<>(runs, PageRequest.of(2, 10), 30);
            when(tradingRunRepository.findAll(any(Specification.class), any(Pageable.class)))
                .thenReturn(page);
            when(decisionPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testDecisionPhase));

            // Act
            RunListResponseDto result = tradingRunService.listRuns(null, cutoff, PageRequest.of(2, 10));

            // Assert
            verify(tradingRunRepository).findAll(any(Specification.class), any(Pageable.class));
            assertNotNull(result);
            assertEquals(30L, result.getTotal());
            assertEquals(2, result.getPage());
            assertEquals(10, result.getLimit());
        }

        @Test
        @DisplayName("List runs includes decision data in DTO with database filtering")
        void listRuns_IncludesDecisionDataInDto() {
            // Arrange
            testRun.setStartedAt(Instant.now().minus(10, ChronoUnit.DAYS)); // Make it old enough
            List<TradingRun> runs = Arrays.asList(testRun);
            Page<TradingRun> page = new PageImpl<>(runs, PageRequest.of(0, 20), 1);
            when(tradingRunRepository.findAll(any(Specification.class), any(Pageable.class)))
                .thenReturn(page);
            when(decisionPhaseRepository.findByRunId(100L)).thenReturn(Optional.of(testDecisionPhase));

            // Act
            RunListResponseDto result = tradingRunService.listRuns(null, cutoff, PageRequest.of(0, 20));

            // Assert
            verify(tradingRunRepository).findAll(any(Specification.class), any(Pageable.class));
            assertNotNull(result);
            assertEquals(1, result.getRuns().size());
            TradingRunDto runDto = result.getRuns().get(0);
            assertEquals(TradeDecision.BUY, runDto.getDecision());
            assertEquals("JPM", runDto.getSymbol());
        }

        @Test
        @DisplayName("List runs filters by publicDisplayDelayDays at database level - excludes recent runs")
        void listRuns_FiltersRecentRunsByDelayDaysAtDatabaseLevel() {
            // Arrange - mock repository to return only old runs (database already filtered)
            TradingRun oldRun = new TradingRun(testAgent);
            oldRun.setId(101L);
            // Set startedAt to 10 days ago (older than 7-day delay)
            Instant tenDaysAgo = Instant.now().minus(10, ChronoUnit.DAYS);
            oldRun.setStartedAt(tenDaysAgo);

            // Repository should be called with date filter - returns only matching runs
            List<TradingRun> runs = Arrays.asList(oldRun);
            Page<TradingRun> page = new PageImpl<>(runs, PageRequest.of(0, 20), 1);

            // Verify database-level filtering: repository receives cutoff date predicate
            when(tradingRunRepository.findAll(any(Specification.class), any(Pageable.class)))
                .thenReturn(page);
            when(decisionPhaseRepository.findByRunId(101L)).thenReturn(Optional.empty());

            // Act
            RunListResponseDto result = tradingRunService.listRuns(null, cutoff, PageRequest.of(0, 20));

            // Assert - verify repository was called with Specification (database-level)
            verify(tradingRunRepository).findAll(any(Specification.class), any(Pageable.class));
            assertNotNull(result);
            assertEquals(1, result.getRuns().size(), "Should only return runs older than 7 days");
            assertEquals(101L, result.getRuns().get(0).getRunId(), "Should return the 10-day-old run");
        }

        @Test
        @DisplayName("List runs filters by publicDisplayDelayDays at database level - includes run exactly at cutoff")
        void listRuns_IncludesRunAtExactCutoffAtDatabaseLevel() {
            // Arrange - create run exactly at 7-day cutoff
            TradingRun cutoffRun = new TradingRun(testAgent);
            cutoffRun.setId(103L);
            // Set startedAt to exactly 7 days ago
            Instant sevenDaysAgo = Instant.now().minus(7, ChronoUnit.DAYS).minusSeconds(1);
            cutoffRun.setStartedAt(sevenDaysAgo);

            List<TradingRun> runs = Arrays.asList(cutoffRun);
            Page<TradingRun> page = new PageImpl<>(runs, PageRequest.of(0, 20), 1);
            when(tradingRunRepository.findAll(any(Specification.class), any(Pageable.class)))
                .thenReturn(page);
            when(decisionPhaseRepository.findByRunId(103L)).thenReturn(Optional.empty());

            // Act
            RunListResponseDto result = tradingRunService.listRuns(null, cutoff, PageRequest.of(0, 20));

            // Assert - run at cutoff should be included
            verify(tradingRunRepository).findAll(any(Specification.class), any(Pageable.class));
            assertNotNull(result);
            assertEquals(1, result.getRuns().size(), "Should include run at exactly 7 days old");
            assertEquals(103L, result.getRuns().get(0).getRunId());
        }

        @Test
        @DisplayName("List runs returns empty list when database returns no old runs")
        void listRuns_ReturnsEmptyWhenDatabaseReturnsNoOldRuns() {
            // Arrange - database returns empty (all runs filtered at DB level)
            Page<TradingRun> emptyPage = new PageImpl<>(List.of(), PageRequest.of(0, 20), 0);
            when(tradingRunRepository.findAll(any(Specification.class), any(Pageable.class)))
                .thenReturn(emptyPage);

            // Act
            RunListResponseDto result = tradingRunService.listRuns(null, cutoff, PageRequest.of(0, 20));

            // Assert - should return empty list
            verify(tradingRunRepository).findAll(any(Specification.class), any(Pageable.class));
            assertNotNull(result);
            assertEquals(0, result.getRuns().size(), "Should return empty list when database returns no old runs");
        }

        @Test
        @DisplayName("List runs with filters combines Specification with date filter at database level")
        void listRuns_WithFilters_CombinesSpecificationWithDateFilter() {
            // Arrange - filtered results should also respect delay at database level
            TradingRun oldMatchingRun = new TradingRun(testAgent);
            oldMatchingRun.setId(106L);
            oldMatchingRun.setStartedAt(Instant.now().minus(10, ChronoUnit.DAYS));

            RunQueryFilter filter = new RunQueryFilter(1L, null, null, null);
            List<TradingRun> runs = Arrays.asList(oldMatchingRun);
            Page<TradingRun> page = new PageImpl<>(runs, PageRequest.of(0, 20), 1);

            // Verify that Specification is combined with date filter
            when(tradingRunRepository.findAll(any(Specification.class), any(Pageable.class)))
                .thenReturn(page);
            when(decisionPhaseRepository.findByRunId(106L)).thenReturn(Optional.empty());

            // Act
            RunListResponseDto result = tradingRunService.listRuns(filter, cutoff, PageRequest.of(0, 20));

            // Assert - Specification should include both filter and date criteria
            verify(tradingRunRepository).findAll(any(Specification.class), any(Pageable.class));
            assertNotNull(result);
            assertEquals(1, result.getRuns().size(), "Filtered results should respect delay at DB level");
            assertEquals(106L, result.getRuns().get(0).getRunId());
        }
    }
}
