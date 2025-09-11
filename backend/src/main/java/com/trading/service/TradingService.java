package com.trading.service;

import org.springframework.stereotype.Service;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Service
public class TradingService {
    
    // Mock data for trades and orders (agent status now comes from PostgreSQL)
    private static final String[] AGENT_NAMES = {"Warren", "George", "Ray", "Cathie"};
    private final List<AgentTradeData> agentTrades = new ArrayList<>();
    private final List<TradeOrderData> orders = new ArrayList<>();
    
    public TradingService() {
        initializeMockData();
    }
    
    private void initializeMockData() {
        // Initialize some mock trades
        agentTrades.add(new AgentTradeData("1", "Warren", "acc_warren", "AAPL", "BUY", 100, 185.50, 
            "Strong fundamentals and undervalued", 0.85, LocalDateTime.now().minusMinutes(10), "EXECUTED", "order_1"));
        agentTrades.add(new AgentTradeData("2", "George", "acc_george", "SPY", "SELL", 50, 445.20, 
            "Market overheated, taking profits", 0.78, LocalDateTime.now().minusMinutes(8), "EXECUTED", "order_2"));
        agentTrades.add(new AgentTradeData("3", "Cathie", "acc_cathie", "TSLA", "BUY", 25, 248.90, 
            "Innovation cycle acceleration", 0.92, LocalDateTime.now().minusMinutes(5), "EXECUTED", "order_3"));
        
        // Initialize some mock orders
        orders.add(new TradeOrderData("order_1", "acc_warren", "AAPL", "BUY", "MARKET", 100, null, null, 
            "GTC", "FILLED", 100, 185.50, LocalDateTime.now().minusMinutes(10), LocalDateTime.now().minusMinutes(10), "Warren"));
        orders.add(new TradeOrderData("order_2", "acc_george", "SPY", "SELL", "LIMIT", 50, 445.20, null, 
            "DAY", "FILLED", 50, 445.20, LocalDateTime.now().minusMinutes(8), LocalDateTime.now().minusMinutes(8), "George"));
        orders.add(new TradeOrderData("order_3", "acc_cathie", "TSLA", "BUY", "MARKET", 25, null, null, 
            "GTC", "FILLED", 25, 248.90, LocalDateTime.now().minusMinutes(5), LocalDateTime.now().minusMinutes(5), "Cathie"));
    }
    
    // Agent Status Operations - REMOVED: Now handled by PostgreSQLAgentMonitoringService
    // These methods have been moved to use real database data instead of mock data
    
    // Agent control operations - REMOVED: These should be handled by PostgreSQLAgentMonitoringService
    // or moved to a dedicated agent management service that updates the database directly
    
    // Order Operations
    public List<TradeOrderResponse> getOrders(String accountId) {
        return orders.stream()
            .filter(order -> accountId == null || order.getAccountId().equals(accountId))
            .map(this::convertToOrderResponse)
            .toList();
    }
    
    public TradeOrderResponse getOrder(String orderId) {
        return orders.stream()
            .filter(order -> order.getId().equals(orderId))
            .findFirst()
            .map(this::convertToOrderResponse)
            .orElseThrow(() -> new RuntimeException("Order not found: " + orderId));
    }
    
    public TradeOrderResponse createOrder(CreateOrderRequest request) {
        String orderId = "order_" + System.currentTimeMillis();
        TradeOrderData order = new TradeOrderData(
            orderId, request.getAccountId(), request.getSymbol(), request.getType(), 
            request.getOrderType(), request.getQuantity(), request.getPrice(), request.getStopPrice(),
            request.getTimeInForce() != null ? request.getTimeInForce() : "DAY", 
            "PENDING", 0, 0.0, LocalDateTime.now(), LocalDateTime.now(), request.getAgentId()
        );
        orders.add(order);
        return convertToOrderResponse(order);
    }
    
    public void cancelOrder(String orderId) {
        orders.stream()
            .filter(order -> order.getId().equals(orderId))
            .findFirst()
            .ifPresentOrElse(
                order -> order.setStatus("CANCELLED"),
                () -> { throw new RuntimeException("Order not found: " + orderId); }
            );
    }
    
    // Agent Trades Operations
    public List<AgentTradeResponse> getAgentTrades(String agentName) {
        return agentTrades.stream()
            .filter(trade -> agentName == null || trade.getAgentName().equals(agentName))
            .map(this::convertToTradeResponse)
            .toList();
    }
    
    public List<AgentTradeResponse> getRecentActivity(int limit) {
        return agentTrades.stream()
            .sorted((a, b) -> b.getTimestamp().compareTo(a.getTimestamp()))
            .limit(limit)
            .map(this::convertToTradeResponse)
            .toList();
    }
    
    // Trading Statistics
    public TradingStatsResponse getTradingStats(String accountId, String agentName) {
        List<AgentTradeData> filteredTrades = agentTrades.stream()
            .filter(trade -> (accountId == null || trade.getAccountId().equals(accountId)) &&
                           (agentName == null || trade.getAgentName().equals(agentName)))
            .toList();
        
        int totalTrades = filteredTrades.size();
        int successfulTrades = (int) filteredTrades.stream().filter(t -> "EXECUTED".equals(t.getStatus())).count();
        int failedTrades = totalTrades - successfulTrades;
        double totalVolume = filteredTrades.stream().mapToDouble(t -> t.getQuantity() * t.getPrice()).sum();
        
        return new TradingStatsResponse(totalTrades, successfulTrades, failedTrades, totalVolume, 
            2500.0, successfulTrades > 0 ? (double) successfulTrades / totalTrades : 0.0, 
            totalTrades > 0 ? totalVolume / totalTrades : 0.0, 5000.0, -1500.0);
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
    
    private TradeOrderResponse convertToOrderResponse(TradeOrderData order) {
        return new TradeOrderResponse(
            order.getId(), order.getAccountId(), order.getSymbol(), order.getType(),
            order.getOrderType(), order.getQuantity(), order.getPrice(), order.getStopPrice(),
            order.getTimeInForce(), order.getStatus(), order.getFilledQuantity(),
            order.getAverageFillPrice(), order.getCreatedAt().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
            order.getUpdatedAt().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME), order.getAgentId()
        );
    }
    
    private AgentTradeResponse convertToTradeResponse(AgentTradeData trade) {
        return new AgentTradeResponse(
            trade.getId(), trade.getAgentName(), trade.getAccountId(), trade.getSymbol(),
            trade.getType(), trade.getQuantity(), trade.getPrice(), trade.getReasoning(),
            trade.getConfidence(), trade.getTimestamp().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
            trade.getStatus(), trade.getOrderId()
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
    
    private static class AgentTradeData {
        private String id, agentName, accountId, symbol, type, reasoning, status, orderId;
        private int quantity;
        private double price, confidence;
        private LocalDateTime timestamp;
        
        public AgentTradeData(String id, String agentName, String accountId, String symbol, String type,
                             int quantity, double price, String reasoning, double confidence, 
                             LocalDateTime timestamp, String status, String orderId) {
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
        public LocalDateTime getTimestamp() { return timestamp; }
        public String getStatus() { return status; }
        public String getOrderId() { return orderId; }
    }
    
    private static class TradeOrderData {
        private String id, accountId, symbol, type, orderType, timeInForce, status, agentId;
        private int quantity, filledQuantity;
        private Double price, stopPrice;
        private double averageFillPrice;
        private LocalDateTime createdAt, updatedAt;
        
        public TradeOrderData(String id, String accountId, String symbol, String type, String orderType,
                             int quantity, Double price, Double stopPrice, String timeInForce, String status,
                             int filledQuantity, double averageFillPrice, LocalDateTime createdAt, 
                             LocalDateTime updatedAt, String agentId) {
            this.id = id; this.accountId = accountId; this.symbol = symbol; this.type = type;
            this.orderType = orderType; this.quantity = quantity; this.price = price; this.stopPrice = stopPrice;
            this.timeInForce = timeInForce; this.status = status; this.filledQuantity = filledQuantity;
            this.averageFillPrice = averageFillPrice; this.createdAt = createdAt; this.updatedAt = updatedAt;
            this.agentId = agentId;
        }
        
        // Getters and setters
        public String getId() { return id; }
        public String getAccountId() { return accountId; }
        public String getSymbol() { return symbol; }
        public String getType() { return type; }
        public String getOrderType() { return orderType; }
        public int getQuantity() { return quantity; }
        public Double getPrice() { return price; }
        public Double getStopPrice() { return stopPrice; }
        public String getTimeInForce() { return timeInForce; }
        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }
        public int getFilledQuantity() { return filledQuantity; }
        public double getAverageFillPrice() { return averageFillPrice; }
        public LocalDateTime getCreatedAt() { return createdAt; }
        public LocalDateTime getUpdatedAt() { return updatedAt; }
        public String getAgentId() { return agentId; }
    }
    
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
    
    public static class TradeOrderResponse {
        private String id, accountId, symbol, type, orderType, timeInForce, status, createdAt, updatedAt, agentId;
        private int quantity, filledQuantity;
        private Double price, stopPrice;
        private double averageFillPrice;
        
        public TradeOrderResponse(String id, String accountId, String symbol, String type, String orderType,
                                 int quantity, Double price, Double stopPrice, String timeInForce, String status,
                                 int filledQuantity, double averageFillPrice, String createdAt, String updatedAt, String agentId) {
            this.id = id; this.accountId = accountId; this.symbol = symbol; this.type = type;
            this.orderType = orderType; this.quantity = quantity; this.price = price; this.stopPrice = stopPrice;
            this.timeInForce = timeInForce; this.status = status; this.filledQuantity = filledQuantity;
            this.averageFillPrice = averageFillPrice; this.createdAt = createdAt; this.updatedAt = updatedAt;
            this.agentId = agentId;
        }
        
        // Getters
        public String getId() { return id; }
        public String getAccountId() { return accountId; }
        public String getSymbol() { return symbol; }
        public String getType() { return type; }
        public String getOrderType() { return orderType; }
        public int getQuantity() { return quantity; }
        public Double getPrice() { return price; }
        public Double getStopPrice() { return stopPrice; }
        public String getTimeInForce() { return timeInForce; }
        public String getStatus() { return status; }
        public int getFilledQuantity() { return filledQuantity; }
        public double getAverageFillPrice() { return averageFillPrice; }
        public String getCreatedAt() { return createdAt; }
        public String getUpdatedAt() { return updatedAt; }
        public String getAgentId() { return agentId; }
    }
    
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
    
    public static class CreateOrderRequest {
        private String accountId, symbol, type, orderType, timeInForce, agentId;
        private int quantity;
        private Double price, stopPrice;
        
        public CreateOrderRequest() {}
        
        // Getters and setters
        public String getAccountId() { return accountId; }
        public void setAccountId(String accountId) { this.accountId = accountId; }
        public String getSymbol() { return symbol; }
        public void setSymbol(String symbol) { this.symbol = symbol; }
        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
        public String getOrderType() { return orderType; }
        public void setOrderType(String orderType) { this.orderType = orderType; }
        public int getQuantity() { return quantity; }
        public void setQuantity(int quantity) { this.quantity = quantity; }
        public Double getPrice() { return price; }
        public void setPrice(Double price) { this.price = price; }
        public Double getStopPrice() { return stopPrice; }
        public void setStopPrice(Double stopPrice) { this.stopPrice = stopPrice; }
        public String getTimeInForce() { return timeInForce; }
        public void setTimeInForce(String timeInForce) { this.timeInForce = timeInForce; }
        public String getAgentId() { return agentId; }
        public void setAgentId(String agentId) { this.agentId = agentId; }
    }
}