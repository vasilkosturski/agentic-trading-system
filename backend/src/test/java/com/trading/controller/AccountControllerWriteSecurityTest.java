package com.trading.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.trading.config.SecurityConfig;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.security.JwtAuthenticationFilter;
import com.trading.security.JwtTokenProvider;
import com.trading.service.AccountProvisioner;
import com.trading.service.AccountQueryService;
import com.trading.service.AgentIdentityService;
import com.trading.service.MemoryService;
import com.trading.service.TradeOrchestrator;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Security tests for state-changing endpoints on AccountController:
 * createAccount (POST) and executeTrade (POST).
 *
 * <p>Mirrors the pattern in {@link TradingRunControllerAdminSecurityTest} —
 * real {@link SecurityConfig} import plus a real {@link JwtAuthenticationFilter}
 * wired to mocked collaborators.
 */
@WebMvcTest(AccountController.class)
@Import({SecurityConfig.class, AccountControllerWriteSecurityTest.JwtFilterTestConfig.class})
@DisplayName("AccountController Write Security Tests")
class AccountControllerWriteSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private AccountQueryService accountQueryService;

    @MockBean
    private AccountProvisioner accountProvisioner;

    @MockBean
    private TradeOrchestrator tradeOrchestrator;

    @MockBean
    private AgentIdentityService agentIdentityService;

    @MockBean
    private MemoryService memoryService;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    @TestConfiguration
    static class JwtFilterTestConfig {
        @Bean("accountControllerWriteSecurityJwtAuthenticationFilter")
        JwtAuthenticationFilter jwtAuthenticationFilter(
                JwtTokenProvider jwtTokenProvider, UserDetailsService userDetailsService) {
            return new JwtAuthenticationFilter(jwtTokenProvider, userDetailsService);
        }
    }

    private String createAccountJson() {
        return "{\"name\":\"Warren\",\"initialBalance\":100000.0}";
    }

    private String tradeJson() {
        return "{\"type\":\"BUY\",\"symbol\":\"AAPL\",\"quantity\":10,\"runId\":1}";
    }

    private void stubProvisioner() {
        TradingAgent agent = new TradingAgent();
        agent.setId(1L);
        agent.setName("Warren");
        TradingAccount account = new TradingAccount();
        account.setId(10L);
        account.setBalance(100000.0);
        account.setAgent(agent);
        when(accountProvisioner.initializeAgent(anyString(), anyDouble())).thenReturn(account);
    }

    // ===== createAccount =====

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("ADMIN: POST /api/accounts returns 201")
    void createAccount_WithAdminRole_Returns201() throws Exception {
        stubProvisioner();

        mockMvc.perform(post("/api/accounts")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(createAccountJson()))
                .andExpect(status().isCreated());
    }

    @Test
    @WithMockUser(roles = "USER")
    @DisplayName("USER: POST /api/accounts returns 403")
    void createAccount_WithUserRole_Returns403() throws Exception {
        mockMvc.perform(post("/api/accounts")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(createAccountJson()))
                .andExpect(status().isForbidden());

        verify(accountProvisioner, never()).initializeAgent(anyString(), anyDouble());
    }

    @Test
    @DisplayName("Anonymous: POST /api/accounts is denied")
    void createAccount_Unauthenticated_IsDenied() throws Exception {
        mockMvc.perform(post("/api/accounts")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(createAccountJson()))
                .andExpect(result -> {
                    int status = result.getResponse().getStatus();
                    if (status != 401 && status != 403) {
                        throw new AssertionError("Expected 401 or 403 for anonymous, got " + status);
                    }
                });

        verify(accountProvisioner, never()).initializeAgent(anyString(), anyDouble());
    }

    // ===== executeTrade =====

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("ADMIN: POST /api/accounts/{agentId}/trades returns 201")
    void executeTrade_WithAdminRole_Returns201() throws Exception {
        when(agentIdentityService.requireAgentName(anyLong())).thenReturn("Warren");
        when(tradeOrchestrator.buyShares(anyString(), anyString(), anyInt(), any()))
                .thenReturn(new com.trading.dto.response.TradeResult(
                        1L, "AAPL", 10, 150.0, 98500.0));

        mockMvc.perform(post("/api/accounts/1/trades")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(tradeJson()))
                .andExpect(status().isCreated());
    }

    @Test
    @WithMockUser(roles = "USER")
    @DisplayName("USER: POST /api/accounts/{agentId}/trades returns 403")
    void executeTrade_WithUserRole_Returns403() throws Exception {
        mockMvc.perform(post("/api/accounts/1/trades")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(tradeJson()))
                .andExpect(status().isForbidden());

        verify(tradeOrchestrator, never()).buyShares(anyString(), anyString(), anyInt(), any());
        verify(tradeOrchestrator, never()).sellShares(anyString(), anyString(), anyInt(), any());
    }

    @Test
    @DisplayName("Anonymous: POST /api/accounts/{agentId}/trades is denied")
    void executeTrade_Unauthenticated_IsDenied() throws Exception {
        mockMvc.perform(post("/api/accounts/1/trades")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(tradeJson()))
                .andExpect(result -> {
                    int status = result.getResponse().getStatus();
                    if (status != 401 && status != 403) {
                        throw new AssertionError("Expected 401 or 403 for anonymous, got " + status);
                    }
                });

        verify(tradeOrchestrator, never()).buyShares(anyString(), anyString(), anyInt(), any());
        verify(tradeOrchestrator, never()).sellShares(anyString(), anyString(), anyInt(), any());
    }
}
