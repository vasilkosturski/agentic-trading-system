package com.trading.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

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
import java.util.stream.Stream;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

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

    private static final String CREATE_ACCOUNT_ENDPOINT = "/api/accounts";
    private static final String EXECUTE_TRADE_ENDPOINT = "/api/accounts/1/trades";

    private static final String CREATE_ACCOUNT_BODY = "{\"name\":\"Warren\",\"initialBalance\":100000.0}";
    private static final String TRADE_BODY = "{\"type\":\"BUY\",\"symbol\":\"AAPL\",\"quantity\":10,\"runId\":1}";

    // Endpoint × role matrix. Anonymous is encoded as a null post-processor and
    // accepts either 401 or 403 — both are valid denials by Spring Security
    // (entry-point vs. access-denied handler depending on chain config).
    private static Stream<Arguments> endpointRoleMatrix() {
        RequestPostProcessor admin = user("admin").roles("ADMIN");
        RequestPostProcessor regular = user("user").roles("USER");
        return Stream.of(
                Arguments.of("createAccount", CREATE_ACCOUNT_ENDPOINT, CREATE_ACCOUNT_BODY, admin, 201),
                Arguments.of("createAccount", CREATE_ACCOUNT_ENDPOINT, CREATE_ACCOUNT_BODY, regular, 403),
                Arguments.of("createAccount", CREATE_ACCOUNT_ENDPOINT, CREATE_ACCOUNT_BODY, null, -1),
                Arguments.of("executeTrade", EXECUTE_TRADE_ENDPOINT, TRADE_BODY, admin, 201),
                Arguments.of("executeTrade", EXECUTE_TRADE_ENDPOINT, TRADE_BODY, regular, 403),
                Arguments.of("executeTrade", EXECUTE_TRADE_ENDPOINT, TRADE_BODY, null, -1));
    }

    @ParameterizedTest(name = "{0}: role={3} → status={4}")
    @MethodSource("endpointRoleMatrix")
    @DisplayName("Write endpoints enforce ADMIN-only access")
    void writeEndpoint_EnforcesAdminOnly(
            String label, String endpoint, String body, RequestPostProcessor authentication, int expectedStatus)
            throws Exception {
        // ADMIN happy path must wire downstream stubs so the controller actually returns 201.
        if (expectedStatus == 201) {
            stubProvisioner();
            stubTradeOrchestrator();
        }

        var request = post(endpoint).contentType(MediaType.APPLICATION_JSON).content(body);
        if (authentication != null) {
            request = request.with(authentication);
        } else {
            request = request.with(SecurityMockMvcRequestPostProcessors.anonymous());
        }

        mockMvc.perform(request).andExpect(result -> {
            int status = result.getResponse().getStatus();
            if (expectedStatus == -1) {
                // Anonymous: either 401 (entry-point) or 403 (access-denied) is acceptable.
                if (status != 401 && status != 403) {
                    throw new AssertionError("Expected 401 or 403 for anonymous, got " + status);
                }
            } else if (status != expectedStatus) {
                throw new AssertionError("Expected " + expectedStatus + " got " + status);
            }
        });
    }

    private void stubProvisioner() {
        TradingAgent agent = new TradingAgent();
        agent.setId(1L);
        agent.setName("Warren");
        TradingAccount account = new TradingAccount();
        account.setId(10L);
        account.setBalance(100000.0);
        account.setAgent(agent);
        org.mockito.Mockito.when(accountProvisioner.initializeAgent(anyString(), anyDouble()))
                .thenReturn(account);
    }

    private void stubTradeOrchestrator() {
        org.mockito.Mockito.when(agentIdentityService.requireAgentName(anyLong()))
                .thenReturn("Warren");
        org.mockito.Mockito.when(tradeOrchestrator.buyShares(anyString(), anyString(), anyInt(), any()))
                .thenReturn(new com.trading.dto.response.TradeResult(1L, "AAPL", 10, 150.0, 98500.0));
    }
}
