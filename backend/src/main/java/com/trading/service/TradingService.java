package com.trading.service;

import com.trading.entity.AccountTransaction;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.TradingAccountRepository;
import com.trading.repository.TradingAgentRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class TradingService {
    
    @Autowired
    private AccountTransactionRepository transactionRepository;
    
    @Autowired
    private TradingAccountRepository accountRepository;
    
    @Autowired
    private TradingAgentRepository agentRepository;
    
    // Constructor - no mock data initialization needed
    public TradingService() {
        // All data now comes from database
    }
    
    /**
     * Record a new trade in the database and update agent statistics
     */
    @Transactional
    public AccountTransaction recordTrade(String agentName, String symbol, Integer quantity,
                                        Double price, String rationale) {
        // Find the trading account for this agent
        TradingAccount account = accountRepository.findByName(agentName);
        if (account == null) {
            throw new RuntimeException("Trading account not found for agent: " + agentName);
        }
        
        // Create and save the transaction
        AccountTransaction transaction = new AccountTransaction(
            account, symbol, quantity, price, LocalDateTime.now(), rationale
        );
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
        int successfulTrades = totalTrades; // For now, assume all recorded trades are successful
        
        // Update agent entity
        agent.setTotalTrades(totalTrades);
        agent.setSuccessfulTrades(successfulTrades);
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
    
    
    // Agent Status Operations - REMOVED: Now handled by PostgreSQLAgentMonitoringService
    // These methods have been moved to use real database data instead of mock data
    
    // Agent control operations - REMOVED: These should be handled by PostgreSQLAgentMonitoringService
    // or moved to a dedicated agent management service that updates the database directly
    
    // Order Operations - REMOVED: Mock order system eliminated
    // Orders are not needed for current functionality as UI only shows completed trades
    // If order management is needed in future, implement with database persistence
    
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
            TradingAccount account = accountRepository.findByName(accountId);
            if (account == null) {
                throw new RuntimeException("Account not found: " + accountId);
            }
            transactions = transactionRepository.findByAccountOrderByTimestampDesc(account);
        } else {
            transactions = transactionRepository.findAll();
        }
        
        int totalTrades = transactions.size();
        int successfulTrades = totalTrades; // All recorded transactions are considered successful
        int failedTrades = 0;
        double totalVolume = transactions.stream()
            .mapToDouble(t -> Math.abs(t.getQuantity()) * t.getPrice())
            .sum();
        
        double winRate = totalTrades > 0 ? 1.0 : 0.0; // 100% for now since all recorded trades are successful
        double averageTradeSize = totalTrades > 0 ? totalVolume / totalTrades : 0.0;
        
        // Calculate P&L (simplified - would need more complex logic for real P&L calculation)
        double totalPnL = 0.0; // This would require market data and position tracking
        double largestWin = 0.0;
        double largestLoss = 0.0;
        
        return new TradingStatsResponse(totalTrades, successfulTrades, failedTrades, totalVolume,
            totalPnL, winRate, averageTradeSize, largestWin, largestLoss);
    }
    
    // Portfolio Performance
    public PortfolioPerformanceResponse getPortfolioPerformance(String accountId, String period) {
        // Mock performance data
        List<String> timestamps = Arrays.asList(
            "2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z", "2024-01-03T00:00:00Z"
        );
        List<Double> values = Arrays.asList(100000.0, 102000.0, 105000.0);
        List<Double> returns = Arrays.asList(0.0, 0.02, 0.0294);
        List<Double> benchmark = Arrays.asList(100000.0, 101500.0, 103000.0);
        
        return new PortfolioPerformanceResponse(timestamps, values, returns, benchmark);
    }
    
    // Risk Metrics
    public RiskMetricsResponse getRiskMetrics(String accountId) {
        return new RiskMetricsResponse(85000.0, 0.15, 1.2, 0.18, 1.05, 5000.0, 7500.0);
    }
    
    // Helper methods
    private AgentStatusResponse convertToAgentStatus(AgentData agent) {
        return new AgentStatusResponse(
            agent.getAgentName(), agent.isActive(), 
            agent.getLastActivity().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
            agent.getTotalTrades(), agent.getSuccessRate(), agent.getPortfolioValue(),
            agent.getDayPnL(), agent.getDayPnLPercent(), agent.getCurrentPositions()
        );
    }
    
    // convertToOrderResponse method removed - no longer needed without mock orders
    
    /**
     * Convert AccountTransaction to AgentTradeResponse for API responses
     */
    private AgentTradeResponse convertTransactionToTradeResponse(AccountTransaction transaction) {
        return new AgentTradeResponse(
            transaction.getId().toString(),
            transaction.getAccount().getAgent().getName(),
            transaction.getAccount().getName(),
            transaction.getSymbol(),
            transaction.getTransactionType(),
            Math.abs(transaction.getQuantity()),
            transaction.getPrice(),
            transaction.getRationale() != null ? transaction.getRationale() : "No rationale provided",
            1.0, // Default confidence for database transactions
            transaction.getTimestamp().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
            "EXECUTED", // All database transactions are considered executed
            "N/A" // Order ID not tracked in current schema
        );
    }
    
    // Data classes
    private static class AgentData {
        private String agentName;
        private boolean isActive;
        private LocalDateTime lastActivity;
        private int totalTrades;
        private double successRate;
        private double portfolioValue;
        private double dayPnL;
        private double dayPnLPercent;
        private int currentPositions;
        
        public AgentData(String agentName, boolean isActive, LocalDateTime lastActivity, int totalTrades,
                        double successRate, double portfolioValue, double dayPnL, double dayPnLPercent, int currentPositions) {
            this.agentName = agentName;
            this.isActive = isActive;
            this.lastActivity = lastActivity;
            this.totalTrades = totalTrades;
            this.successRate = successRate;
            this.portfolioValue = portfolioValue;
            this.dayPnL = dayPnL;
            this.dayPnLPercent = dayPnLPercent;
            this.currentPositions = currentPositions;
        }
        
        // Getters and setters
        public String getAgentName() { return agentName; }
        public boolean isActive() { return isActive; }
        public void setActive(boolean active) { isActive = active; }
        public LocalDateTime getLastActivity() { return lastActivity; }
        public void setLastActivity(LocalDateTime lastActivity) { this.lastActivity = lastActivity; }
        public int getTotalTrades() { return totalTrades; }
        public double getSuccessRate() { return successRate; }
        public double getPortfolioValue() { return portfolioValue; }
        public double getDayPnL() { return dayPnL; }
        public double getDayPnLPercent() { return dayPnLPercent; }
        public int getCurrentPositions() { return currentPositions; }
    }
    
    // AgentTradeData class removed - now using real AccountTransaction entities from database
    
    // TradeOrderData class removed - no longer needed without mock orders
    
    // Response classes
    public static class AgentStatusResponse {
        private String agentName, lastActivity;
        private boolean isActive;
        private int totalTrades, currentPositions;
        private double successRate, portfolioValue, dayPnL, dayPnLPercent;
        
        public AgentStatusResponse(String agentName, boolean isActive, String lastActivity, int totalTrades,
                                  double successRate, double portfolioValue, double dayPnL, double dayPnLPercent, int currentPositions) {
            this.agentName = agentName; this.isActive = isActive; this.lastActivity = lastActivity;
            this.totalTrades = totalTrades; this.successRate = successRate; this.portfolioValue = portfolioValue;
            this.dayPnL = dayPnL; this.dayPnLPercent = dayPnLPercent; this.currentPositions = currentPositions;
        }
        
        // Getters
        public String getAgentName() { return agentName; }
        public boolean isActive() { return isActive; }
        public String getLastActivity() { return lastActivity; }
        public int getTotalTrades() { return totalTrades; }
        public double getSuccessRate() { return successRate; }
        public double getPortfolioValue() { return portfolioValue; }
        public double getDayPnL() { return dayPnL; }
        public double getDayPnLPercent() { return dayPnLPercent; }
        public int getCurrentPositions() { return currentPositions; }
    }
    
    // TradeOrderResponse class removed - no longer needed without mock orders
    
    public static class AgentTradeResponse {
        private String id, agentName, accountId, symbol, type, reasoning, timestamp, status, orderId;
        private int quantity;
        private double price, confidence;
        
        public AgentTradeResponse(String id, String agentName, String accountId, String symbol, String type,
                                 int quantity, double price, String reasoning, double confidence, 
                                 String timestamp, String status, String orderId) {
            this.id = id; this.agentName = agentName; this.accountId = accountId; this.symbol = symbol;
            this.type = type; this.quantity = quantity; this.price = price; this.reasoning = reasoning;
            this.confidence = confidence; this.timestamp = timestamp; this.status = status; this.orderId = orderId;
        }
        
        // Getters
        public String getId() { return id; }
        public String getAgentName() { return agentName; }
        public String getAccountId() { return accountId; }
        public String getSymbol() { return symbol; }
        public String getType() { return type; }
        public int getQuantity() { return quantity; }
        public double getPrice() { return price; }
        public String getReasoning() { return reasoning; }
        public double getConfidence() { return confidence; }
        public String getTimestamp() { return timestamp; }
        public String getStatus() { return status; }
        public String getOrderId() { return orderId; }
    }
    
    public static class TradingStatsResponse {
        private int totalTrades, successfulTrades, failedTrades;
        private double totalVolume, totalPnL, winRate, averageTradeSize, largestWin, largestLoss;
        
        public TradingStatsResponse(int totalTrades, int successfulTrades, int failedTrades, double totalVolume,
                                   double totalPnL, double winRate, double averageTradeSize, double largestWin, double largestLoss) {
            this.totalTrades = totalTrades; this.successfulTrades = successfulTrades; this.failedTrades = failedTrades;
            this.totalVolume = totalVolume; this.totalPnL = totalPnL; this.winRate = winRate;
            this.averageTradeSize = averageTradeSize; this.largestWin = largestWin; this.largestLoss = largestLoss;
        }
        
        // Getters
        public int getTotalTrades() { return totalTrades; }
        public int getSuccessfulTrades() { return successfulTrades; }
        public int getFailedTrades() { return failedTrades; }
        public double getTotalVolume() { return totalVolume; }
        public double getTotalPnL() { return totalPnL; }
        public double getWinRate() { return winRate; }
        public double getAverageTradeSize() { return averageTradeSize; }
        public double getLargestWin() { return largestWin; }
        public double getLargestLoss() { return largestLoss; }
    }
    
    public static class PortfolioPerformanceResponse {
        private List<String> timestamps;
        private List<Double> values, returns, benchmark;
        
        public PortfolioPerformanceResponse(List<String> timestamps, List<Double> values, List<Double> returns, List<Double> benchmark) {
            this.timestamps = timestamps; this.values = values; this.returns = returns; this.benchmark = benchmark;
        }
        
        // Getters
        public List<String> getTimestamps() { return timestamps; }
        public List<Double> getValues() { return values; }
        public List<Double> getReturns() { return returns; }
        public List<Double> getBenchmark() { return benchmark; }
    }
    
    public static class RiskMetricsResponse {
        private double totalExposure, maxDrawdown, sharpeRatio, volatility, beta, var95, expectedShortfall;
        
        public RiskMetricsResponse(double totalExposure, double maxDrawdown, double sharpeRatio, double volatility,
                                  double beta, double var95, double expectedShortfall) {
            this.totalExposure = totalExposure; this.maxDrawdown = maxDrawdown; this.sharpeRatio = sharpeRatio;
            this.volatility = volatility; this.beta = beta; this.var95 = var95; this.expectedShortfall = expectedShortfall;
        }
        
        // Getters
        public double getTotalExposure() { return totalExposure; }
        public double getMaxDrawdown() { return maxDrawdown; }
        public double getSharpeRatio() { return sharpeRatio; }
        public double getVolatility() { return volatility; }
        public double getBeta() { return beta; }
        public double getVar95() { return var95; }
        public double getExpectedShortfall() { return expectedShortfall; }
    }
    
    // CreateOrderRequest class removed - no longer needed without mock orders
}