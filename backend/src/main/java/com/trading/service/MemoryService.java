package com.trading.service;

import com.trading.config.TradingPublicProperties;
import com.trading.dto.response.HoldingDto;
import com.trading.dto.response.RecentActivityResponse;
import com.trading.dto.response.TradingHistoryResponse;
import com.trading.entity.AccountTransaction;
import com.trading.entity.DecisionPhase;
import com.trading.entity.ExecutionPhase;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.entity.TradingRun;
import com.trading.entity.TransactionType;
import com.trading.exception.ResourceNotFoundException;
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.TradingAccountRepository;
import com.trading.repository.TradingAgentRepository;
import com.trading.repository.TradingRunRepository;
import com.trading.util.MoneyMath;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Service for providing memory/context to agents about their past decisions.
 * Returns DTOs that Jackson serializes to JSON.
 */
@Service
@Transactional(readOnly = true)
public class MemoryService {

    private final TradingPublicProperties tradingPublicProperties;
    private final AccountTransactionRepository transactionRepository;
    private final TradingRunRepository tradingRunRepository;
    private final TradingAgentRepository tradingAgentRepository;
    private final TradingAccountRepository accountRepository;
    private final AccountQueryService accountQueryService;

    public MemoryService(
            TradingPublicProperties tradingPublicProperties,
            AccountTransactionRepository transactionRepository,
            TradingRunRepository tradingRunRepository,
            TradingAgentRepository tradingAgentRepository,
            TradingAccountRepository accountRepository,
            AccountQueryService accountQueryService) {
        this.tradingPublicProperties = tradingPublicProperties;
        this.transactionRepository = transactionRepository;
        this.tradingRunRepository = tradingRunRepository;
        this.tradingAgentRepository = tradingAgentRepository;
        this.accountRepository = accountRepository;
        this.accountQueryService = accountQueryService;
    }

    /**
     * Get complete trading history for a specific stock
     */
    public TradingHistoryResponse getTradingHistory(String agentName, String symbol, int days) {
        // Validate inputs
        if (agentName == null || agentName.trim().isEmpty()) {
            throw new IllegalArgumentException("Agent name is required");
        }
        if (symbol == null || symbol.trim().isEmpty()) {
            throw new IllegalArgumentException("Symbol is required");
        }
        if (days < 1 || days > 365) {
            throw new IllegalArgumentException("Days must be between 1 and 365");
        }

        // Get account
        TradingAccount account = accountRepository
                .findByAgentName(agentName)
                .orElseThrow(() -> new ResourceNotFoundException("Agent not found: " + agentName));

        Instant since = Instant.now().minus(days, ChronoUnit.DAYS);
        Instant cutoffDate = Instant.now().minus(tradingPublicProperties.getDisplayDelayDays(), ChronoUnit.DAYS);

        // Get transactions for this symbol within the date window — filtered at DB level
        List<AccountTransaction> transactions = transactionRepository.findByAccountIdAndSymbolAndTimestampBetween(
                account.getId(), symbol, since, cutoffDate);

        // Return empty response — "no history" is valid data, not an error
        if (transactions.isEmpty()) {
            return TradingHistoryResponse.empty(symbol, agentName, days);
        }

        // Build response DTO
        return buildTradingHistoryResponse(agentName, symbol, days, transactions, account);
    }

    /**
     * Get recent trading activity across all stocks.
     * Uses TradingRun (new system) to provide run-level context to agents.
     */
    public RecentActivityResponse getRecentActivity(String agentName, int days) {
        // Validate inputs
        if (agentName == null || agentName.trim().isEmpty()) {
            throw new IllegalArgumentException("Agent name is required");
        }
        if (days < 1 || days > 90) {
            throw new IllegalArgumentException("Days must be between 1 and 90");
        }

        // Look up agent to get ID for TradingRun queries
        TradingAgent agent = tradingAgentRepository.findByName(agentName).orElse(null);

        // If agent not found in new system, return empty response
        if (agent == null) {
            return RecentActivityResponse.empty(agentName, days);
        }

        Instant since = Instant.now().minus(days, ChronoUnit.DAYS);
        Instant cutoffDate = Instant.now().minus(tradingPublicProperties.getDisplayDelayDays(), ChronoUnit.DAYS);

        // Get recent runs within the date window — filtered + limited at DB level
        List<TradingRun> recentRuns = tradingRunRepository.findByAgentIdAndStartedAtBetween(
                agent.getId(), since, cutoffDate, PageRequest.of(0, 20));

        // Return empty response — "no activity" is valid data, not an error
        if (recentRuns.isEmpty()) {
            return RecentActivityResponse.empty(agentName, days);
        }

        // Build response DTO from TradingRun data
        return buildRecentActivityResponse(agentName, days, recentRuns);
    }

    /**
     * Build trading history response DTO
     */
    private TradingHistoryResponse buildTradingHistoryResponse(
            String agentName, String symbol, int days, List<AccountTransaction> transactions, TradingAccount account) {

        TradingHistoryResponse response = new TradingHistoryResponse();
        response.setSymbol(symbol);
        response.setAgentName(agentName);
        response.setDays(days);

        // Current position
        List<HoldingDto> holdings = accountQueryService.getHoldings(agentName);
        HoldingDto holding = holdings.stream()
                .filter(h -> symbol.equals(h.getSymbol()))
                .findFirst()
                .orElse(null);
        Integer currentShares = holding != null ? holding.getQuantity() : null;
        if (currentShares != null && currentShares > 0) {
            // Calculate average cost
            double totalCost = 0;
            int totalShares = 0;
            for (AccountTransaction t : transactions) {
                if (TransactionType.BUY.equals(t.getTransactionType())) {
                    totalCost += Math.abs(t.getTotalAmount());
                    totalShares += t.getQuantity();
                }
            }
            double avgCost = totalShares > 0 ? totalCost / totalShares : 0;
            response.setCurrentPosition(new TradingHistoryResponse.Position(currentShares, MoneyMath.round2(avgCost)));
        }

        // Trades
        List<TradingHistoryResponse.Trade> trades = new ArrayList<>();
        for (AccountTransaction t : transactions) {
            TradingHistoryResponse.Trade trade = new TradingHistoryResponse.Trade();
            trade.setDate(t.getTimestamp().toString());
            trade.setType(t.getTransactionType().name()); // Convert enum to string
            trade.setQuantity(Math.abs(t.getQuantity()));
            trade.setPrice(MoneyMath.round2(t.getPrice()));
            trade.setTotalAmount(MoneyMath.round2(Math.abs(t.getTotalAmount())));
            // Rationale is now stored in DecisionPhase, not AccountTransaction
            // Access it via run detail endpoint if needed
            trades.add(trade);
        }
        response.setTrades(trades);

        // Summary
        long buyCount = transactions.stream()
                .filter(t -> TransactionType.BUY.equals(t.getTransactionType()))
                .count();
        long sellCount = transactions.stream()
                .filter(t -> TransactionType.SELL.equals(t.getTransactionType()))
                .count();

        TradingHistoryResponse.Summary summary = new TradingHistoryResponse.Summary();
        summary.setTotalTrades(transactions.size());
        summary.setBuys((int) buyCount);
        summary.setSells((int) sellCount);

        if (buyCount > sellCount) {
            summary.setPattern("accumulating");
        } else if (sellCount > buyCount) {
            summary.setPattern("reducing");
        } else if (transactions.isEmpty()) {
            summary.setPattern("none");
        } else {
            summary.setPattern("mixed");
        }
        response.setSummary(summary);

        return response;
    }

    /**
     * Build recent activity response DTO from TradingRun data.
     * Maps TradingRun + DecisionPhase + ExecutionPhase to the RecentActivityResponse format.
     */
    private RecentActivityResponse buildRecentActivityResponse(String agentName, int days, List<TradingRun> runs) {
        RecentActivityResponse response = new RecentActivityResponse();
        response.setAgentName(agentName);
        response.setDays(days);

        List<RecentActivityResponse.Run> runsList = new ArrayList<>();
        int totalTrades = 0;

        for (TradingRun run : runs) {
            RecentActivityResponse.Run runDto = new RecentActivityResponse.Run();
            runDto.setDate(run.getStartedAt().toString());
            runDto.setOutcome(run.getStatus().name());

            // Extract reasoning from DecisionPhase if available
            DecisionPhase decision = run.getDecision();
            ReasoningSummaryExtractor.extractSummary(decision).ifPresent(runDto::setSummary);

            // Extract trade info from ExecutionPhase if available
            ExecutionPhase execution = run.getExecution();
            if (execution != null && execution.getTrade() != null) {
                AccountTransaction trade = execution.getTrade();
                List<RecentActivityResponse.Trade> trades = new ArrayList<>();
                RecentActivityResponse.Trade tradeDto = new RecentActivityResponse.Trade();
                tradeDto.setType(trade.getTransactionType().name());
                tradeDto.setSymbol(trade.getSymbol());
                tradeDto.setQuantity(Math.abs(trade.getQuantity()));
                tradeDto.setPrice(MoneyMath.round2(trade.getPrice()));
                trades.add(tradeDto);
                runDto.setTrades(trades);
                totalTrades += 1;
            }

            runsList.add(runDto);
        }

        response.setRuns(runsList);
        response.setTotalRuns(runs.size());
        response.setTotalTrades(totalTrades);

        return response;
    }
}
