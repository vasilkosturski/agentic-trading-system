package com.trading.service;

import com.trading.dto.response.DecisionPhaseDto;
import com.trading.dto.response.ExecutionPhaseDto;
import com.trading.dto.response.ResearchPhaseDto;
import com.trading.dto.response.TradingRunDetailDto;
import com.trading.dto.response.TradingRunDto;
import com.trading.entity.AccountTransaction;
import com.trading.entity.DecisionPhase;
import com.trading.entity.ExecutionPhase;
import com.trading.entity.ResearchPhase;
import com.trading.entity.TradingAgent;
import com.trading.entity.TradingRun;
import com.trading.entity.TransactionType;
import com.trading.enums.PhaseStatus;
import com.trading.enums.RunPhase;
import com.trading.enums.RunStatus;
import com.trading.enums.TradeDecision;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.Arrays;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

/**
 * Unit tests for RunDtoMapper.
 * Pins byte-for-byte equality of assembled DTOs against the static
 * {@code fromEntity*} factories that lived inline in TradingRunService.
 *
 * Plain Mockito-free: the mapper is a pure component with no collaborators.
 */
@DisplayName("RunDtoMapper Tests")
class RunDtoMapperTest {

    private RunDtoMapper mapper;

    private TradingAgent agent;
    private TradingRun run;
    private ResearchPhase researchPhase;
    private DecisionPhase decisionPhase;
    private ExecutionPhase executionPhase;
    private AccountTransaction trade;

    @BeforeEach
    void setUp() {
        mapper = new RunDtoMapper();

        agent = new TradingAgent("Warren", "Value investor agent");
        agent.setId(1L);

        run = new TradingRun(agent);
        run.setId(100L);
        run.setStatus(RunStatus.COMPLETED);
        run.setPhase(RunPhase.COMPLETED);
        run.setStartedAt(Instant.parse("2026-01-01T10:00:00Z"));
        run.setCompletedAt(Instant.parse("2026-01-01T10:05:00Z"));
        run.setErrorMessage(null);

        researchPhase = new ResearchPhase(run);
        researchPhase.setId(200L);
        researchPhase.setCandidates(Arrays.asList("JPM", "BAC", "WFC"));
        researchPhase.setResearchNotes("Banking sector analysis");
        researchPhase.setLatencyMs(3400L);
        researchPhase.setSystemPrompt("research-system");
        researchPhase.setTaskPrompt("research-task");
        researchPhase.setCreatedAt(Instant.parse("2026-01-01T10:01:00Z"));

        decisionPhase = new DecisionPhase(run);
        decisionPhase.setId(300L);
        decisionPhase.setDecision(TradeDecision.BUY);
        decisionPhase.setSymbol("JPM");
        decisionPhase.setQuantity(30);
        decisionPhase.setLatencyMs(2100L);
        decisionPhase.setSystemPrompt("decision-system");
        decisionPhase.setTaskPrompt("decision-task");
        decisionPhase.setCreatedAt(Instant.parse("2026-01-01T10:02:00Z"));

        trade = new AccountTransaction();
        trade.setId(500L);
        trade.setSymbol("JPM");
        trade.setTransactionType(TransactionType.BUY);
        trade.setQuantity(30);
        trade.setPrice(150.0);
        trade.setTotalAmount(4500.0);

        executionPhase = new ExecutionPhase();
        executionPhase.setId(400L);
        executionPhase.setRun(run);
        executionPhase.setDecision(decisionPhase);
        executionPhase.setStatus(PhaseStatus.COMPLETED);
        executionPhase.setTrade(trade);
        executionPhase.setCreatedAt(Instant.parse("2026-01-01T10:03:00Z"));
    }

    @Nested
    @DisplayName("assembleDetail() Tests")
    class AssembleDetailTests {

        @Test
        @DisplayName("All three phases present produces fully populated DTO matching fromEntity factories")
        void assembleDetail_AllPhasesPresent_FullyPopulated() {
            TradingRunDetailDto result = mapper.assembleDetail(
                run,
                Optional.of(researchPhase),
                Optional.of(decisionPhase),
                Optional.of(executionPhase)
            );

            assertNotNull(result);

            // Run sub-DTO — must use fromEntityWithDecision because decision is present
            TradingRunDto runDto = result.getRun();
            assertNotNull(runDto);
            assertEquals(100L, runDto.getRunId());
            assertEquals(1L, runDto.getAgentId());
            assertEquals(RunStatus.COMPLETED, runDto.getStatus());
            assertEquals(RunPhase.COMPLETED, runDto.getPhase());
            assertEquals(TradeDecision.BUY, runDto.getDecision());
            assertEquals("JPM", runDto.getSymbol());
            assertEquals(Instant.parse("2026-01-01T10:00:00Z"), runDto.getStartedAt());
            assertEquals(Instant.parse("2026-01-01T10:05:00Z"), runDto.getCompletedAt());
            assertNull(runDto.getErrorMessage());

            // Research sub-DTO
            ResearchPhaseDto researchDto = result.getResearch();
            assertNotNull(researchDto);
            assertEquals(200L, researchDto.getResearchId());
            assertEquals(100L, researchDto.getRunId());
            assertEquals(Arrays.asList("JPM", "BAC", "WFC"), researchDto.getCandidates());
            assertEquals("Banking sector analysis", researchDto.getResearchNotes());
            assertEquals(3400L, researchDto.getLatencyMs());
            assertEquals("research-system", researchDto.getSystemPrompt());
            assertEquals("research-task", researchDto.getTaskPrompt());

            // Decision sub-DTO
            DecisionPhaseDto decisionDto = result.getDecision();
            assertNotNull(decisionDto);
            assertEquals(300L, decisionDto.getDecisionId());
            assertEquals(100L, decisionDto.getRunId());
            assertEquals(TradeDecision.BUY, decisionDto.getDecision());
            assertEquals("JPM", decisionDto.getSymbol());
            assertEquals(30, decisionDto.getQuantity());
            assertEquals(2100L, decisionDto.getLatencyMs());
            assertEquals("decision-system", decisionDto.getSystemPrompt());
            assertEquals("decision-task", decisionDto.getTaskPrompt());

            // Execution sub-DTO
            ExecutionPhaseDto executionDto = result.getExecution();
            assertNotNull(executionDto);
            assertEquals(400L, executionDto.getExecutionId());
            assertEquals(100L, executionDto.getRunId());
            assertEquals(500L, executionDto.getTradeId());
            assertEquals(PhaseStatus.COMPLETED, executionDto.getStatus());
            assertNull(executionDto.getErrorDetails());
            assertNotNull(executionDto.getTrade());
            assertEquals("JPM", executionDto.getTrade().getSymbol());
            assertEquals("BUY", executionDto.getTrade().getTransactionType());
            assertEquals(30, executionDto.getTrade().getQuantity());
            assertEquals(150.0, executionDto.getTrade().getPrice());
            assertEquals(4500.0, executionDto.getTrade().getTotalAmount());
        }

        @Test
        @DisplayName("All phases empty — run-only DTO with null nested phases and no decision-derived fields")
        void assembleDetail_AllPhasesEmpty_NullSubDtos() {
            TradingRunDetailDto result = mapper.assembleDetail(
                run,
                Optional.empty(),
                Optional.empty(),
                Optional.empty()
            );

            assertNotNull(result);

            // Run sub-DTO present, but uses fromEntity (no decision) — decision/symbol null
            TradingRunDto runDto = result.getRun();
            assertNotNull(runDto);
            assertEquals(100L, runDto.getRunId());
            assertEquals(1L, runDto.getAgentId());
            assertEquals(RunStatus.COMPLETED, runDto.getStatus());
            assertEquals(RunPhase.COMPLETED, runDto.getPhase());
            assertNull(runDto.getDecision(), "decision should be null when decisionPhase absent");
            assertNull(runDto.getSymbol(), "symbol should be null when decisionPhase absent");

            // Nested phase DTOs all null
            assertNull(result.getResearch());
            assertNull(result.getDecision());
            assertNull(result.getExecution());
        }

        @Test
        @DisplayName("HOLD decision present — research + decision populated, execution null, run carries decision/symbol")
        void assembleDetail_HoldDecisionNoExecution_PopulatesResearchAndDecisionOnly() {
            decisionPhase.setDecision(TradeDecision.HOLD);
            decisionPhase.setSymbol(null);
            decisionPhase.setQuantity(null);

            TradingRunDetailDto result = mapper.assembleDetail(
                run,
                Optional.of(researchPhase),
                Optional.of(decisionPhase),
                Optional.empty()
            );

            assertNotNull(result);
            assertNotNull(result.getRun());
            assertEquals(TradeDecision.HOLD, result.getRun().getDecision());
            assertNull(result.getRun().getSymbol());

            assertNotNull(result.getResearch());
            assertNotNull(result.getDecision());
            assertEquals(TradeDecision.HOLD, result.getDecision().getDecision());
            assertNull(result.getExecution());
        }
    }

    @Nested
    @DisplayName("assembleListRow() Tests")
    class AssembleListRowTests {

        @Test
        @DisplayName("Non-null decision yields fromEntityWithDecision — decision and symbol populated")
        void assembleListRow_WithDecision_UsesFromEntityWithDecision() {
            TradingRunDto result = mapper.assembleListRow(run, decisionPhase);

            assertNotNull(result);
            assertEquals(100L, result.getRunId());
            assertEquals(1L, result.getAgentId());
            assertEquals(RunStatus.COMPLETED, result.getStatus());
            assertEquals(RunPhase.COMPLETED, result.getPhase());
            assertEquals(TradeDecision.BUY, result.getDecision());
            assertEquals("JPM", result.getSymbol());
            assertEquals(Instant.parse("2026-01-01T10:00:00Z"), result.getStartedAt());
            assertEquals(Instant.parse("2026-01-01T10:05:00Z"), result.getCompletedAt());
            assertNull(result.getErrorMessage());
        }

        @Test
        @DisplayName("Null decision yields fromEntity — decision and symbol stay null")
        void assembleListRow_NullDecision_UsesFromEntity() {
            TradingRunDto result = mapper.assembleListRow(run, null);

            assertNotNull(result);
            assertEquals(100L, result.getRunId());
            assertEquals(1L, result.getAgentId());
            assertEquals(RunStatus.COMPLETED, result.getStatus());
            assertEquals(RunPhase.COMPLETED, result.getPhase());
            assertNull(result.getDecision(), "decision should be null when DecisionPhase arg is null");
            assertNull(result.getSymbol(), "symbol should be null when DecisionPhase arg is null");
            assertEquals(Instant.parse("2026-01-01T10:00:00Z"), result.getStartedAt());
            assertEquals(Instant.parse("2026-01-01T10:05:00Z"), result.getCompletedAt());
        }
    }
}
