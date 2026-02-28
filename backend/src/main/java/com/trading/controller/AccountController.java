package com.trading.controller;

import com.trading.dto.request.*;
import com.trading.dto.response.AccountReportDto;
import com.trading.dto.response.HoldingDto;
import com.trading.dto.response.PortfolioHistoryPoint;
import com.trading.dto.response.RecentActivityResponse;
import com.trading.dto.response.RecentTradeDto;
import com.trading.dto.response.RunDetailDto;
import com.trading.dto.response.TradeDetailResponse;
import com.trading.dto.response.TradeResult;
import com.trading.dto.response.TradingHistoryResponse;
import com.trading.exception.ResourceNotFoundException;
import jakarta.validation.Valid;
import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.entity.AccountTransaction;
import com.trading.entity.AgentRun;
import com.trading.repository.AccountPortfolioSnapshotRepository;
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.AgentReasoningStepRepository;
import com.trading.service.AccountService;
import com.trading.service.AgentIdentityService;
import com.trading.service.MemoryService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * REST controller for account operations.
 * All endpoints follow REST conventions with direct response types.
 * Exceptions are handled by AccountControllerAdvice and GlobalExceptionHandler.
 */
@RestController
@RequestMapping("/api/accounts")
public class AccountController {

    @Autowired
    private AccountService accountService;

    @Autowired
    private AccountPortfolioSnapshotRepository snapshotRepository;

    @Autowired
    private AccountTransactionRepository transactionRepository;

    @Autowired
    private AgentReasoningStepRepository reasoningStepRepository;

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
    public ResponseEntity<String> createAccount(@Valid @RequestBody InitializeAgentRequest request) {
        accountService.initializeAgent(request.getName(), request.getInitialBalance());
        return ResponseEntity.status(201).body("Successfully initialized agent " + request.getName());
    }

    /**
     * Get agent balance (REST endpoint).
     * GET /api/accounts/{agentId}/balance
     *
     * @param agentId agent ID from path
     * @return balance as Double
     */
    @GetMapping("/{agentId}/balance")
    public ResponseEntity<Double> getBalanceRest(@PathVariable Long agentId) {
        String name = agentIdentityService.requireAgentName(agentId);
        Double balance = accountService.getBalance(name);
        return ResponseEntity.ok(balance);
    }

    /**
     * Get agent holdings (REST endpoint).
     * GET /api/accounts/{agentId}/holdings
     *
     * @param agentId agent ID from path
     * @return List of HoldingDto
     */
    @GetMapping("/{agentId}/holdings")
    public ResponseEntity<List<HoldingDto>> getHoldingsRest(@PathVariable Long agentId) {
        String name = agentIdentityService.requireAgentName(agentId);
        List<HoldingDto> holdings = accountService.getHoldings(name);
        return ResponseEntity.ok(holdings);
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
    public ResponseEntity<TradeResult> executeTrade(
            @PathVariable Long agentId,
            @Valid @RequestBody TradeRequest request) {
        String name = agentIdentityService.requireAgentName(agentId);
        TradeResult result;

        if (request.getType() == TradeType.BUY) {
            result = accountService.buyShares(name, request.getSymbol(), request.getQuantity(), request.getRunId());
        } else {
            result = accountService.sellShares(name, request.getSymbol(), request.getQuantity(), request.getRunId());
        }

        return ResponseEntity.status(201).body(result);
    }

    /**
     * Update agent activity timestamp (REST endpoint).
     * PUT /api/accounts/{agentId}/activity
     *
     * @param agentId agent ID from path
     * @return 204 No Content
     */
    @PutMapping("/{agentId}/activity")
    public ResponseEntity<Void> updateActivityRest(@PathVariable Long agentId) {
        String name = agentIdentityService.requireAgentName(agentId);
        accountService.updateAgentActivity(name);
        return ResponseEntity.noContent().build();
    }

    // MCP Resource endpoints
    @GetMapping("/resources/accounts/{agentId}")
    public ResponseEntity<AccountReportDto> getAccountResource(@PathVariable Long agentId) {
        String name = agentIdentityService.requireAgentName(agentId);
        AccountReportDto accountReport = accountService.getAccountReport(name);
        return ResponseEntity.ok(accountReport);
    }

    // strategy resource endpoint removed - using hardcoded strategies only

    // Portfolio history endpoint for charts
    @GetMapping("/portfolio/{agentId}/history")
    public ResponseEntity<List<PortfolioHistoryPoint>> getPortfolioHistory(
            @PathVariable Long agentId,
            @RequestParam(defaultValue = "7") int days) {
        String agentName = agentIdentityService.requireAgentName(agentId);

        // Use Instant (not LocalDateTime) to match entity field type
        Instant fromDate = Instant.now().minus(days, java.time.temporal.ChronoUnit.DAYS);
        List<AccountPortfolioSnapshot> snapshots = snapshotRepository
                .getPortfolioPerformance(agentName, fromDate);

        // Convert to simple DTO
        List<PortfolioHistoryPoint> history = snapshots.stream()
                .map(s -> new PortfolioHistoryPoint(s.getTimestamp(), s.getTotalValue()))
                .collect(Collectors.toList());

        // Return empty list if no snapshots found (not an error)
        return ResponseEntity.ok(history);
    }

    // Recent trades endpoint for trade log
    @GetMapping("/trades/recent")
    public ResponseEntity<List<RecentTradeDto>> getRecentTrades(
            @RequestParam(defaultValue = "20") int limit) {
        // Get recent transactions using optimized query (no findAll())
        List<AccountTransaction> transactions = transactionRepository.findRecentTransactions(limit);

        // Convert to DTOs
        List<RecentTradeDto> recentTrades = transactions.stream()
                .map(t -> new RecentTradeDto(
                        t.getId(),
                        t.getAccount().getAgent().getName(),
                        t.getTransactionType().name(),  // Convert enum to string
                        t.getSymbol(),
                        Math.abs(t.getQuantity()), // Always show positive quantity
                        t.getPrice(),
                        t.getTotalAmount(),
                        t.getTimestamp()
                ))
                .collect(Collectors.toList());

        return ResponseEntity.ok(recentTrades);
    }

    // Trade detail endpoint
    @GetMapping("/trades/{tradeId}")
    public ResponseEntity<TradeDetailResponse> getTradeDetail(@PathVariable Long tradeId) {
        // Get the transaction
        AccountTransaction transaction = transactionRepository.findById(tradeId)
                .orElseThrow(() -> new ResourceNotFoundException("Trade not found"));

        // Build trade info
        TradeDetailResponse.TradeInfo tradeInfo = new TradeDetailResponse.TradeInfo(
                transaction.getId(),
                transaction.getAccount().getAgent().getName(),
                transaction.getTransactionType().name(),  // Convert enum to string
                transaction.getSymbol(),
                Math.abs(transaction.getQuantity()),
                transaction.getPrice(),
                transaction.getTotalAmount(),
                transaction.getTimestamp()
        );

        // Get related trades using optimized query (no findAll())
        List<TradeDetailResponse.RelatedTrade> relatedTrades = transactionRepository
                .findRelatedTrades(
                    transaction.getAccount().getId(),
                    transaction.getSymbol(),
                    tradeId
                )
                .stream()
                .limit(5)  // Limit to 5 related trades
                .map(t -> new TradeDetailResponse.RelatedTrade(
                        t.getId(),
                        t.getTransactionType().name(),  // Convert enum to string
                        Math.abs(t.getQuantity()),
                        t.getPrice(),
                        t.getTimestamp()
                ))
                .collect(Collectors.toList());

        // Get run info and reasoning steps if available
        Long runId = null;
        String runSummary = null;
        String summary = null;
        String fullReasoning = null;
        String researchSources = null;
        String historicalContext = null;
        List<RunDetailDto.ReasoningStepInfo> reasoningSteps = null;

        if (transaction.getAgentRun() != null) {
            AgentRun run = transaction.getAgentRun();
            runId = run.getId();
            runSummary = run.getSummary();
            summary = run.getSummary();
            fullReasoning = run.getFullReasoning();
            researchSources = run.getResearchSources();
            historicalContext = run.getHistoricalContext();

            // Fetch reasoning steps from the run
            reasoningSteps = reasoningStepRepository
                    .findByAgentRunIdOrderBySequenceNumberAsc(runId)
                    .stream()
                    .map(RunDetailDto.ReasoningStepInfo::fromEntity)
                    .collect(Collectors.toList());
        }

        // Build response
        TradeDetailResponse response = new TradeDetailResponse(
                tradeInfo,
                summary,
                fullReasoning,
                researchSources,
                historicalContext,
                relatedTrades,
                runId,
                runSummary,
                reasoningSteps
        );

        return ResponseEntity.ok(response);
    }

    // ==================== RUN HISTORY ENDPOINTS (agent context) ====================

    /**
     * Get complete trading history for a specific stock.
     * GET /api/accounts/{agentId}/runs/trading-history?symbol=NVDA&days=30
     */
    @GetMapping("/{agentId}/runs/trading-history")
    public ResponseEntity<?> getTradingHistory(
            @PathVariable Long agentId,
            @RequestParam String symbol,
            @RequestParam(defaultValue = "30") int days) {
        try {
            String agentName = agentIdentityService.requireAgentName(agentId);
            TradingHistoryResponse history = memoryService.getTradingHistory(agentName, symbol, days);
            if (history == null) {
                return ResponseEntity.status(404).body(
                    Map.of("error", "No trading history found for " + symbol + " in the last " + days + " days")
                );
            }
            return ResponseEntity.ok(history);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(
                Map.of("error", "Failed to retrieve trading history: " + e.getMessage())
            );
        }
    }

    /**
     * Get recent trading activity across all stocks.
     * GET /api/accounts/{agentId}/runs/recent-activity?days=7
     */
    @GetMapping("/{agentId}/runs/recent-activity")
    public ResponseEntity<?> getRecentActivity(
            @PathVariable Long agentId,
            @RequestParam(defaultValue = "7") int days) {
        try {
            String agentName = agentIdentityService.requireAgentName(agentId);
            RecentActivityResponse activity = memoryService.getRecentActivity(agentName, days);
            if (activity == null) {
                return ResponseEntity.status(404).body(
                    Map.of("error", "No recent activity found for agent in the last " + days + " days")
                );
            }
            return ResponseEntity.ok(activity);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(
                Map.of("error", "Failed to retrieve recent activity: " + e.getMessage())
            );
        }
    }
}
