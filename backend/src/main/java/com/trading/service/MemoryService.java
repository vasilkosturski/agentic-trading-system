package com.trading.service;

import com.trading.dto.response.RecentActivityResponse;
import com.trading.dto.response.TradingHistoryResponse;
import com.trading.entity.AccountTransaction;
import com.trading.entity.AgentRun;
import com.trading.entity.TransactionType;
import com.trading.entity.TradingAccount;
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.AgentRunRepository;
import com.trading.repository.TradingAccountRepository;
import org.springframework.beans.factory.annotation.Autowired;
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

    @Autowired
    private AccountTransactionRepository transactionRepository;

    @Autowired
    private AgentRunRepository runRepository;

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
        TradingAccount account = accountRepository.findByName(agentName);
        if (account == null) {
            throw new IllegalArgumentException("Agent not found: " + agentName);
        }

        Instant since = Instant.now().minus(days, ChronoUnit.DAYS);

        // Get all transactions for this symbol
        List<AccountTransaction> transactions = transactionRepository
                .findByAccountIdAndSymbolOrderByTimestampDesc(account.getId(), symbol)
                .stream()
                .filter(t -> t.getTimestamp().isAfter(since))
                .collect(Collectors.toList());

        // Build response DTO
        return buildTradingHistoryResponse(agentName, symbol, days, transactions, account);
    }

    /**
     * Get recent trading activity across all stocks
     */
    public RecentActivityResponse getRecentActivity(String agentName, int days) {
        // Validate inputs
        if (agentName == null || agentName.trim().isEmpty()) {
            throw new IllegalArgumentException("Agent name is required");
        }
        if (days < 1 || days > 90) {
            throw new IllegalArgumentException("Days must be between 1 and 90");
        }

        Instant since = Instant.now().minus(days, ChronoUnit.DAYS);

        // Get all recent runs
        List<AgentRun> recentRuns = runRepository
                .findByAgentNameOrderByStartTimeDesc(agentName)
                .stream()
                .filter(r -> r.getStartTime().isAfter(since))
                .limit(20)  // Limit to last 20 runs
                .collect(Collectors.toList());

        // Build response DTO
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
            var holdings = accountService.getHoldings(agentName);
            Integer currentShares = holdings.get(symbol);
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
            if (t.getRationale() != null && !t.getRationale().isEmpty()) {
                trade.setRationale(t.getRationale());
            }
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
     * Build recent activity response DTO
     */
    private RecentActivityResponse buildRecentActivityResponse(String agentName, int days, List<AgentRun> runs) {
        RecentActivityResponse response = new RecentActivityResponse();
        response.setAgentName(agentName);
        response.setDays(days);

        List<RecentActivityResponse.Run> runsList = new ArrayList<>();
        int totalTrades = 0;
        
        for (AgentRun run : runs) {
            RecentActivityResponse.Run runDto = new RecentActivityResponse.Run();
            runDto.setDate(run.getStartTime().toString());
            runDto.setOutcome(run.getOutcome());
            
            if (run.getSummary() != null && !run.getSummary().isEmpty()) {
                runDto.setSummary(run.getSummary());
            }
            
            // Get trades for this run
            if (run.getTradeCount() != null && run.getTradeCount() > 0) {
                List<AccountTransaction> runTrades = transactionRepository.findByAgentRunId(run.getId());
                if (!runTrades.isEmpty()) {
                    List<RecentActivityResponse.Trade> trades = new ArrayList<>();
                    for (AccountTransaction t : runTrades) {
                        RecentActivityResponse.Trade trade = new RecentActivityResponse.Trade();
                        trade.setType(t.getTransactionType().name());  // Convert enum to string
                        trade.setSymbol(t.getSymbol());
                        trade.setQuantity(Math.abs(t.getQuantity()));
                        trade.setPrice(Math.round(t.getPrice() * 100.0) / 100.0);
                        if (t.getRationale() != null && !t.getRationale().isEmpty()) {
                            trade.setRationale(t.getRationale());
                        }
                        trades.add(trade);
                    }
                    runDto.setTrades(trades);
                    totalTrades += runTrades.size();
                }
            }
            
            runsList.add(runDto);
        }
        
        response.setRuns(runsList);
        response.setTotalRuns(runs.size());
        response.setTotalTrades(totalTrades);

        return response;
    }
}

