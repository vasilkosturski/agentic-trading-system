package com.trading.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.trading.dto.response.AccountReportDto;
import com.trading.dto.response.HoldingDto;
import com.trading.dto.response.PortfolioHistoryPoint;
import com.trading.dto.response.RecentTradeDto;
import com.trading.dto.response.TradeDetailResponse;
import com.trading.dto.response.TradeResult;
import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.entity.AccountTransaction;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.entity.TransactionType;
import com.trading.repository.AccountPortfolioSnapshotRepository;
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.AgentReasoningStepRepository;
import com.trading.service.AccountService;
import com.trading.service.AgentIdentityService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import com.trading.exception.BusinessRuleException;
import com.trading.exception.ResourceNotFoundException;

import java.time.Instant;
import java.util.*;

import static org.hamcrest.Matchers.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(AccountController.class)
@DisplayName("AccountController Tests")
class AccountControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private AccountService accountService;

    @MockBean
    private AccountPortfolioSnapshotRepository snapshotRepository;

    @MockBean
    private AccountTransactionRepository transactionRepository;

    @MockBean
    private AgentReasoningStepRepository reasoningStepRepository;

    @MockBean
    private AgentIdentityService agentIdentityService;

    private TradingAgent testAgent;
    private TradingAccount testAccount;
    private AccountTransaction testTransaction;

    @BeforeEach
    void setUp() {
        testAgent = new TradingAgent("Warren", "Value investor");
        testAgent.setId(1L);

        testAccount = new TradingAccount(testAgent, 100000.0);
        testAccount.setId(1L);

        testTransaction = new AccountTransaction();
        testTransaction.setId(1L);
        testTransaction.setAccount(testAccount);
        testTransaction.setSymbol("AAPL");
        testTransaction.setQuantity(10);
        testTransaction.setPrice(150.0);
        testTransaction.setTotalAmount(1500.0);
        testTransaction.setTransactionType(TransactionType.BUY);
        testTransaction.setTimestamp(Instant.now());
    }

    // ==================== Get Account Resource Tests ====================

    @Test
    @DisplayName("GET /resources/accounts/{agentId} - Success")
    void testGetAccountResource_Success() throws Exception {
        AccountReportDto report = new AccountReportDto(
            "Warren",           // agentName
            95000.0,           // balance
            5000.0,            // holdingsValue
            100000.0,          // totalPortfolioValue
            100000.0,          // initialBalance
            0.0,               // totalProfitLoss
            0.0,               // profitLossPercent
            java.time.LocalDateTime.now(),  // lastUpdated
            1,                 // holdingsCount
            5L                 // transactionCount
        );

        when(agentIdentityService.requireAgentName(1L)).thenReturn("Warren");
        when(accountService.getAccountReport("Warren")).thenReturn(report);

        mockMvc.perform(get("/api/accounts/resources/accounts/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.agentName").value("Warren"))
                .andExpect(jsonPath("$.balance").value(95000.0))
                .andExpect(jsonPath("$.holdingsValue").value(5000.0))
                .andExpect(jsonPath("$.totalPortfolioValue").value(100000.0));
    }

    // ==================== Portfolio History Tests ====================

    @Test
    @DisplayName("GET /portfolio/{agentId}/history - Success")
    void testGetPortfolioHistory_Success() throws Exception {
        List<AccountPortfolioSnapshot> snapshots = Arrays.asList(
            createSnapshot(100000.0, Instant.now().minusSeconds(86400)),
            createSnapshot(101000.0, Instant.now())
        );

        when(agentIdentityService.requireAgentName(1L)).thenReturn("Warren");
        when(snapshotRepository.getPortfolioPerformance(eq("Warren"), any(Instant.class)))
            .thenReturn(snapshots);

        mockMvc.perform(get("/api/accounts/portfolio/1/history")
                .param("days", "7"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[0].portfolioValue").value(100000.0))
                .andExpect(jsonPath("$[1].portfolioValue").value(101000.0));
    }

    // ==================== Recent Trades Tests ====================

    @Test
    @DisplayName("GET /trades/recent - Success")
    void testGetRecentTrades_Success() throws Exception {
        List<AccountTransaction> transactions = Arrays.asList(
            testTransaction
        );

        when(transactionRepository.findRecentTransactions(20))
            .thenReturn(transactions);

        mockMvc.perform(get("/api/accounts/trades/recent")
                .param("limit", "20"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].id").value(1))
                .andExpect(jsonPath("$[0].agentName").value("Warren"))
                .andExpect(jsonPath("$[0].symbol").value("AAPL"))
                .andExpect(jsonPath("$[0].transactionType").value("BUY"));
    }

    @Test
    @DisplayName("GET /trades/recent - With custom limit")
    void testGetRecentTrades_CustomLimit() throws Exception {
        when(transactionRepository.findRecentTransactions(5))
            .thenReturn(Collections.emptyList());

        mockMvc.perform(get("/api/accounts/trades/recent")
                .param("limit", "5"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray())
                .andExpect(jsonPath("$", hasSize(0)));
    }

    // ==================== Trade Detail Tests ====================

    @Test
    @DisplayName("GET /trades/{tradeId} - Success")
    void testGetTradeDetail_Success() throws Exception {
        when(transactionRepository.findById(1L))
            .thenReturn(Optional.of(testTransaction));
        when(transactionRepository.findRelatedTrades(1L, "AAPL", 1L))
            .thenReturn(Collections.emptyList());
        when(reasoningStepRepository.findByAgentRunIdOrderBySequenceNumberAsc(any()))
            .thenReturn(Collections.emptyList());

        mockMvc.perform(get("/api/accounts/trades/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.trade.id").value(1))
                .andExpect(jsonPath("$.trade.agentName").value("Warren"))
                .andExpect(jsonPath("$.trade.symbol").value("AAPL"))
                .andExpect(jsonPath("$.trade.type").value("BUY"))
                .andExpect(jsonPath("$.relatedTrades").isArray());
    }

    @Test
    @DisplayName("GET /trades/{tradeId} - Trade not found")
    void testGetTradeDetail_NotFound() throws Exception {
        when(transactionRepository.findById(999L))
            .thenReturn(Optional.empty());

        mockMvc.perform(get("/api/accounts/trades/999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.detail").value("Trade not found"));
    }

    // ==================== Helper Methods ====================

    private AccountPortfolioSnapshot createSnapshot(Double totalValue, Instant timestamp) {
        AccountPortfolioSnapshot snapshot = new AccountPortfolioSnapshot();
        snapshot.setAccount(testAccount);
        snapshot.setTotalValue(totalValue);
        snapshot.setTimestamp(timestamp);
        return snapshot;
    }
}
