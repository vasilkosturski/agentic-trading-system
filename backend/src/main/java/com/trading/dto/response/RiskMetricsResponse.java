package com.trading.dto.response;

/**
 * Response DTO for risk metrics.
 * Extracted from TradingService for better modularity.
 */
public class RiskMetricsResponse {
    private double totalExposure;
    private double maxDrawdown;
    private double sharpeRatio;
    private double volatility;
    private double beta;
    private double var95;
    private double expectedShortfall;

    public RiskMetricsResponse(double totalExposure, double maxDrawdown, double sharpeRatio,
                               double volatility, double beta, double var95, double expectedShortfall) {
        this.totalExposure = totalExposure;
        this.maxDrawdown = maxDrawdown;
        this.sharpeRatio = sharpeRatio;
        this.volatility = volatility;
        this.beta = beta;
        this.var95 = var95;
        this.expectedShortfall = expectedShortfall;
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

