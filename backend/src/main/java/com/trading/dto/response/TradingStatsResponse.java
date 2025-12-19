package com.trading.dto.response;

/**
 * Response DTO for trading statistics.
 * Extracted from TradingService for better modularity.
 */
public class TradingStatsResponse {
    private int totalTrades;
    private double totalVolume;
    private double totalPnL;
    private double averageTradeSize;
    private double largestWin;
    private double largestLoss;

    public TradingStatsResponse(int totalTrades, double totalVolume, double totalPnL,
                                double averageTradeSize, double largestWin, double largestLoss) {
        this.totalTrades = totalTrades;
        this.totalVolume = totalVolume;
        this.totalPnL = totalPnL;
        this.averageTradeSize = averageTradeSize;
        this.largestWin = largestWin;
        this.largestLoss = largestLoss;
    }

    // Getters
    public int getTotalTrades() { return totalTrades; }
    public double getTotalVolume() { return totalVolume; }
    public double getTotalPnL() { return totalPnL; }
    public double getAverageTradeSize() { return averageTradeSize; }
    public double getLargestWin() { return largestWin; }
    public double getLargestLoss() { return largestLoss; }
}

