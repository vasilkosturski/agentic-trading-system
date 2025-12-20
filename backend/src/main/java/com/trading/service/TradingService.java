package com.trading.service;

import com.trading.dto.response.AgentTradeResponse;
import com.trading.dto.response.TradingStatsResponse;
import com.trading.entity.AccountTransaction;
import com.trading.entity.AgentRun;
import com.trading.entity.TransactionType;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.AgentRunRepository;
import com.trading.repository.TradingAccountRepository;
import com.trading.repository.TradingAgentRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class TradingService {
    
    private final AccountTransactionRepository transactionRepository;
    private final TradingAccountRepository accountRepository;
    private final TradingAgentRepository agentRepository;
    private final AgentRunRepository agentRunRepository;
    
    public TradingService(
            AccountTransactionRepository transactionRepository,
            TradingAccountRepository accountRepository,
            TradingAgentRepository agentRepository,
            AgentRunRepository agentRunRepository) {
        this.transactionRepository = transactionRepository;
        this.accountRepository = accountRepository;
        this.agentRepository = agentRepository;
        this.agentRunRepository = agentRunRepository;
    }
    
    /**
     * Record a new trade in the database and update agent statistics
     * NOTE: This method appears to be legacy/unused. All trades should go through AccountService.buyShares/sellShares
     * which require runId. If this method is needed, it must provide a runId.
     * 
     * @param runId REQUIRED - Every transaction must be linked to an agent run
     */
    @Transactional
    public AccountTransaction recordTrade(String agentName, String symbol, Integer quantity,
                                        Double price, Long runId) {
        if (runId == null) {
            throw new IllegalArgumentException("runId is required - every transaction must be linked to an agent run");
        }
        
        // Find the trading account for this agent
        TradingAccount account = accountRepository.findByAgentName(agentName)
            .orElseThrow(() -> new RuntimeException("Trading account not found for agent: " + agentName));
        
        // Create and save the transaction
        AccountTransaction transaction = new AccountTransaction(
            account, symbol, quantity, price, Instant.now()
        );
        // Must set transaction type explicitly (not derived from quantity sign)
        transaction.setTransactionType(quantity > 0 ? TransactionType.BUY : TransactionType.SELL);
        
        // Link transaction to agent run (REQUIRED)
        AgentRun agentRun = agentRunRepository.findById(runId)
            .orElseThrow(() -> new RuntimeException("Agent run not found: " + runId));
        transaction.setAgentRun(agentRun);
        
        transaction = transactionRepository.save(transaction);
        
        // Update agent statistics
        updateAgentTradeStatistics(agentName);
        
        return transaction;
    }
    
    /**
     * Update agent trade statistics based on actual database transactions
     */
    @Transactional
    public void updateAgentTradeStatistics(String agentName) {
        TradingAgent agent = agentRepository.findByName(agentName)
            .orElseThrow(() -> new RuntimeException("Agent not found: " + agentName));

        // Get all transactions for this agent
        List<AccountTransaction> transactions = transactionRepository.findByAgentNameOrderByTransactionDateDesc(agentName);

        // Calculate statistics
        int totalTrades = transactions.size();

        // Update agent entity
        agent.setTotalTrades(totalTrades);
        agent.updateActivity();

        agentRepository.save(agent);
    }
    
    /**
     * Update all agent statistics (useful for initialization or batch updates)
     */
    @Transactional
    public void updateAllAgentStatistics() {
        List<TradingAgent> agents = agentRepository.findAll();
        for (TradingAgent agent : agents) {
            updateAgentTradeStatistics(agent.getName());
        }
    }
    
    // Agent Trades Operations - Now using real database data
    public List<AgentTradeResponse> getAgentTrades(String agentName) {
        List<AccountTransaction> transactions;
        if (agentName != null) {
            transactions = transactionRepository.findByAgentNameOrderByTransactionDateDesc(agentName);
        } else {
            transactions = transactionRepository.findAll();
            transactions.sort((a, b) -> b.getTimestamp().compareTo(a.getTimestamp()));
        }
        
        return transactions.stream()
            .map(this::convertTransactionToTradeResponse)
            .collect(Collectors.toList());
    }
    
    public List<AgentTradeResponse> getRecentActivity(int limit) {
        List<AccountTransaction> transactions = transactionRepository.findAll();
        return transactions.stream()
            .sorted((a, b) -> b.getTimestamp().compareTo(a.getTimestamp()))
            .limit(limit)
            .map(this::convertTransactionToTradeResponse)
            .collect(Collectors.toList());
    }
    
    // Trading Statistics - Now using real database data
    public TradingStatsResponse getTradingStats(String accountId, String agentName) {
        List<AccountTransaction> transactions;
        
        if (agentName != null) {
            transactions = transactionRepository.findByAgentNameOrderByTransactionDateDesc(agentName);
        } else if (accountId != null) {
            TradingAccount account = accountRepository.findByAgentName(accountId)
                .orElseThrow(() -> new RuntimeException("Account not found: " + accountId));
            transactions = transactionRepository.findByAccountOrderByTimestampDesc(account);
        } else {
            transactions = transactionRepository.findAll();
        }
        
        int totalTrades = transactions.size();
        double totalVolume = transactions.stream()
            .mapToDouble(t -> Math.abs(t.getQuantity()) * t.getPrice())
            .sum();

        double averageTradeSize = totalTrades > 0 ? totalVolume / totalTrades : 0.0;

        // Calculate P&L (simplified - would need more complex logic for real P&L calculation)
        double totalPnL = 0.0; // This would require market data and position tracking
        double largestWin = 0.0;
        double largestLoss = 0.0;

        return new TradingStatsResponse(totalTrades, totalVolume,
            totalPnL, averageTradeSize, largestWin, largestLoss);
    }
    
    /**
     * Convert AccountTransaction to AgentTradeResponse for API responses
     */
    private AgentTradeResponse convertTransactionToTradeResponse(AccountTransaction transaction) {
        return new AgentTradeResponse(
            transaction.getId().toString(),
            transaction.getAccount().getAgent().getName(),
            transaction.getAccount().getAgent().getName(),
            transaction.getSymbol(),
            transaction.getTransactionType().name(),  // Convert enum to string for API
            Math.abs(transaction.getQuantity()),
            transaction.getPrice(),
            null, // Rationale is now stored in AgentRun, not AccountTransaction
            1.0, // Default confidence for database transactions
            transaction.getTimestamp().toString(), // Instant to ISO-8601 string
            "EXECUTED", // All database transactions are considered executed
            "N/A" // Order ID not tracked in current schema
        );
    }
}
