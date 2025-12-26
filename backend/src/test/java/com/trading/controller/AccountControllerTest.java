package com.trading.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.trading.dto.request.*;
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

    // ==================== Initialize Agent Tests ====================

    @Test
    @DisplayName("POST /tools/initialize_agent - Success")
    void testInitializeAgent_Success() throws Exception {
        InitializeAgentRequest request = new InitializeAgentRequest("Warren", 100000.0);

        when(accountService.initializeAgent("Warren", 100000.0))
            .thenReturn(testAccount);

        mockMvc.perform(post("/api/accounts/tools/initialize_agent")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data").value("Successfully initialized agent Warren"));
    }

    @Test
    @DisplayName("POST /tools/initialize_agent - Invalid Request")
    void testInitializeAgent_InvalidRequest() throws Exception {
        InitializeAgentRequest request = new InitializeAgentRequest(null, 100000.0);

        mockMvc.perform(post("/api/accounts/tools/initialize_agent")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest());
    }

    // ==================== Get Balance Tests ====================

    @Test
    @DisplayName("POST /tools/get_balance - Success")
    void testGetBalance_Success() throws Exception {
        GetBalanceRequest request = new GetBalanceRequest(1L);

        when(agentIdentityService.requireAgentName(1L)).thenReturn("Warren");
        when(accountService.getBalance("Warren")).thenReturn(95000.0);

        mockMvc.perform(post("/api/accounts/tools/get_balance")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data").value(95000.0));
    }

    @Test
    @DisplayName("POST /tools/get_balance - Missing agentId (null)")
    void testGetBalance_MissingAgentId() throws Exception {
        GetBalanceRequest request = new GetBalanceRequest(null);

        mockMvc.perform(post("/api/accounts/tools/get_balance")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("POST /tools/get_balance - Agent not found")
    void testGetBalance_AgentNotFound() throws Exception {
        Map<String, Object> request = Map.of("agentId", 999);

        when(agentIdentityService.requireAgentName(999L))
            .thenThrow(new ResourceNotFoundException("Agent not found"));

        mockMvc.perform(post("/api/accounts/tools/get_balance")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error").value("Agent not found"));
    }

    // ==================== Get Holdings Tests ====================

    @Test
    @DisplayName("POST /tools/get_holdings - Success")
    void testGetHoldings_Success() throws Exception {
        GetHoldingsRequest request = new GetHoldingsRequest(1L);
        List<HoldingDto> holdings = Arrays.asList(
            new HoldingDto("AAPL", 10, 150.0),
            new HoldingDto("GOOGL", 5, 100.0)
        );

        when(agentIdentityService.requireAgentName(1L)).thenReturn("Warren");
        when(accountService.getHoldings("Warren")).thenReturn(holdings);

        mockMvc.perform(post("/api/accounts/tools/get_holdings")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data").isArray())
                .andExpect(jsonPath("$.data", hasSize(2)))
                .andExpect(jsonPath("$.data[0].symbol").value("AAPL"))
                .andExpect(jsonPath("$.data[1].symbol").value("GOOGL"));
    }

    // ==================== Buy Shares Tests ====================

    @Test
    @DisplayName("POST /tools/buy_shares - Success")
    void testBuyShares_Success() throws Exception {
        BuySharesRequest request = new BuySharesRequest(1L, "AAPL", 10, 100L);

        TradeResult tradeResult = new TradeResult(
            "AAPL", 10, 150.0, 93500.0
        );

        when(agentIdentityService.requireAgentName(1L)).thenReturn("Warren");
        when(accountService.buyShares("Warren", "AAPL", 10, 100L))
            .thenReturn(tradeResult);

        mockMvc.perform(post("/api/accounts/tools/buy_shares")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.symbol").value("AAPL"))
                .andExpect(jsonPath("$.data.quantity").value(10))
                .andExpect(jsonPath("$.data.price").value(150.0))
                .andExpect(jsonPath("$.data.newBalance").value(93500.0));
    }

    @Test
    @DisplayName("POST /tools/buy_shares - Missing runId (validation)")
    void testBuyShares_MissingRunId() throws Exception {
        BuySharesRequest request = new BuySharesRequest(1L, "AAPL", 10, null);

        mockMvc.perform(post("/api/accounts/tools/buy_shares")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("POST /tools/buy_shares - Insufficient funds")
    void testBuyShares_InsufficientFunds() throws Exception {
        BuySharesRequest request = new BuySharesRequest(1L, "AAPL", 10000, 100L);

        when(agentIdentityService.requireAgentName(1L)).thenReturn("Warren");
        when(accountService.buyShares("Warren", "AAPL", 10000, 100L))
            .thenThrow(new BusinessRuleException("Insufficient funds"));

        mockMvc.perform(post("/api/accounts/tools/buy_shares")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error").value("Insufficient funds"));
    }

    @Test
    @DisplayName("POST /tools/buy_shares - Position limit reached")
    void testBuyShares_PositionLimit() throws Exception {
        BuySharesRequest request = new BuySharesRequest(1L, "AAPL", 10, 100L);

        when(agentIdentityService.requireAgentName(1L)).thenReturn("Warren");
        when(accountService.buyShares("Warren", "AAPL", 10, 100L))
            .thenThrow(new BusinessRuleException("Agent already has maximum number of positions (10)"));

        mockMvc.perform(post("/api/accounts/tools/buy_shares")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error").value(containsString("maximum")));
    }

    // ==================== Sell Shares Tests ====================

    @Test
    @DisplayName("POST /tools/sell_shares - Success")
    void testSellShares_Success() throws Exception {
        SellSharesRequest request = new SellSharesRequest(1L, "AAPL", 5, 100L);

        TradeResult tradeResult = new TradeResult(
            "AAPL", 5, 160.0, 96300.0
        );

        when(agentIdentityService.requireAgentName(1L)).thenReturn("Warren");
        when(accountService.sellShares("Warren", "AAPL", 5, 100L))
            .thenReturn(tradeResult);

        mockMvc.perform(post("/api/accounts/tools/sell_shares")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.symbol").value("AAPL"))
                .andExpect(jsonPath("$.data.quantity").value(5));
    }

    @Test
    @DisplayName("POST /tools/sell_shares - Insufficient shares")
    void testSellShares_InsufficientShares() throws Exception {
        SellSharesRequest request = new SellSharesRequest(1L, "AAPL", 100, 100L);

        when(agentIdentityService.requireAgentName(1L)).thenReturn("Warren");
        when(accountService.sellShares("Warren", "AAPL", 100, 100L))
            .thenThrow(new BusinessRuleException("Insufficient shares to sell"));

        mockMvc.perform(post("/api/accounts/tools/sell_shares")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error").value("Insufficient shares to sell"));
    }

    // ==================== Update Activity Tests ====================

    @Test
    @DisplayName("POST /tools/update_activity - Success")
    void testUpdateActivity_Success() throws Exception {
        UpdateActivityRequest request = new UpdateActivityRequest(1L);

        when(agentIdentityService.requireAgentName(1L)).thenReturn("Warren");

        mockMvc.perform(post("/api/accounts/tools/update_activity")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isNoContent());
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
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error").value("Trade not found"));
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
