package com.trading.service;

import com.trading.entity.*;
import com.trading.repository.*;
import com.trading.service.TradingService.AgentStatusResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
public class PostgreSQLAgentMonitoringService {
    
    @Autowired
    private TradingAccountRepository tradingAccountRepository;
    
    @Autowired
    private TradingAgentRepository agentRepository;
    
    @Autowired
    private AccountTransactionRepository transactionRepository;
    
    @Autowired
    private AccountHoldingRepository holdingRepository;
    
    @Autowired
    private LogRepository logRepository;
    
    private static final List<String> AGENT_NAMES = Arrays.asList("warren", "george", "ray", "cathie");
    
    /**
     * Get real agent statuses from PostgreSQL database (normalized entities)
     */
    public List<AgentStatusResponse> getRealAgentStatuses() {
        return AGENT_NAMES.stream()
            .map(this::getRealAgentStatus)
            .collect(Collectors.toList());
    }
    
    /**
     * Get real agent status from PostgreSQL database using normalized entities
     */
    public AgentStatusResponse getRealAgentStatus(String agentName) {
        TradingAccount account = tradingAccountRepository.findByName(agentName.toLowerCase());
        
        if (account != null) {
            TradingAgent agent = account.getAgent();
            
            // Get transaction count
            Long totalTrades = transactionRepository.countByAccount(account);
            
            // Calculate portfolio value
            List<AccountHolding> holdings = holdingRepository.findByAccount(account);
            double holdingsValue = holdings.stream()
                .mapToDouble(h -> h.getQuantity() * h.getCurrentPrice())
                .sum();
            double portfolioValue = account.getBalance() + holdingsValue;
            
            // Calculate day P&L (simplified - could be enhanced with time-based queries)
            double initialValue = 100000.0; // Default initial balance
            double dayPnL = portfolioValue - initialValue;
            double dayPnLPercent = portfolioValue > 0 ? (dayPnL / initialValue) * 100 : 0.0;
            
            // Get current positions count
            int currentPositions = (int) holdings.stream()
                .filter(h -> h.getQuantity() > 0)
                .count();
            
            // Get success rate from agent if available
            double successRate = agent != null && agent.getWinRate() != null ? 
                agent.getWinRate() / 100.0 : 0.85; // Default success rate
            
            // Get last activity from agent
            String lastActivity = agent != null && agent.getLastActivity() != null ?
                agent.getLastActivity().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME) :
                LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
            
            return new AgentStatusResponse(
                capitalizeFirst(agentName),
                account.getIsActive(),
                lastActivity,
                totalTrades.intValue(),
                successRate,
                portfolioValue,
                dayPnL,
                dayPnLPercent,
                currentPositions
            );
        } else {
            // Return inactive status if no account found
            return new AgentStatusResponse(
                capitalizeFirst(agentName),
                false,
                LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
                0,
                0.0,
                100000.0, // Initial balance
                0.0,
                0.0,
                0
            );
        }
    }
    
    /**
     * Get recent activity logs for an agent
     */
    public List<String> getAgentLogs(String agentName, int limit) {
        // Get log entries and convert to strings
        List<LogEntry> logEntries = logRepository.findTopByNameOrderByDatetimeDesc(agentName.toLowerCase(), limit);
        return logEntries.stream()
            .map(log -> String.format("[%s] %s: %s",
                log.getDatetime().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
                log.getLogLevel(),
                log.getMessage()))
            .collect(Collectors.toList());
    }
    
    /**
     * Check if Python trading system is running
     */
    public boolean isPythonTradingSystemActive() {
        // Check if any agent has recent transactions (within last hour)
        LocalDateTime oneHourAgo = LocalDateTime.now().minusHours(1);
        
        return AGENT_NAMES.stream()
            .anyMatch(name -> {
                TradingAccount account = tradingAccountRepository.findByName(name);
                if (account != null) {
                    List<AccountTransaction> recentTransactions = transactionRepository
                        .findByAccountOrderByTimestampDesc(account)
                        .stream()
                        .filter(t -> t.getTimestamp().isAfter(oneHourAgo))
                        .limit(1)
                        .collect(Collectors.toList());
                    return !recentTransactions.isEmpty();
                }
                return false;
            });
    }
    
    /**
     * Get agent performance metrics
     */
    public AgentPerformanceMetrics getAgentPerformanceMetrics(String agentName) {
        TradingAccount account = tradingAccountRepository.findByName(agentName.toLowerCase());
        
        if (account != null) {
            TradingAgent agent = account.getAgent();
            
            // Get all transactions for analysis
            List<AccountTransaction> transactions = transactionRepository.findByAccountOrderByTimestampDesc(account);
            
            // Calculate metrics
            long totalTrades = transactions.size();
            double totalVolume = transactions.stream()
                .mapToDouble(t -> t.getQuantity() * t.getPrice())
                .sum();
            
            // Get current portfolio value
            List<AccountHolding> holdings = holdingRepository.findByAccount(account);
            double holdingsValue = holdings.stream()
                .mapToDouble(h -> h.getQuantity() * h.getCurrentPrice())
                .sum();
            double portfolioValue = account.getBalance() + holdingsValue;
            
            return new AgentPerformanceMetrics(
                agentName,
                totalTrades,
                agent != null ? agent.getWinRate() : 0.0,
                portfolioValue,
                agent != null ? agent.getTotalPnl() : 0.0,
                totalVolume,
                holdings.size(),
                agent != null ? agent.getLastActivity() : null
            );
        }
        
        return null;
    }
    
    private String capitalizeFirst(String str) {
        if (str == null || str.isEmpty()) {
            return str;
        }
        return str.substring(0, 1).toUpperCase() + str.substring(1).toLowerCase();
    }
    
    /**
     * Performance metrics data class
     */
    public static class AgentPerformanceMetrics {
        private String agentName;
        private long totalTrades;
        private double winRate;
        private double portfolioValue;
        private double totalPnl;
        private double totalVolume;
        private int currentPositions;
        private LocalDateTime lastActivity;
        
        public AgentPerformanceMetrics(String agentName, long totalTrades, double winRate, 
                                     double portfolioValue, double totalPnl, double totalVolume,
                                     int currentPositions, LocalDateTime lastActivity) {
            this.agentName = agentName;
            this.totalTrades = totalTrades;
            this.winRate = winRate;
            this.portfolioValue = portfolioValue;
            this.totalPnl = totalPnl;
            this.totalVolume = totalVolume;
            this.currentPositions = currentPositions;
            this.lastActivity = lastActivity;
        }
        
        // Getters
        public String getAgentName() { return agentName; }
        public long getTotalTrades() { return totalTrades; }
        public double getWinRate() { return winRate; }
        public double getPortfolioValue() { return portfolioValue; }
        public double getTotalPnl() { return totalPnl; }
        public double getTotalVolume() { return totalVolume; }
        public int getCurrentPositions() { return currentPositions; }
        public LocalDateTime getLastActivity() { return lastActivity; }
    }
}