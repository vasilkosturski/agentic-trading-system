package com.trading.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.trading.dto.response.AccountReportDto;
import com.trading.dto.response.HoldingDto;
import com.trading.dto.response.TradeResult;
import com.trading.service.AccountService;
import com.trading.service.AgentIdentityService;
import com.trading.service.MemoryService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(AccountController.class)
@AutoConfigureMockMvc(addFilters = false)
@DisplayName("AccountController Tests")
class AccountControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private AccountService accountService;

    @MockBean
    private AgentIdentityService agentIdentityService;

    @MockBean
    private MemoryService memoryService;

    // ==================== Get Account Resource Tests ====================

    @Test
    @DisplayName("GET /resources/accounts/{agentId} - Success")
    void testGetAccountResource_Success() throws Exception {
        List<HoldingDto> holdings = List.of(new HoldingDto("AAPL", 10, 150.0));
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
            5L,                // transactionCount
            holdings           // holdings
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
}
