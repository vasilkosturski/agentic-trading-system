package com.trading.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.RestClientException;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

// Data tier enumeration for tracking data source quality
enum DataTier {
    REAL_TIME("Real-time", 0),
    END_OF_DAY("End-of-day", 1440), // 24 hours delay for free tier
    DELAYED("Delayed", 15),
    CACHED("Cached", 300),
    MOCK("Mock/Simulated", Integer.MAX_VALUE);
    
    private final String description;
    private final int delayMinutes;
    
    DataTier(String description, int delayMinutes) {
        this.description = description;
        this.delayMinutes = delayMinutes;
    }
    
    public String getDescription() { return description; }
    public int getDelayMinutes() { return delayMinutes; }
}

@Service
public class MarketService {
    
    private static final Logger logger = LoggerFactory.getLogger(MarketService.class);
    
    private final RestTemplate restTemplate;
    private final Random random = new Random();

    // Configuration - Finnhub
    @Value("${market.finnhub.api-key:}")
    private String finnhubApiKey;

    @Value("${market.finnhub.base-url:https://finnhub.io/api/v1}")
    private String finnhubBaseUrl;

    @Value("${market.cache.ttl-minutes:60}")
    private int cacheTtlMinutes;

    // Cache for stock prices with timestamps
    private final Map<String, CachedPrice> priceCache = new ConcurrentHashMap<>();


    public MarketService() {
        this.restTemplate = new RestTemplate();
    }
    
    /**
     * Get current stock price with caching (single provider: Finnhub)
     */
    public PriceData getSharePrice(String symbol) {
        if (symbol == null || symbol.trim().isEmpty()) {
            throw new IllegalArgumentException("Symbol cannot be null or empty");
        }

        String upperSymbol = symbol.toUpperCase();
        logger.info("MarketService.getSharePrice() called for symbol: {}", upperSymbol);

        // Check cache first
        CachedPrice cachedPrice = priceCache.get(upperSymbol);
        if (cachedPrice != null && !cachedPrice.isExpired(cacheTtlMinutes)) {
            logger.debug("Returning cached price for {}: ${}", upperSymbol, cachedPrice.price);
            return new PriceData(cachedPrice.price, DataTier.CACHED, cachedPrice.timestamp,
                "Data retrieved from cache (age: " + java.time.Duration.between(cachedPrice.timestamp, Instant.now()).toMinutes() + " minutes)");
        }

        // Fetch from Finnhub
        logger.info("Fetching price for {} from Finnhub", upperSymbol);
        PriceData priceData = fetchFromFinnhub(upperSymbol);
        if (priceData != null) {
            priceCache.put(upperSymbol, new CachedPrice(priceData.getPrice(), Instant.now()));
            logger.info("Successfully fetched price for {}: ${} from Finnhub", upperSymbol, priceData.getPrice());
            return priceData;
        }

        logger.error("Unable to fetch market data for {} from Finnhub", upperSymbol);
        throw new RuntimeException("Unable to fetch market data for symbol: " + upperSymbol +
            ". Finnhub API failed. Check FINNHUB_API_KEY and network connectivity.");
    }
    
    /**
     * Fetch price from Finnhub API (real-time quotes, 60 calls/min free tier)
     */
    private PriceData fetchFromFinnhub(String symbol) {
        try {
            logger.info("Fetching price from Finnhub for symbol: {}", symbol);

            String url = String.format("%s/quote?symbol=%s&token=%s",
                    finnhubBaseUrl, symbol, finnhubApiKey);

            FinnhubQuoteResponse quote = restTemplate.getForObject(url, FinnhubQuoteResponse.class);

            if (quote != null && quote.c() > 0) {
                logger.info("Finnhub price for {}: ${}", symbol, quote.c());
                return new PriceData(quote.c(), DataTier.REAL_TIME, Instant.now(),
                        "Real-time quote from Finnhub");
            }

            if (quote != null) {
                logger.warn("Finnhub returned zero price for {} - symbol may not be supported", symbol);
            }

            logger.debug("No Finnhub data available for {}", symbol);
            return null;

        } catch (RestClientException e) {
            logger.error("HTTP error fetching from Finnhub for {}: {}", symbol, e.getMessage());
            return null;
        } catch (Exception e) {
            logger.error("Error fetching from Finnhub for {}: {}", symbol, e.getMessage());
            return null;
        }
    }

    /**
     * Typed response for Finnhub /quote endpoint.
     * Fields match the Finnhub JSON keys for automatic Jackson deserialization.
     */
    private record FinnhubQuoteResponse(
        double c,   // current price
        double d,   // change
        double dp,  // percent change
        double h,   // high price of the day
        double l,   // low price of the day
        double o,   // open price of the day
        double pc,  // previous close price
        long t      // timestamp (unix)
    ) {}

    /**
     * Get historical prices for a symbol (mock implementation for now)
     */
    public HistoricalPriceData getHistoricalPrices(String symbol, int days) {
        List<HistoricalPrice> prices = new ArrayList<>();
        PriceData currentPriceData = getSharePrice(symbol);
        Double currentPrice = currentPriceData.getPrice();
        
        for (int i = days; i >= 0; i--) {
            Instant instant = Instant.now().minus(i, ChronoUnit.DAYS);
            LocalDate date = instant.atZone(ZoneId.of("UTC")).toLocalDate();
            double variation = (random.nextDouble() - 0.5) * 0.1; // +/- 5%
            double price = currentPrice * (1 + variation);

            prices.add(new HistoricalPrice(
                date.format(DateTimeFormatter.ISO_LOCAL_DATE),
                Math.round(price * 100.0) / 100.0
            ));
        }

        // Add data consistency warning for mock data
        String warning = null;
        if (currentPriceData.getDataTier() == DataTier.MOCK) {
            warning = "Historical data is simulated and may not reflect actual market conditions";
        }

        return new HistoricalPriceData(prices, currentPriceData.getDataTier(),
            Instant.now(), warning);
    }
    
    /**
     * Get market indicators for a symbol
     */
    public MarketIndicatorsData getMarketIndicators(String symbol) {
        HistoricalPriceData historicalData = getHistoricalPrices(symbol, 20);
        List<HistoricalPrice> prices = historicalData.getPrices();
        
        // Calculate simple moving averages
        double sma5 = prices.stream()
            .skip(Math.max(0, prices.size() - 5))
            .mapToDouble(p -> p.price)
            .average()
            .orElse(0.0);
            
        double sma20 = prices.stream()
            .mapToDouble(p -> p.price)
            .average()
            .orElse(0.0);
        
        // Calculate volatility (standard deviation)
        double mean = sma20;
        double variance = prices.stream()
            .mapToDouble(p -> Math.pow(p.price - mean, 2))
            .average()
            .orElse(0.0);
        double volatility = Math.sqrt(variance);
        
        MarketIndicators indicators = new MarketIndicators(
            Math.round(sma5 * 100.0) / 100.0,
            Math.round(sma20 * 100.0) / 100.0,
            Math.round(volatility * 100.0) / 100.0
        );

        return new MarketIndicatorsData(indicators, historicalData.getDataTier(),
            Instant.now(), historicalData.getWarning());
    }
    
    /**
     * Clear price cache (useful for testing or manual refresh)
     */
    public void clearCache() {
        priceCache.clear();
        logger.info("Price cache cleared");
    }
    
    // Inner classes for data structures
    
    private static class CachedPrice {
        final Double price;
        final Instant timestamp;

        CachedPrice(Double price, Instant timestamp) {
            this.price = price;
            this.timestamp = timestamp;
        }

        boolean isExpired(int ttlMinutes) {
            return Instant.now().isAfter(timestamp.plus(ttlMinutes, ChronoUnit.MINUTES));
        }
    }
    
    public static class HistoricalPrice {
        public final String date;
        public final Double price;
        
        public HistoricalPrice(String date, Double price) {
            this.date = date;
            this.price = price;
        }
    }
    
    public static class MarketIndicators {
        public final Double sma5;
        public final Double sma20;
        public final Double volatility;
        
        public MarketIndicators(Double sma5, Double sma20, Double volatility) {
            this.sma5 = sma5;
            this.sma20 = sma20;
            this.volatility = volatility;
        }
    }
    
    // Enhanced data structures with timing metadata
    
    public static class PriceData {
        private final Double price;
        private final DataTier dataTier;
        private final Instant timestamp;
        private final String dataSource;

        public PriceData(Double price, DataTier dataTier, Instant timestamp, String dataSource) {
            this.price = price;
            this.dataTier = dataTier;
            this.timestamp = timestamp;
            this.dataSource = dataSource;
        }

        public Double getPrice() { return price; }
        public DataTier getDataTier() { return dataTier; }
        public Instant getTimestamp() { return timestamp; }
        public String getDataSource() { return dataSource; }
        public int getDataAgeMinutes() {
            return (int) java.time.Duration.between(timestamp, Instant.now()).toMinutes();
        }
    }
    
    public static class HistoricalPriceData {
        private final List<HistoricalPrice> prices;
        private final DataTier dataTier;
        private final Instant timestamp;
        private final String warning;

        public HistoricalPriceData(List<HistoricalPrice> prices, DataTier dataTier,
                                 Instant timestamp, String warning) {
            this.prices = prices;
            this.dataTier = dataTier;
            this.timestamp = timestamp;
            this.warning = warning;
        }

        public List<HistoricalPrice> getPrices() { return prices; }
        public DataTier getDataTier() { return dataTier; }
        public Instant getTimestamp() { return timestamp; }
        public String getWarning() { return warning; }
    }
    
    public static class MarketIndicatorsData {
        private final MarketIndicators indicators;
        private final DataTier dataTier;
        private final Instant timestamp;
        private final String warning;

        public MarketIndicatorsData(MarketIndicators indicators, DataTier dataTier,
                                  Instant timestamp, String warning) {
            this.indicators = indicators;
            this.dataTier = dataTier;
            this.timestamp = timestamp;
            this.warning = warning;
        }

        public MarketIndicators getIndicators() { return indicators; }
        public DataTier getDataTier() { return dataTier; }
        public Instant getTimestamp() { return timestamp; }
        public String getWarning() { return warning; }
    }

    /**
     * Combined market data response: price + metadata + historical prices + indicators.
     * Single DTO for the consolidated GET /api/market/{symbol} endpoint.
     */
    public static class MarketDataResponse {
        private final Double price;
        private final DataTier dataTier;
        private final Instant timestamp;
        private final String dataSource;
        private final int dataAgeMinutes;
        private final List<HistoricalPrice> historicalPrices;
        private final MarketIndicators indicators;

        public MarketDataResponse(PriceData priceData,
                                  List<HistoricalPrice> historicalPrices,
                                  MarketIndicators indicators) {
            this.price = priceData.getPrice();
            this.dataTier = priceData.getDataTier();
            this.timestamp = priceData.getTimestamp();
            this.dataSource = priceData.getDataSource();
            this.dataAgeMinutes = priceData.getDataAgeMinutes();
            this.historicalPrices = historicalPrices;
            this.indicators = indicators;
        }

        public Double getPrice() { return price; }
        public DataTier getDataTier() { return dataTier; }
        public Instant getTimestamp() { return timestamp; }
        public String getDataSource() { return dataSource; }
        public int getDataAgeMinutes() { return dataAgeMinutes; }
        public List<HistoricalPrice> getHistoricalPrices() { return historicalPrices; }
        public MarketIndicators getIndicators() { return indicators; }
    }

    /**
     * Get combined market data for a symbol: price + historical prices + indicators.
     * Single method backing the consolidated endpoint.
     */
    public MarketDataResponse getMarketData(String symbol, int days) {
        PriceData priceData = getSharePrice(symbol);
        HistoricalPriceData historicalData = getHistoricalPrices(symbol, days);
        MarketIndicatorsData indicatorsData = getMarketIndicators(symbol);

        return new MarketDataResponse(
            priceData,
            historicalData.getPrices(),
            indicatorsData.getIndicators()
        );
    }
}