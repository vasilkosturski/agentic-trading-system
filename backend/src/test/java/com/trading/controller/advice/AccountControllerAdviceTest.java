package com.trading.controller.advice;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.trading.config.TestSecurityConfig;
import com.trading.controller.AccountController;
import com.trading.exception.ResourceNotFoundException;
import com.trading.service.AccountProvisioner;
import com.trading.service.AccountQueryService;
import com.trading.service.AgentIdentityService;
import com.trading.service.MemoryService;
import com.trading.service.TradeOrchestrator;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Verifies that AccountControllerAdvice translates typed exceptions thrown by
 * AccountController dependencies into RFC 7807 ProblemDetail responses with the
 * correct HTTP status. Guards the unknown-agent 404 contract end-to-end.
 */
@WebMvcTest(AccountController.class)
@AutoConfigureMockMvc(addFilters = false)
@Import(TestSecurityConfig.class)
@DisplayName("AccountControllerAdvice Tests")
class AccountControllerAdviceTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private AccountQueryService accountQueryService;

    @MockitoBean
    private AccountProvisioner accountProvisioner;

    @MockitoBean
    private AgentIdentityService agentIdentityService;

    @MockitoBean
    private MemoryService memoryService;

    @MockitoBean
    private TradeOrchestrator tradeOrchestrator;

    @Test
    @DisplayName("Unknown agent returns 404 ProblemDetail when AccountQueryService throws ResourceNotFoundException")
    void unknownAgent_returns404ProblemDetail() throws Exception {
        Long agentId = 999L;
        String agentName = "nonexistent";

        when(agentIdentityService.requireAgentName(agentId)).thenReturn(agentName);
        when(accountQueryService.getAccountReport(agentName))
                .thenThrow(new ResourceNotFoundException("Trading account not found for agent: " + agentName));

        mockMvc.perform(get("/api/accounts/resources/accounts/{agentId}", agentId))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.type").value("https://trading.example.com/errors/resource-not-found"))
                .andExpect(jsonPath("$.title").value("Resource Not Found"))
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.detail").value(org.hamcrest.Matchers.containsString(agentName)));
    }

    @Test
    @DisplayName(
            "GET /api/accounts/{unknown}/runs/trading-history returns 404 ProblemDetail when MemoryService propagates ResourceNotFoundException")
    void unknownAgentTradingHistory_returns404ProblemDetail() throws Exception {
        Long agentId = 999L;
        String agentName = "nonexistent";

        when(agentIdentityService.requireAgentName(agentId)).thenReturn(agentName);
        when(memoryService.getTradingHistory(agentName, "NVDA", 30))
                .thenThrow(new ResourceNotFoundException("Agent not found: " + agentName));

        mockMvc.perform(get("/api/accounts/{agentId}/runs/trading-history", agentId)
                        .param("symbol", "NVDA")
                        .param("days", "30"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.type").value("https://trading.example.com/errors/resource-not-found"))
                .andExpect(jsonPath("$.title").value("Resource Not Found"))
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.detail").value(org.hamcrest.Matchers.containsString(agentName)));
    }

    @Test
    @DisplayName(
            "Unconfigured agent returns 500 ProblemDetail with NO message leak when IllegalStateException is thrown")
    void unconfiguredAgent_returns500WithoutLeak() throws Exception {
        Long agentId = 1L;
        String agentName = "warren";

        when(agentIdentityService.requireAgentName(agentId)).thenReturn(agentName);
        when(accountQueryService.getAccountReport(agentName))
                .thenThrow(
                        new IllegalStateException(
                                "No initial-capital configured for agent: warren. Add trading.agents.profiles.warren.initial-capital to application.yml"));

        mockMvc.perform(get("/api/accounts/resources/accounts/{agentId}", agentId))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.type").value("https://trading.example.com/errors/internal-error"))
                .andExpect(jsonPath("$.title").value("Internal Server Error"))
                .andExpect(jsonPath("$.status").value(500))
                .andExpect(jsonPath("$.detail").value("Internal server error"))
                .andExpect(jsonPath("$.detail")
                        .value(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("warren"))))
                .andExpect(jsonPath("$.detail")
                        .value(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("initial-capital"))));
    }
}
