package com.trading.dto.response;

import java.util.List;

/**
 * Response DTO for portfolio performance data.
 * Extracted from TradingService for better modularity.
 */
public class PortfolioPerformanceResponse {
    private List<String> timestamps;
    private List<Double> values;
    private List<Double> returns;
    private List<Double> benchmark;

    public PortfolioPerformanceResponse(List<String> timestamps, List<Double> values,
                                        List<Double> returns, List<Double> benchmark) {
        this.timestamps = timestamps;
        this.values = values;
        this.returns = returns;
        this.benchmark = benchmark;
    }

    // Getters
    public List<String> getTimestamps() { return timestamps; }
    public List<Double> getValues() { return values; }
    public List<Double> getReturns() { return returns; }
    public List<Double> getBenchmark() { return benchmark; }
}

