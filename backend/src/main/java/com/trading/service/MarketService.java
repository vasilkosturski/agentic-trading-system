package com.trading.service;

import org.springframework.stereotype.Service;
import java.util.HashMap;
import java.util.Map;
import java.util.Random;

@Service
public class MarketService {
    
    private final Random random = new Random();
    
    // Mock stock prices - in a real system this would call external APIs
    private final Map<String, Double> basePrices = new HashMap<String, Double>() {{
        put("AAPL", 150.0);
        put("GOOGL", 2800.0);
        put("MSFT", 300.0);
        put("TSLA", 200.0);
        put("AMZN", 3200.0);
        put("NVDA", 800.0);
        put("META", 350.0);
        put("NFLX", 400.0);
        put("SPY", 450.0);
        put("QQQ", 380.0);
    }};
    
    public Double getSharePrice(String symbol) {
        if (symbol == null || symbol.trim().isEmpty()) {
            throw new IllegalArgumentException("Symbol cannot be null or empty");
        }
        
        String upperSymbol = symbol.toUpperCase();
        
        // Get base price or default to $100 for unknown symbols
        Double basePrice = basePrices.getOrDefault(upperSymbol, 100.0);
        
        // Add some random variation (+/- 5%)
        double variation = (random.nextDouble() - 0.5) * 0.1; // -5% to +5%
        double currentPrice = basePrice * (1 + variation);
        
        // Round to 2 decimal places
        return Math.round(currentPrice * 100.0) / 100.0;
    }
    
    public boolean isMarketOpen() {
        // Simplified market hours check - in reality this would check actual market hours
        java.time.LocalTime now = java.time.LocalTime.now();
        java.time.LocalTime marketOpen = java.time.LocalTime.of(9, 30);
        java.time.LocalTime marketClose = java.time.LocalTime.of(16, 0);
        
        return now.isAfter(marketOpen) && now.isBefore(marketClose);
    }
}