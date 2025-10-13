package com.trading.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.Instant;

/**
 * Simple DTO for portfolio history data points used in charts
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PortfolioHistoryPoint {
    private Instant timestamp;
    private Double portfolioValue;
    
    @Override
    public String toString() {
        return "PortfolioHistoryPoint{" +
                "timestamp=" + timestamp +
                ", portfolioValue=" + portfolioValue +
                '}';
    }
}