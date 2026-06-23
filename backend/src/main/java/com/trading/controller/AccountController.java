package com.trading.controller;

import com.trading.dto.request.InitializeAgentRequest;
import com.trading.dto.request.TradeRequest;
import com.trading.dto.request.TradeType;
import com.trading.dto.response.AccountReportDto;
import com.trading.dto.response.CreateAccountResponse;
import com.trading.dto.response.RecentActivityResponse;
import com.trading.dto.response.TradeResult;
import com.trading.dto.response.TradingHistoryResponse;
import com.trading.service.AccountProvisioner;
import com.trading.service.AccountQueryService;
import com.trading.service.AgentIdentityService;
import com.trading.service.MemoryService;
import com.trading.service.TradeService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * REST controller for account operations.
 * All endpoints follow REST conventions with direct response types.
 * Exceptions are handled by AccountControllerAdvice and GlobalExceptionHandler.
 */
@RestController
@RequestMapping("/api/accounts")
public class AccountController {

    @Autowired
    private AccountQueryService accountQueryService;

    @Autowired
    private AccountProvisioner accountProvisioner;

    @Autowired
    private TradeService tradeService;

    @Autowired
    private AgentIdentityService agentIdentityService;

    @Autowired
    private MemoryService memoryService;

    // ==================== NEW REST ENDPOINTS ====================

    /**
     * Initialize a new agent account (REST endpoint).
     * POST /api/accounts
     *
     * @param request InitializeAgentRequest with agent name and initial balance
     * @return success message with 201 Created
     */
    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<CreateAccountResponse> createAccount(@Valid @RequestBody InitializeAgentRequest request) {
        var account = accountProvisioner.initializeAgent(request.getName(), request.getInitialBalance());
        var response = new CreateAccountResponse(
                account.getAgent().getId(), account.getId(), request.getName(), account.getBalance());
        return ResponseEntity.status(201).body(response);
    }

    /**
     * Execute a trade (buy or sell) for an agent (REST endpoint).
     * POST /api/accounts/{agentId}/trades
     *
     * @param agentId agent ID from path
     * @param request TradeRequest with symbol, quantity, type, and run ID
     * @return TradeResult with 201 Created
     */
    @PostMapping("/{agentId}/trades")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<TradeResult> executeTrade(
            @PathVariable Long agentId, @Valid @RequestBody TradeRequest request) {
        String name = agentIdentityService.requireAgentName(agentId);
        TradeResult result;

        if (request.getType() == TradeType.BUY) {
            result = tradeService.buyShares(name, request.getSymbol(), request.getQuantity(), request.getRunId());
        } else {
            result = tradeService.sellShares(name, request.getSymbol(), request.getQuantity(), request.getRunId());
        }

        return ResponseEntity.status(201).body(result);
    }

    // MCP Resource endpoints
    @GetMapping("/resources/accounts/{agentId}")
    public ResponseEntity<AccountReportDto> getAccountResource(@PathVariable Long agentId) {
        String name = agentIdentityService.requireAgentName(agentId);
        AccountReportDto accountReport = accountQueryService.getAccountReport(name);
        return ResponseEntity.ok(accountReport);
    }

    // ==================== RUN HISTORY ENDPOINTS (agent context) ====================

    /**
     * Get complete trading history for a specific stock.
     * GET /api/accounts/{agentId}/runs/trading-history?symbol=NVDA&days=30
     */
    @GetMapping("/{agentId}/runs/trading-history")
    public ResponseEntity<TradingHistoryResponse> getTradingHistory(
            @PathVariable Long agentId, @RequestParam String symbol, @RequestParam(defaultValue = "30") int days) {
        String agentName = agentIdentityService.requireAgentName(agentId);
        TradingHistoryResponse history = memoryService.getTradingHistory(agentName, symbol, days);
        return ResponseEntity.ok(history);
    }

    /**
     * Get recent trading activity across all stocks.
     * GET /api/accounts/{agentId}/runs/recent-activity?days=7
     */
    @GetMapping("/{agentId}/runs/recent-activity")
    public ResponseEntity<RecentActivityResponse> getRecentActivity(
            @PathVariable Long agentId, @RequestParam(defaultValue = "7") int days) {
        String agentName = agentIdentityService.requireAgentName(agentId);
        RecentActivityResponse activity = memoryService.getRecentActivity(agentName, days);
        return ResponseEntity.ok(activity);
    }
}
