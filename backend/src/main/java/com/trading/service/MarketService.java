package com.trading.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.RestClientException;

import java.time.Duration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class MarketService {

    private static final Logger logger = LoggerFactory.getLogger(MarketService.class);

    private final RestTemplate restTemplate;
    private final RetryTemplate retryTemplate;

    @Value("${market.finnhub.api-key:}")
    private String finnhubApiKey;

    @Value("${market.finnhub.base-url:https://finnhub.io/api/v1}")
    private String finnhubBaseUrl;

    @Value("${market.cache.ttl-minutes:60}")
    private int cacheTtlMinutes;

    private final Map<String, CachedPrice> priceCache = new ConcurrentHashMap<>();

    public MarketService(RetryTemplate retryTemplate) {
        this.restTemplate = new RestTemplate();
        this.retryTemplate = retryTemplate;
    }

    /**
     * Get current stock price with caching (single provider: Finnhub).
     */
    public PriceData getSharePrice(String symbol) {
        if (symbol == null || symbol.trim().isEmpty()) {
            throw new IllegalArgumentException("Symbol cannot be null or empty");
        }

        String upperSymbol = symbol.toUpperCase();

        // Check cache first
        CachedPrice cached = priceCache.get(upperSymbol);
        if (cached != null && !cached.isExpired(cacheTtlMinutes)) {
            long ageMinutes = Duration.between(cached.timestamp, Instant.now()).toMinutes();
            logger.debug("Returning cached price for {}: ${} (age: {} min)", upperSymbol, cached.price, ageMinutes);
            return new PriceData(cached.price, true, cached.timestamp, "Cached (age: " + ageMinutes + " min)");
        }

        // Fetch from Finnhub with retry
        PriceData priceData = fetchFromFinnhub(upperSymbol);
        if (priceData != null) {
            priceCache.put(upperSymbol, new CachedPrice(priceData.getPrice(), Instant.now()));
            return priceData;
        }

        throw new RuntimeException("Unable to fetch market data for symbol: " + upperSymbol +
            ". Finnhub API failed. Check FINNHUB_API_KEY and network connectivity.");
    }

    /**
     * Fetch price from Finnhub API with centralized retry (exponential backoff via RetryTemplate).
     */
    private PriceData fetchFromFinnhub(String symbol) {
        try {
            FinnhubQuoteResponse quote = retryTemplate.execute(ctx -> {
                if (ctx.getRetryCount() > 0) {
                    logger.warn("Finnhub retry {}/3 for {}", ctx.getRetryCount(), symbol);
                }
                String url = String.format("%s/quote?symbol=%s&token=%s",
                        finnhubBaseUrl, symbol, finnhubApiKey);
                return restTemplate.getForObject(url, FinnhubQuoteResponse.class);
            });

            if (quote != null && quote.c() > 0) {
                logger.info("Finnhub price for {}: ${}", symbol, quote.c());
                return new PriceData(quote.c(), false, Instant.now(), "Real-time quote from Finnhub");
            }

            if (quote != null) {
                logger.warn("Finnhub returned zero price for {} - symbol may not be supported", symbol);
            }
            return null;

        } catch (RestClientException e) {
            logger.error("Finnhub failed after retries for {}: {}", symbol, e.getMessage());
            return null;
        }
    }

    private record FinnhubQuoteResponse(
        double c, double d, double dp, double h,
        double l, double o, double pc, long t
    ) {}

    private static class CachedPrice {
        final double price;
        final Instant timestamp;

        CachedPrice(double price, Instant timestamp) {
            this.price = price;
            this.timestamp = timestamp;
        }

        boolean isExpired(int ttlMinutes) {
            return Instant.now().isAfter(timestamp.plus(ttlMinutes, ChronoUnit.MINUTES));
        }
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

        public double getPrice() { return price; }
        public boolean isCached() { return cached; }
        public Instant getTimestamp() { return timestamp; }
        public String getSource() { return source; }
    }
}
