package com.trading.service;

import com.trading.exception.ResourceNotFoundException;
import java.time.Instant;
import org.springframework.stereotype.Service;

@Service
public class MarketService {

    private final PriceCacheService priceCacheService;

    public MarketService(PriceCacheService priceCacheService) {
        this.priceCacheService = priceCacheService;
    }

    public PriceData getSharePrice(String symbol) {
        if (symbol == null || symbol.trim().isEmpty()) {
            throw new IllegalArgumentException("Symbol cannot be null or empty");
        }
        String upperSymbol = symbol.toUpperCase();
        PriceData priceData = priceCacheService.getPrice(upperSymbol);
        if (priceData == null) {
            throw new ResourceNotFoundException(
                    "Symbol not found: " + upperSymbol + ". Finnhub does not have data for this symbol.");
        }
        return priceData;
    }

    public static class PriceData {
        private final double price;
        private final boolean cached;
        private final Instant timestamp;
        private final String source;

        public PriceData(double price, boolean cached, Instant timestamp, String source) {
            this.price = price;
            this.cached = cached;
            this.timestamp = timestamp;
            this.source = source;
        }

        public double getPrice() {
            return price;
        }

        public boolean isCached() {
            return cached;
        }

        public Instant getTimestamp() {
            return timestamp;
        }

        public String getSource() {
            return source;
        }
    }
}
