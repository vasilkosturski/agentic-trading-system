package com.trading.dto.response;

/**
 * Response DTO for agent status information.
 * Extracted from TradingService for better modularity.
 */
public class AgentStatusResponse {
    private Long agentId;
    private String agentName;
    private String lastActivity;
    private boolean isActive;
    private int totalTrades;
    private int currentPositions;
    private int cycleIntervalSeconds;
    private double totalReturnPercent;
    private double portfolioValue;
    private double dayPnL;
    private double dayPnLPercent;

    public AgentStatusResponse(Long agentId, String agentName, boolean isActive, String lastActivity,
                               int totalTrades, double totalReturnPercent, double portfolioValue,
                               double dayPnL, double dayPnLPercent, int currentPositions,
                               int cycleIntervalSeconds) {
        this.agentId = agentId;
        this.agentName = agentName;
        this.isActive = isActive;
        this.lastActivity = lastActivity;
        this.totalTrades = totalTrades;
        this.totalReturnPercent = totalReturnPercent;
        this.portfolioValue = portfolioValue;
        this.dayPnL = dayPnL;
        this.dayPnLPercent = dayPnLPercent;
        this.currentPositions = currentPositions;
        this.cycleIntervalSeconds = cycleIntervalSeconds;
    }

    // Getters
    public Long getAgentId() { return agentId; }
    public String getAgentName() { return agentName; }
    public boolean isActive() { return isActive; }
    public String getLastActivity() { return lastActivity; }
    public int getTotalTrades() { return totalTrades; }
    public double getTotalReturnPercent() { return totalReturnPercent; }
    public double getPortfolioValue() { return portfolioValue; }
    public double getDayPnL() { return dayPnL; }
    public double getDayPnLPercent() { return dayPnLPercent; }
    public int getCurrentPositions() { return currentPositions; }
    public int getCycleIntervalSeconds() { return cycleIntervalSeconds; }
}

