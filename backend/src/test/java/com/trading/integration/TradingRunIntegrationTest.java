package com.trading.integration;

import com.trading.dto.request.CompleteRunRequest;
import com.trading.dto.request.RunQueryFilter;
import com.trading.dto.response.TradingRunDetailDto;
import com.trading.dto.response.TradingRunDto;
import com.trading.entity.TradingAgent;
import com.trading.entity.TradingRun;
import com.trading.enums.PhaseStatus;
import com.trading.enums.RunPhase;
import com.trading.enums.RunStatus;
import com.trading.enums.TradeDecision;
import com.trading.exception.ResourceNotFoundException;
import com.trading.repository.*;
import com.trading.service.TradingRunService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.context.annotation.Import;
import org.springframework.data.domain.PageRequest;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;

import java.util.Arrays;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;

/**
 * Integration tests for Trading Runs API.
 * Uses @DataJpaTest with real PostgreSQL via Testcontainers.
 * Tests complete end-to-end workflows through service layer with real database.
 *
 * Note: Uses @DataJpaTest to avoid web layer and controller mapping conflicts.
 * Manually configures TradingRunService with mocked SimpMessagingTemplate.
 */
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@DisplayName("TradingRun Integration Tests")
class TradingRunIntegrationTest {

    // Singleton container - shared across all tests for performance
    private static final PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15-alpine")
            .withDatabaseName("test_trading")
            .withUsername("test")
            .withPassword("test")
            .withReuse(true);

    static {
        postgres.start();
    }

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
        registry.add("spring.jpa.hibernate.ddl-auto", () -> "create-drop");
        registry.add("spring.jpa.properties.hibernate.hbm2ddl.create_namespaces", () -> "true");
    }

    @Autowired
    private TradingAgentRepository tradingAgentRepository;

    @Autowired
    private TradingRunRepository tradingRunRepository;

    @Autowired
    private ResearchPhaseRepository researchPhaseRepository;

    @Autowired
    private DecisionPhaseRepository decisionPhaseRepository;

    @Autowired
    private ExecutionPhaseRepository executionPhaseRepository;

    @Autowired
    private AccountTransactionRepository accountTransactionRepository;

    // Service under test - manually instantiated with mocked WebSocket
    private TradingRunService tradingRunService;
    private SimpMessagingTemplate mockMessagingTemplate;

    private TradingAgent testAgent;

    @BeforeEach
    void setUp() {
        // Clean up in proper order (phases reference runs, runs reference agents)
        executionPhaseRepository.deleteAll();
        decisionPhaseRepository.deleteAll();
        researchPhaseRepository.deleteAll();
        tradingRunRepository.deleteAll();
        tradingAgentRepository.deleteAll();

        // Create mock messaging template (we don't test WebSocket here)
        mockMessagingTemplate = mock(SimpMessagingTemplate.class);

        // Manually create service with repositories and mock messaging
        tradingRunService = new TradingRunService(
            tradingRunRepository,
            researchPhaseRepository,
            decisionPhaseRepository,
            executionPhaseRepository,
            tradingAgentRepository,
            accountTransactionRepository,
            mockMessagingTemplate
        );

        // Create test agent
        testAgent = new TradingAgent("IntegrationTestAgent", "Agent for integration testing");
        testAgent.setInitialCapital(100000.0);
        testAgent = tradingAgentRepository.save(testAgent);
    }

    // ========== 6.1 Full Workflow Test ==========

    @Test
    @DisplayName("6.1 Full workflow: createRun → updatePhase → completeRun → getRunWithAllPhases")
    void testFullWorkflow() {
        // Step 1: Create run
        TradingRunDto runDto = tradingRunService.createRun(testAgent.getId());
        Long runId = runDto.getRunId();

        // Verify initial state
        assertThat(runDto.getStatus()).isEqualTo(RunStatus.IN_PROGRESS);
        assertThat(runDto.getPhase()).isEqualTo(RunPhase.INITIALIZING);

        // Step 2: Progress through phases
        tradingRunService.updatePhase(runId, RunPhase.RESEARCHING);
        tradingRunService.updatePhase(runId, RunPhase.DECIDING);
        tradingRunService.updatePhase(runId, RunPhase.TRADING);

        // Step 3: Complete with BUY decision
        CompleteRunRequest completeRequest = buildBuyCompleteRequest();
        tradingRunService.completeRun(runId, completeRequest);

        // Step 4: Verify complete run with all phases
        TradingRunDetailDto detailDto = tradingRunService.getRunWithAllPhases(runId);

        assertThat(detailDto.getRun().getStatus()).isEqualTo(RunStatus.COMPLETED);
        assertThat(detailDto.getRun().getPhase()).isEqualTo(RunPhase.COMPLETED);
        assertThat(detailDto.getRun().getCompletedAt()).isNotNull();

        // Verify research phase
        assertThat(detailDto.getResearch()).isNotNull();
        assertThat(detailDto.getResearch().getCandidates()).hasSize(3);

        // Verify decision phase
        assertThat(detailDto.getDecision()).isNotNull();
        assertThat(detailDto.getDecision().getDecision()).isEqualTo(TradeDecision.BUY);
        assertThat(detailDto.getDecision().getSymbol()).isEqualTo("AAPL");
        assertThat(detailDto.getDecision().getQuantity()).isEqualTo(10);

        // Verify execution phase exists for BUY
        assertThat(detailDto.getExecution()).isNotNull();

        // Verify database state
        TradingRun savedRun = tradingRunRepository.findById(runId).orElseThrow();
        assertThat(savedRun.getStatus()).isEqualTo(RunStatus.COMPLETED);
        assertThat(savedRun.getPhase()).isEqualTo(RunPhase.COMPLETED);
    }

    // ========== 6.2 HOLD Decision Test ==========

    @Test
    @DisplayName("6.2 HOLD decision: No execution phase created")
    void testHoldDecision() {
        // Create and progress run to DECIDING phase
        Long runId = createAndProgressRun(RunPhase.DECIDING);

        // Complete with HOLD decision
        CompleteRunRequest holdRequest = buildHoldCompleteRequest();
        tradingRunService.completeRun(runId, holdRequest);

        // Verify run details
        TradingRunDetailDto detailDto = tradingRunService.getRunWithAllPhases(runId);

        assertThat(detailDto.getRun().getStatus()).isEqualTo(RunStatus.COMPLETED);
        assertThat(detailDto.getDecision().getDecision()).isEqualTo(TradeDecision.HOLD);

        // Verify NO execution phase for HOLD
        assertThat(detailDto.getExecution()).isNull();

        // Verify getExecutionPhase throws ResourceNotFoundException
        assertThatThrownBy(() -> tradingRunService.getExecutionPhase(runId))
            .isInstanceOf(ResourceNotFoundException.class)
            .hasMessageContaining("Execution phase not found");

        // Verify database: no ExecutionPhase record
        assertThat(executionPhaseRepository.findByRunId(runId)).isEmpty();
    }

    // ========== 6.3 BUY Decision Test ==========

    @Test
    @DisplayName("6.3 BUY decision: Execution phase created")
    void testBuyDecision() {
        // Create and progress run to TRADING phase
        Long runId = createAndProgressRun(RunPhase.TRADING);

        // Complete with BUY decision
        CompleteRunRequest buyRequest = buildBuyCompleteRequest();
        tradingRunService.completeRun(runId, buyRequest);

        // Verify run details
        TradingRunDetailDto detailDto = tradingRunService.getRunWithAllPhases(runId);

        assertThat(detailDto.getRun().getStatus()).isEqualTo(RunStatus.COMPLETED);
        assertThat(detailDto.getDecision().getDecision()).isEqualTo(TradeDecision.BUY);
        assertThat(detailDto.getDecision().getSymbol()).isEqualTo("AAPL");

        // Verify execution phase EXISTS for BUY
        assertThat(detailDto.getExecution()).isNotNull();
        assertThat(detailDto.getExecution().getStatus()).isEqualTo(PhaseStatus.COMPLETED);

        // Verify getExecutionPhase returns data
        var executionDto = tradingRunService.getExecutionPhase(runId);
        assertThat(executionDto).isNotNull();
        assertThat(executionDto.getStatus()).isEqualTo(PhaseStatus.COMPLETED);

        // Verify database: ExecutionPhase record exists
        assertThat(executionPhaseRepository.findByRunId(runId)).isPresent();
    }

    // ========== 6.4 Joined Queries Test ==========

    @Test
    @DisplayName("6.4 Joined queries: Filter by decision and symbol")
    void testJoinedQueries() {
        // Create multiple runs with different decisions
        Long buyRunId = createAndProgressRun(RunPhase.TRADING);
        completeRunWithDecision(buyRunId, TradeDecision.BUY, "AAPL", 10);

        Long sellRunId = createAndProgressRun(RunPhase.TRADING);
        completeRunWithDecision(sellRunId, TradeDecision.SELL, "GOOGL", 5);

        Long holdRunId = createAndProgressRun(RunPhase.DECIDING);
        completeRunWithDecision(holdRunId, TradeDecision.HOLD, null, null);

        var pageable = PageRequest.of(0, 20);

        // Filter by decision=BUY
        var buyFilter = new RunQueryFilter(null, null, TradeDecision.BUY, null);
        var buyResult = tradingRunService.listRuns(buyFilter, pageable);
        assertThat(buyResult.getTotal()).isEqualTo(1);
        assertThat(buyResult.getRuns().get(0).getDecision()).isEqualTo(TradeDecision.BUY);
        assertThat(buyResult.getRuns().get(0).getSymbol()).isEqualTo("AAPL");

        // Filter by decision=SELL
        var sellFilter = new RunQueryFilter(null, null, TradeDecision.SELL, null);
        var sellResult = tradingRunService.listRuns(sellFilter, pageable);
        assertThat(sellResult.getTotal()).isEqualTo(1);
        assertThat(sellResult.getRuns().get(0).getDecision()).isEqualTo(TradeDecision.SELL);
        assertThat(sellResult.getRuns().get(0).getSymbol()).isEqualTo("GOOGL");

        // Filter by symbol=AAPL
        var symbolFilter = new RunQueryFilter(null, null, null, "AAPL");
        var symbolResult = tradingRunService.listRuns(symbolFilter, pageable);
        assertThat(symbolResult.getTotal()).isEqualTo(1);
        assertThat(symbolResult.getRuns().get(0).getSymbol()).isEqualTo("AAPL");

        // Filter by decision=HOLD
        var holdFilter = new RunQueryFilter(null, null, TradeDecision.HOLD, null);
        var holdResult = tradingRunService.listRuns(holdFilter, pageable);
        assertThat(holdResult.getTotal()).isEqualTo(1);
        assertThat(holdResult.getRuns().get(0).getDecision()).isEqualTo(TradeDecision.HOLD);

        // Verify all runs returned without filter
        var allResult = tradingRunService.listRuns(null, pageable);
        assertThat(allResult.getTotal()).isEqualTo(3);
    }

    // ========== Helper Methods ==========

    private Long createAndProgressRun(RunPhase targetPhase) {
        // Create run
        TradingRunDto runDto = tradingRunService.createRun(testAgent.getId());
        Long runId = runDto.getRunId();

        // Progress through phases up to target
        RunPhase[] phases = {RunPhase.RESEARCHING, RunPhase.DECIDING, RunPhase.TRADING};
        for (RunPhase phase : phases) {
            if (phase.ordinal() <= targetPhase.ordinal() && phase != RunPhase.COMPLETED) {
                tradingRunService.updatePhase(runId, phase);
            }
            if (phase == targetPhase) break;
        }

        return runId;
    }

    private void completeRunWithDecision(Long runId, TradeDecision decision, String symbol, Integer quantity) {
        CompleteRunRequest request = new CompleteRunRequest();
        request.setCandidates(Arrays.asList("AAPL", "GOOGL", "MSFT"));
        request.setResearchNotes("Research notes for test");
        request.setResearchLatencyMs(1000L);
        request.setDecision(decision);
        request.setSymbol(symbol);
        request.setQuantity(quantity);
        request.setDecisionLatencyMs(500L);

        if (decision != TradeDecision.HOLD) {
            request.setExecutionStatus(PhaseStatus.COMPLETED);
        }

        tradingRunService.completeRun(runId, request);
    }

    private CompleteRunRequest buildBuyCompleteRequest() {
        CompleteRunRequest request = new CompleteRunRequest();
        request.setCandidates(Arrays.asList("AAPL", "GOOGL", "MSFT"));
        request.setResearchNotes("Tech sector analysis - strong fundamentals");
        request.setResearchLatencyMs(3400L);
        request.setDecision(TradeDecision.BUY);
        request.setSymbol("AAPL");
        request.setQuantity(10);
        request.setDecisionLatencyMs(1200L);
        request.setExecutionStatus(PhaseStatus.COMPLETED);
        return request;
    }

    private CompleteRunRequest buildHoldCompleteRequest() {
        CompleteRunRequest request = new CompleteRunRequest();
        request.setCandidates(Arrays.asList("AAPL", "GOOGL", "MSFT"));
        request.setResearchNotes("Market conditions uncertain - holding");
        request.setResearchLatencyMs(2800L);
        request.setDecision(TradeDecision.HOLD);
        request.setDecisionLatencyMs(800L);
        return request;
    }
}
