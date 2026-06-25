package com.trading.controller;

import static org.hamcrest.Matchers.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.trading.config.TestSecurityConfig;
import com.trading.config.TradingPublicProperties;
import com.trading.dto.request.CompleteRunRequest;
import com.trading.dto.request.CreateRunRequest;
import com.trading.dto.request.RunQueryFilter;
import com.trading.dto.request.UpdatePhaseRequest;
import com.trading.dto.response.DecisionPhaseDto;
import com.trading.dto.response.ExecutionPhaseDto;
import com.trading.dto.response.ResearchPhaseDto;
import com.trading.dto.response.RunListResponseDto;
import com.trading.dto.response.TradingRunDetailDto;
import com.trading.dto.response.TradingRunDto;
import com.trading.enums.PhaseStatus;
import com.trading.enums.RunPhase;
import com.trading.enums.RunStatus;
import com.trading.enums.TradeDecision;
import com.trading.exception.ResourceNotFoundException;
import com.trading.service.TradingRunService;
import java.time.Instant;
import java.util.Arrays;
import java.util.Collections;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Unit tests for TradingRunController.
 * Uses @WebMvcTest for controller slice testing with mocked service.
 * Security filters are disabled to test controller logic in isolation.
 */
@WebMvcTest(TradingRunController.class)
@AutoConfigureMockMvc(addFilters = false)
@Import(TestSecurityConfig.class)
@DisplayName("TradingRunController Tests")
class TradingRunControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockitoBean
    private TradingRunService tradingRunService;

    @MockitoBean
    private TradingPublicProperties tradingPublicProperties;

    // Test fixtures
    private TradingRunDto testRunDto;
    private TradingRunDetailDto testRunDetailDto;
    private ResearchPhaseDto testResearchDto;
    private DecisionPhaseDto testDecisionDto;
    private ExecutionPhaseDto testExecutionDto;

    @BeforeEach
    void setUp() {
        when(tradingPublicProperties.getDisplayDelayDays()).thenReturn(7);
        // Create test DTOs using setters to avoid type issues with complex nested types
        testRunDto = new TradingRunDto();
        testRunDto.setRunId(100L);
        testRunDto.setAgentId(1L);
        testRunDto.setStatus(RunStatus.IN_PROGRESS);
        testRunDto.setPhase(RunPhase.INITIALIZING);
        testRunDto.setStartedAt(Instant.now());

        testResearchDto = new ResearchPhaseDto();
        testResearchDto.setResearchId(200L);
        testResearchDto.setRunId(100L);
        testResearchDto.setCandidates(Arrays.asList("AAPL", "GOOGL", "MSFT"));
        testResearchDto.setResearchNotes("Tech sector analysis");
        testResearchDto.setLatencyMs(3400L);
        testResearchDto.setCreatedAt(Instant.now());

        testDecisionDto = new DecisionPhaseDto();
        testDecisionDto.setDecisionId(300L);
        testDecisionDto.setRunId(100L);
        testDecisionDto.setDecision(TradeDecision.BUY);
        testDecisionDto.setSymbol("AAPL");
        testDecisionDto.setQuantity(50);
        testDecisionDto.setLatencyMs(2100L);
        testDecisionDto.setCreatedAt(Instant.now());

        testExecutionDto = new ExecutionPhaseDto();
        testExecutionDto.setExecutionId(400L);
        testExecutionDto.setRunId(100L);
        testExecutionDto.setTradeId(500L);
        testExecutionDto.setStatus(PhaseStatus.COMPLETED);
        testExecutionDto.setCreatedAt(Instant.now());

        testRunDetailDto = new TradingRunDetailDto(testRunDto, testResearchDto, testDecisionDto, testExecutionDto);
    }

    // ==================== POST /api/runs Tests ====================

    @Nested
    @DisplayName("POST /api/runs (createRun)")
    class CreateRunTests {

        @Test
        @DisplayName("Valid request returns 201 Created with TradingRunDto and Location header")
        void createRun_ValidRequest_Returns201() throws Exception {
            when(tradingRunService.createRun(1L)).thenReturn(testRunDto);

            CreateRunRequest request = new CreateRunRequest(1L);

            mockMvc.perform(post("/api/runs")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(request)))
                    .andExpect(status().isCreated())
                    .andExpect(header().exists("Location"))
                    .andExpect(header().string("Location", containsString("/api/runs/100")))
                    .andExpect(jsonPath("$.runId").value(100))
                    .andExpect(jsonPath("$.agentId").value(1))
                    .andExpect(jsonPath("$.status").value("IN_PROGRESS"))
                    .andExpect(jsonPath("$.phase").value("INITIALIZING"));

            verify(tradingRunService).createRun(1L);
        }

        @Test
        @DisplayName("Agent not found returns 404")
        void createRun_AgentNotFound_Returns404() throws Exception {
            when(tradingRunService.createRun(999L))
                    .thenThrow(new ResourceNotFoundException("Agent not found with id: 999"));

            CreateRunRequest request = new CreateRunRequest(999L);

            mockMvc.perform(post("/api/runs")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(request)))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.status").value(404))
                    .andExpect(jsonPath("$.detail").value("Agent not found with id: 999"));
        }

        @Test
        @DisplayName("Missing agentId returns 400 via @Valid annotation")
        void createRun_MissingAgentId_Returns400() throws Exception {
            // Request without agentId - should fail @NotNull validation
            String jsonWithoutAgentId = "{}";

            mockMvc.perform(post("/api/runs")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(jsonWithoutAgentId))
                    .andExpect(status().isBadRequest());

            // Service should NOT be called - validation fails at controller level
            verify(tradingRunService, never()).createRun(any());
        }
    }

    // ==================== PATCH /api/runs/{id}/phase Tests ====================

    @Nested
    @DisplayName("PATCH /api/runs/{id}/phase (updatePhase)")
    class UpdatePhaseTests {

        @Test
        @DisplayName("Valid request returns 200")
        void updatePhase_ValidRequest_Returns200() throws Exception {
            doNothing().when(tradingRunService).updatePhase(eq(100L), eq(RunPhase.RESEARCHING), any());

            UpdatePhaseRequest request = new UpdatePhaseRequest();
            request.setPhase(RunPhase.RESEARCHING);

            mockMvc.perform(patch("/api/runs/100/phase")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(request)))
                    .andExpect(status().isOk());

            verify(tradingRunService).updatePhase(eq(100L), eq(RunPhase.RESEARCHING), any());
        }

        @Test
        @DisplayName("Invalid phase transition returns 400")
        void updatePhase_InvalidTransition_Returns400() throws Exception {
            doThrow(new IllegalArgumentException("Invalid phase transition from COMPLETED to RESEARCHING"))
                    .when(tradingRunService)
                    .updatePhase(eq(100L), any(RunPhase.class), any());

            UpdatePhaseRequest request = new UpdatePhaseRequest();
            request.setPhase(RunPhase.RESEARCHING);

            mockMvc.perform(patch("/api/runs/100/phase")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(request)))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.status").value(400));
        }

        @Test
        @DisplayName("Missing phase returns 400")
        void updatePhase_MissingPhase_Returns400() throws Exception {
            mockMvc.perform(patch("/api/runs/100/phase")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{}"))
                    .andExpect(status().isBadRequest());
        }
    }

    // ==================== PUT /api/runs/{id}/complete Tests ====================

    @Nested
    @DisplayName("PUT /api/runs/{id}/complete (completeRun)")
    class CompleteRunTests {

        @Test
        @DisplayName("Valid BUY request returns 200")
        void completeRun_ValidBuyRequest_Returns200() throws Exception {
            doNothing().when(tradingRunService).completeRun(eq(100L), any(CompleteRunRequest.class));

            CompleteRunRequest request = createBuyRequest();

            mockMvc.perform(put("/api/runs/100/complete")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(request)))
                    .andExpect(status().isOk());

            verify(tradingRunService).completeRun(eq(100L), any(CompleteRunRequest.class));
        }

        @Test
        @DisplayName("Valid HOLD request returns 200")
        void completeRun_ValidHoldRequest_Returns200() throws Exception {
            doNothing().when(tradingRunService).completeRun(eq(100L), any(CompleteRunRequest.class));

            CompleteRunRequest request = createHoldRequest();

            mockMvc.perform(put("/api/runs/100/complete")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(request)))
                    .andExpect(status().isOk());
        }

        @Test
        @DisplayName("Invalid request (BUY without symbol) returns 400")
        void completeRun_InvalidRequest_Returns400() throws Exception {
            doThrow(new IllegalArgumentException("BUY/SELL decision requires symbol"))
                    .when(tradingRunService)
                    .completeRun(eq(100L), any(CompleteRunRequest.class));

            CompleteRunRequest request = createBuyRequest();
            request.getDecision().setSymbol(null);

            mockMvc.perform(put("/api/runs/100/complete")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(request)))
                    .andExpect(status().isBadRequest());
        }

        @Test
        @DisplayName("Missing decision field returns 400 via @Valid annotation")
        void completeRun_MissingDecision_Returns400() throws Exception {
            // Request without decision field - should fail @NotNull validation
            String jsonWithoutDecision =
                    """
                {
                    "candidates": ["AAPL"],
                    "researchNotes": "Some notes"
                }
                """;

            mockMvc.perform(put("/api/runs/100/complete")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(jsonWithoutDecision))
                    .andExpect(status().isBadRequest());

            // Service should NOT be called - validation fails at controller level
            verify(tradingRunService, never()).completeRun(any(), any());
        }

        private CompleteRunRequest createBuyRequest() {
            // Research phase DTO (using fully qualified name to avoid conflict with response DTO)
            var research = new com.trading.dto.request.ResearchPhaseDto();
            research.setCandidates(Arrays.asList("AAPL", "GOOGL"));
            research.setNotes("Tech analysis");
            research.setLatencyMs(3400L);

            // Decision phase DTO
            var decision = new com.trading.dto.request.DecisionPhaseDto();
            decision.setDecision(TradeDecision.BUY);
            decision.setSymbol("AAPL");
            decision.setQuantity(50);
            decision.setLatencyMs(2100L);

            // Execution phase DTO
            var execution = new com.trading.dto.request.ExecutionPhaseDto();
            execution.setTradeId(500L);
            execution.setStatus(PhaseStatus.COMPLETED);

            return new CompleteRunRequest(research, decision, execution);
        }

        private CompleteRunRequest createHoldRequest() {
            // Research phase DTO (using fully qualified name to avoid conflict with response DTO)
            var research = new com.trading.dto.request.ResearchPhaseDto();
            research.setCandidates(Arrays.asList("AAPL", "GOOGL"));
            research.setNotes("Market conditions unfavorable");
            research.setLatencyMs(3400L);

            // Decision phase DTO
            var decision = new com.trading.dto.request.DecisionPhaseDto();
            decision.setDecision(TradeDecision.HOLD);
            decision.setLatencyMs(2100L);

            return new CompleteRunRequest(research, decision, null);
        }
    }

    // ==================== GET /api/runs/{id} Tests ====================

    @Nested
    @DisplayName("GET /api/runs/{id} (getRunWithAllPhases)")
    class GetRunWithAllPhasesTests {

        @Test
        @DisplayName("Valid ID returns 200 with full run detail")
        void getRunWithAllPhases_ValidId_Returns200() throws Exception {
            when(tradingRunService.getRunWithAllPhases(100L)).thenReturn(testRunDetailDto);

            mockMvc.perform(get("/api/runs/100"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.run.runId").value(100))
                    .andExpect(jsonPath("$.research.researchId").value(200))
                    .andExpect(jsonPath("$.decision.decisionId").value(300))
                    .andExpect(jsonPath("$.execution.executionId").value(400));
        }

        @Test
        @DisplayName("Run not found returns 404")
        void getRunWithAllPhases_RunNotFound_Returns404() throws Exception {
            when(tradingRunService.getRunWithAllPhases(999L))
                    .thenThrow(new ResourceNotFoundException("Trading run not found with id: 999"));

            mockMvc.perform(get("/api/runs/999"))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.status").value(404));
        }
    }

    // ==================== GET /api/runs/{id}/research Tests ====================

    @Nested
    @DisplayName("GET /api/runs/{id}/research (getResearchPhase)")
    class GetResearchPhaseTests {

        @Test
        @DisplayName("Valid ID returns 200 with research phase")
        void getResearchPhase_ValidId_Returns200() throws Exception {
            when(tradingRunService.getResearchPhase(100L)).thenReturn(testResearchDto);

            mockMvc.perform(get("/api/runs/100/research"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.researchId").value(200))
                    .andExpect(jsonPath("$.runId").value(100))
                    .andExpect(jsonPath("$.candidates", hasSize(3)))
                    .andExpect(jsonPath("$.researchNotes").value("Tech sector analysis"));
        }
    }

    // ==================== GET /api/runs/{id}/decision Tests ====================

    @Nested
    @DisplayName("GET /api/runs/{id}/decision (getDecisionPhase)")
    class GetDecisionPhaseTests {

        @Test
        @DisplayName("Valid ID returns 200 with decision phase")
        void getDecisionPhase_ValidId_Returns200() throws Exception {
            when(tradingRunService.getDecisionPhase(100L)).thenReturn(testDecisionDto);

            mockMvc.perform(get("/api/runs/100/decision"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.decisionId").value(300))
                    .andExpect(jsonPath("$.decision").value("BUY"))
                    .andExpect(jsonPath("$.symbol").value("AAPL"))
                    .andExpect(jsonPath("$.quantity").value(50));
        }
    }

    // ==================== GET /api/runs/{id}/execution Tests ====================

    @Nested
    @DisplayName("GET /api/runs/{id}/execution (getExecutionPhase)")
    class GetExecutionPhaseTests {

        @Test
        @DisplayName("BUY decision returns 200 with execution phase")
        void getExecutionPhase_BuyDecision_Returns200() throws Exception {
            when(tradingRunService.getExecutionPhase(100L)).thenReturn(testExecutionDto);

            mockMvc.perform(get("/api/runs/100/execution"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.executionId").value(400))
                    .andExpect(jsonPath("$.tradeId").value(500))
                    .andExpect(jsonPath("$.status").value("COMPLETED"));
        }

        @Test
        @DisplayName("HOLD decision returns 404")
        void getExecutionPhase_HoldDecision_Returns404() throws Exception {
            when(tradingRunService.getExecutionPhase(100L))
                    .thenThrow(new ResourceNotFoundException("Execution phase not found for run: 100"));

            mockMvc.perform(get("/api/runs/100/execution"))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.status").value(404));
        }
    }

    // ==================== GET /api/runs (listRuns) Tests ====================

    @Nested
    @DisplayName("GET /api/runs (listRuns)")
    class ListRunsTests {

        @Test
        @DisplayName("No filters returns 200 with all runs")
        void listRuns_NoFilters_Returns200() throws Exception {
            RunListResponseDto response = new RunListResponseDto(Arrays.asList(testRunDto), 1L, 0, 20);
            when(tradingRunService.listRuns(isNull(), any(Instant.class), any()))
                    .thenReturn(response);

            mockMvc.perform(get("/api/runs"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.runs", hasSize(1)))
                    .andExpect(jsonPath("$.total").value(1))
                    .andExpect(jsonPath("$.page").value(0))
                    .andExpect(jsonPath("$.limit").value(20));
        }

        @Test
        @DisplayName("With filters returns 200")
        void listRuns_WithFilters_Returns200() throws Exception {
            RunListResponseDto response = new RunListResponseDto(Arrays.asList(testRunDto), 1L, 0, 20);
            when(tradingRunService.listRuns(any(RunQueryFilter.class), any(Instant.class), any()))
                    .thenReturn(response);

            mockMvc.perform(get("/api/runs")
                            .param("agentId", "1")
                            .param("status", "IN_PROGRESS")
                            .param("decision", "BUY")
                            .param("symbol", "AAPL"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.runs", hasSize(1)));

            verify(tradingRunService).listRuns(any(RunQueryFilter.class), any(Instant.class), any());
        }

        @Test
        @DisplayName("Pagination returns correct page")
        void listRuns_Pagination_Returns200() throws Exception {
            RunListResponseDto response = new RunListResponseDto(Arrays.asList(testRunDto), 50L, 2, 10);
            when(tradingRunService.listRuns(isNull(), any(Instant.class), any()))
                    .thenReturn(response);

            mockMvc.perform(get("/api/runs").param("page", "2").param("size", "10"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.total").value(50))
                    .andExpect(jsonPath("$.page").value(2))
                    .andExpect(jsonPath("$.limit").value(10));
        }

        @Test
        @DisplayName("Empty result returns 200 with empty list")
        void listRuns_EmptyResult_Returns200() throws Exception {
            RunListResponseDto response = new RunListResponseDto(Collections.emptyList(), 0L, 0, 20);
            when(tradingRunService.listRuns(isNull(), any(Instant.class), any()))
                    .thenReturn(response);

            mockMvc.perform(get("/api/runs"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.runs", hasSize(0)))
                    .andExpect(jsonPath("$.total").value(0));
        }

        @Test
        @DisplayName("Public endpoint always passes a non-null cutoffDate (legal display delay enforced)")
        void listRuns_AlwaysEnforcesPublicDisplayDelay() throws Exception {
            RunListResponseDto response = new RunListResponseDto(Arrays.asList(testRunDto), 1L, 0, 20);
            // Public endpoint must pass a NON-NULL cutoffDate (admin would pass null)
            when(tradingRunService.listRuns(isNull(), any(Instant.class), any()))
                    .thenReturn(response);

            mockMvc.perform(get("/api/runs")).andExpect(status().isOk());

            // Verify service was called with a non-null cutoff (legal protection enabled)
            verify(tradingRunService).listRuns(isNull(), any(Instant.class), any());
            verify(tradingRunService, never()).listRuns(isNull(), isNull(), any());
        }

        @Test
        @DisplayName("Public endpoint ignores showAll query param — cutoff is always derived from properties")
        void listRuns_IgnoresShowAllParameter() throws Exception {
            RunListResponseDto response = new RunListResponseDto(Arrays.asList(testRunDto), 1L, 0, 20);
            // Service must ALWAYS receive a non-null cutoff, regardless of client showAll= param
            when(tradingRunService.listRuns(isNull(), any(Instant.class), any()))
                    .thenReturn(response);

            // Client attempts to bypass the public delay with showAll=true on the public endpoint
            mockMvc.perform(get("/api/runs").param("showAll", "true")).andExpect(status().isOk());

            // Verify the cutoff was applied (non-null) — admin bypass requires the /admin endpoint
            verify(tradingRunService).listRuns(isNull(), any(Instant.class), any());
            verify(tradingRunService, never()).listRuns(isNull(), isNull(), any());
        }
    }

    // Note: Security tests for GET /api/runs/admin are in TradingRunControllerAdminSecurityTest
    // Separate test class required because @PreAuthorize testing needs security filters enabled
}
