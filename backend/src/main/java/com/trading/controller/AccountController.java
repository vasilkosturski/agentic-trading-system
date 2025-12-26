package com.trading.controller;

import com.trading.dto.request.*;
import com.trading.dto.response.AccountReportDto;
import com.trading.dto.response.HoldingDto;
import com.trading.dto.response.PortfolioHistoryPoint;
import com.trading.dto.response.RecentTradeDto;
import com.trading.dto.response.RunDetailDto;
import com.trading.dto.response.ToolResponse;
import com.trading.dto.response.TradeDetailResponse;
import com.trading.dto.response.TradeResult;
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
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.stream.Collectors;

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

    // Agent initialization endpoint
    @PostMapping("/tools/initialize_agent")
    public ResponseEntity<ToolResponse<String>> initializeAgent(@Valid @RequestBody InitializeAgentRequest request) {
        accountService.initializeAgent(request.getName(), request.getInitialBalance());
        return ResponseEntity.status(201).body(ToolResponse.success(
            "Successfully initialized agent " + request.getName()));
    }

    // MCP Tool endpoints
    @PostMapping("/tools/get_balance")
    public ResponseEntity<ToolResponse<Double>> getBalance(@Valid @RequestBody GetBalanceRequest request) {
        String name = agentIdentityService.requireAgentName(request.getAgentId());
        Double balance = accountService.getBalance(name);
        return ResponseEntity.ok(ToolResponse.success(balance));
    }

    @PostMapping("/tools/get_holdings")
    public ResponseEntity<ToolResponse<List<HoldingDto>>> getHoldings(@Valid @RequestBody GetHoldingsRequest request) {
        String name = agentIdentityService.requireAgentName(request.getAgentId());
        List<HoldingDto> holdings = accountService.getHoldings(name);
        return ResponseEntity.ok(ToolResponse.success(holdings));
    }

    @PostMapping("/tools/buy_shares")
    public ResponseEntity<ToolResponse<TradeResult>> buyShares(@Valid @RequestBody BuySharesRequest request) {
        String name = agentIdentityService.requireAgentName(request.getAgentId());
        TradeResult result = accountService.buyShares(
            name,
            request.getSymbol(),
            request.getQuantity(),
            request.getRunId()
        );
        return ResponseEntity.status(201).body(ToolResponse.success(result));
    }

    @PostMapping("/tools/sell_shares")
    public ResponseEntity<ToolResponse<TradeResult>> sellShares(@Valid @RequestBody SellSharesRequest request) {
        String name = agentIdentityService.requireAgentName(request.getAgentId());
        TradeResult result = accountService.sellShares(
            name,
            request.getSymbol(),
            request.getQuantity(),
            request.getRunId()
        );
        return ResponseEntity.status(201).body(ToolResponse.success(result));
    }

    @PostMapping("/tools/update_activity")
    public ResponseEntity<Void> updateActivity(@Valid @RequestBody UpdateActivityRequest request) {
        String name = agentIdentityService.requireAgentName(request.getAgentId());
        accountService.updateAgentActivity(name);
        return ResponseEntity.noContent().build();  // 204 No Content
    }

    // change_strategy endpoint removed - using hardcoded strategies only

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
}
