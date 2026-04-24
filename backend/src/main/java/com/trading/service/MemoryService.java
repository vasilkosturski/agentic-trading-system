package com.trading.service;

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
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.TradingAccountRepository;
import com.trading.repository.TradingAgentRepository;
import com.trading.repository.TradingRunRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Service for providing memory/context to agents about their past decisions.
 * Returns DTOs that Jackson serializes to JSON.
 */
@Service
public class MemoryService {

    @Value("${trading.public-display-delay-days:7}")
    private int publicDisplayDelayDays;

    @Autowired
    private AccountTransactionRepository transactionRepository;

    @Autowired
    private TradingRunRepository tradingRunRepository;

    @Autowired
    private TradingAgentRepository tradingAgentRepository;

    @Autowired
    private TradingAccountRepository accountRepository;

    @Autowired
    private AccountService accountService;

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
        TradingAccount account = accountRepository.findByAgentName(agentName)
            .orElseThrow(() -> new IllegalArgumentException("Agent not found: " + agentName));

        Instant since = Instant.now().minus(days, ChronoUnit.DAYS);
        Instant cutoffDate = Instant.now().minus(publicDisplayDelayDays, ChronoUnit.DAYS);

        // Get all transactions for this symbol, filtered by delay period
        List<AccountTransaction> transactions = transactionRepository
                .findByAccountIdAndSymbolOrderByTimestampDesc(account.getId(), symbol)
                .stream()
                .filter(t -> t.getTimestamp().isAfter(since))
                .filter(t -> t.getTimestamp().isBefore(cutoffDate))
                .collect(Collectors.toList());

        // Return empty response — "no history" is valid data, not an error
        if (transactions.isEmpty()) {
            TradingHistoryResponse response = new TradingHistoryResponse();
            response.setSymbol(symbol);
            response.setAgentName(agentName);
            response.setDays(days);
            response.setCurrentPosition(new TradingHistoryResponse.Position(0, 0.0));
            response.setTrades(List.of());
            TradingHistoryResponse.Summary emptySummary = new TradingHistoryResponse.Summary();
            emptySummary.setTotalTrades(0);
            emptySummary.setBuys(0);
            emptySummary.setSells(0);
            emptySummary.setPattern("none");
            response.setSummary(emptySummary);
            return response;
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
        TradingAgent agent = tradingAgentRepository.findByName(agentName)
            .orElse(null);

        // If agent not found in new system, return empty response
        if (agent == null) {
            RecentActivityResponse response = new RecentActivityResponse();
            response.setAgentName(agentName);
            response.setDays(days);
            response.setRuns(List.of());
            response.setTotalRuns(0);
            response.setTotalTrades(0);
            return response;
        }

        Instant since = Instant.now().minus(days, ChronoUnit.DAYS);
        Instant cutoffDate = Instant.now().minus(publicDisplayDelayDays, ChronoUnit.DAYS);

        // Get recent runs from the new TradingRun system, filtered by delay period
        List<TradingRun> recentRuns = tradingRunRepository
                .findByAgentIdOrderByStartedAtDesc(agent.getId())
                .stream()
                .filter(r -> r.getStartedAt().isAfter(since))
                .filter(r -> r.getStartedAt().isBefore(cutoffDate))
                .limit(20)  // Limit to last 20 runs
                .collect(Collectors.toList());

        // Return empty response — "no activity" is valid data, not an error
        if (recentRuns.isEmpty()) {
            RecentActivityResponse response = new RecentActivityResponse();
            response.setAgentName(agentName);
            response.setDays(days);
            response.setRuns(List.of());
            response.setTotalRuns(0);
            response.setTotalTrades(0);
            return response;
        }

        // Build response DTO from TradingRun data
        return buildRecentActivityResponse(agentName, days, recentRuns);
    }

    /**
     * Build trading history response DTO
     */
    private TradingHistoryResponse buildTradingHistoryResponse(
            String agentName,
            String symbol,
            int days,
            List<AccountTransaction> transactions,
            TradingAccount account) {

        TradingHistoryResponse response = new TradingHistoryResponse();
        response.setSymbol(symbol);
        response.setAgentName(agentName);
        response.setDays(days);

        // Current position
        try {
            List<HoldingDto> holdings = accountService.getHoldings(agentName);
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
                response.setCurrentPosition(new TradingHistoryResponse.Position(
                    currentShares,
                    Math.round(avgCost * 100.0) / 100.0
                ));
            }
        } catch (Exception e) {
            // Leave currentPosition as null
        }

        // Trades
        List<TradingHistoryResponse.Trade> trades = new ArrayList<>();
        for (AccountTransaction t : transactions) {
            TradingHistoryResponse.Trade trade = new TradingHistoryResponse.Trade();
            trade.setDate(t.getTimestamp().toString());
            trade.setType(t.getTransactionType().name());  // Convert enum to string
            trade.setQuantity(Math.abs(t.getQuantity()));
            trade.setPrice(Math.round(t.getPrice() * 100.0) / 100.0);
            trade.setTotalAmount(Math.round(Math.abs(t.getTotalAmount()) * 100.0) / 100.0);
            // Rationale is now stored in DecisionPhase, not AccountTransaction
            // Access it via run detail endpoint if needed
            trades.add(trade);
        }
        response.setTrades(trades);

        // Summary
        long buyCount = transactions.stream().filter(t -> TransactionType.BUY.equals(t.getTransactionType())).count();
        long sellCount = transactions.stream().filter(t -> TransactionType.SELL.equals(t.getTransactionType())).count();

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
            if (decision != null) {
                if (decision.getReasoning() != null) {
                    String reasoningSummary = decision.getReasoning().getResearchContext();
                    if (reasoningSummary != null && !reasoningSummary.isEmpty()) {
                        runDto.setSummary(reasoningSummary);
                    }
                }
            }

            // Extract trade info from ExecutionPhase if available
            ExecutionPhase execution = run.getExecution();
            if (execution != null && execution.getTrade() != null) {
                AccountTransaction trade = execution.getTrade();
                List<RecentActivityResponse.Trade> trades = new ArrayList<>();
                RecentActivityResponse.Trade tradeDto = new RecentActivityResponse.Trade();
                tradeDto.setType(trade.getTransactionType().name());
                tradeDto.setSymbol(trade.getSymbol());
                tradeDto.setQuantity(Math.abs(trade.getQuantity()));
                tradeDto.setPrice(Math.round(trade.getPrice() * 100.0) / 100.0);
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
