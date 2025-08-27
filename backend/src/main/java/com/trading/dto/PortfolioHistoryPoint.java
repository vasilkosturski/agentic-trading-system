package com.trading.dto;

import java.time.LocalDateTime;

/**
 * Simple DTO for portfolio history data points used in charts
 */
public class PortfolioHistoryPoint {
    private LocalDateTime timestamp;
    private Double portfolioValue;
    
    // Constructors
    public PortfolioHistoryPoint() {}
    
    public PortfolioHistoryPoint(LocalDateTime timestamp, Double portfolioValue) {
        this.timestamp = timestamp;
        this.portfolioValue = portfolioValue;
    }
    
    // Getters and Setters
    public LocalDateTime getTimestamp() {
        return timestamp;
    }
    
    public void setTimestamp(LocalDateTime timestamp) {
        this.timestamp = timestamp;
    }
    
    public Double getPortfolioValue() {
        return portfolioValue;
    }
    
    public void setPortfolioValue(Double portfolioValue) {
        this.portfolioValue = portfolioValue;
    }
    
    @Override
    public String toString() {
        return "PortfolioHistoryPoint{" +
                "timestamp=" + timestamp +
                ", portfolioValue=" + portfolioValue +
                '}';
    }
}