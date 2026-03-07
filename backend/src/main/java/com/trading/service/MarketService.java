package com.trading.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
// Note: Using HTTP client approach for Polygon API since Kotlin SDK has Java interop issues
// import io.polygon.kotlin.sdk.rest.PolygonRestClient;
// import io.polygon.kotlin.sdk.rest.stocks.AggregatesParameters;
// import io.polygon.kotlin.sdk.rest.stocks.AggregatesDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.RestClientException;

import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
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
    private final ObjectMapper objectMapper;
    private final Random random = new Random();
    
    // Configuration - Polygon API only (simplified for demo)
    @Value("${market.polygon.api-key:}")
    private String polygonApiKey;

    @Value("${market.polygon.base-url:https://api.polygon.io}")
    private String polygonBaseUrl;

    @Value("${market.polygon.enabled:true}")
    private boolean polygonEnabled;

    @Value("${market.polygon.free-tier:true}")
    private boolean polygonFreeTier;

    @Value("${market.cache.ttl-minutes:60}")
    private int cacheTtlMinutes;
    
    // Polygon HTTP client approach (avoiding Kotlin interop issues)
    private boolean polygonClientInitialized = false;
    
    // Cache for stock prices with timestamps
    private final Map<String, CachedPrice> priceCache = new ConcurrentHashMap<>();
    
    
    public MarketService(ObjectMapper objectMapper) {
        this.restTemplate = new RestTemplate();
        this.objectMapper = objectMapper;
    }
    
    /**
     * Check if Polygon client is available
     */
    private boolean isPolygonAvailable() {
        if (!polygonClientInitialized) {
            if (polygonEnabled && polygonApiKey != null && !polygonApiKey.isEmpty()) {
                logger.info("Polygon API key configured, using HTTP client approach");
                polygonClientInitialized = true;
                return true;
            } else {
                logger.debug("Polygon API not configured or disabled");
                return false;
            }
        }
        return polygonEnabled && polygonApiKey != null && !polygonApiKey.isEmpty();
    }
    
    /**
     * Get current stock price with caching and fallback mechanisms
     */
    public PriceData getSharePrice(String symbol) {
        if (symbol == null || symbol.trim().isEmpty()) {
            throw new IllegalArgumentException("Symbol cannot be null or empty");
        }
        
        String upperSymbol = symbol.toUpperCase();
        logger.info("🚀 DEBUGGING: MarketService.getSharePrice() called for symbol: {}", upperSymbol);
        
        // Check cache first
        CachedPrice cachedPrice = priceCache.get(upperSymbol);
        if (cachedPrice != null && !cachedPrice.isExpired(cacheTtlMinutes)) {
            logger.debug("Returning cached price for {}: ${}", upperSymbol, cachedPrice.price);
            return new PriceData(cachedPrice.price, DataTier.CACHED, cachedPrice.timestamp,
                "Data retrieved from cache (age: " + java.time.Duration.between(cachedPrice.timestamp, Instant.now()).toMinutes() + " minutes)");
        }

        // Try to fetch real price
        logger.info("📡 DEBUGGING: Attempting to fetch real price for {} from external APIs", upperSymbol);
        PriceData realPriceData = fetchRealPrice(upperSymbol);
        if (realPriceData != null) {
            Instant fetchTime = Instant.now();
            priceCache.put(upperSymbol, new CachedPrice(realPriceData.getPrice(), fetchTime));
            logger.info("✅ DEBUGGING: Successfully fetched real price for {}: ${} from {} ({})",
                upperSymbol, realPriceData.getPrice(), realPriceData.getDataSource(), realPriceData.getDataTier());
            return realPriceData;
        }
        
        // Zero tolerance for mock data - fail if real data unavailable
        logger.error("CRITICAL: Unable to fetch real market data for {} - no fallback allowed", upperSymbol);
        throw new RuntimeException("Unable to fetch real market data for symbol: " + upperSymbol +
            ". All external APIs failed. Check API keys and network connectivity.");
    }
    
    /**
     * Fetch real stock price from Polygon API only (simplified for demo)
     */
    private PriceData fetchRealPrice(String symbol) {
        // Only use Polygon API - simplified approach matching source project
        if (polygonEnabled) {
            PriceData polygonPrice = fetchFromPolygon(symbol);
            if (polygonPrice != null) {
                return polygonPrice;
            }
        }
        
        logger.warn("❌ DEBUGGING: Failed to fetch real price for {} from Polygon API", symbol);
        return null;
    }
    
    /**
     * Fetch price from Polygon API (free tier - end-of-day data) using HTTP client
     */
    private PriceData fetchFromPolygon(String symbol) {
        try {
            logger.info("🔍 DEBUGGING: Attempting Polygon API for symbol: {}", symbol);
            if (!isPolygonAvailable()) {
                logger.warn("❌ DEBUGGING: Polygon API not available for {} (enabled: {}, apiKey present: {})",
                    symbol, polygonEnabled, polygonApiKey != null && !polygonApiKey.isEmpty());
                return null;
            }
            
            // For free tier, get previous trading day's data
            LocalDate targetDate = getPreviousTradingDay();
            String dateStr = targetDate.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
            logger.info("📅 DEBUGGING: Using previous trading day: {} for symbol: {}", dateStr, symbol);
            
            // Polygon aggregates endpoint for daily data
            String url = String.format(
                "%s/v2/aggs/ticker/%s/range/1/day/%s/%s?adjusted=true&sort=asc&limit=1&apikey=%s",
                polygonBaseUrl, symbol, dateStr, dateStr, polygonApiKey
            );
            logger.info("🌐 DEBUGGING: Making Polygon API request to: {}", url.replace(polygonApiKey, "***API_KEY***"));
            
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            logger.info("📊 DEBUGGING: Polygon API response status: {} for symbol: {}", response.getStatusCode(), symbol);
            
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                logger.info("📄 DEBUGGING: Polygon API response body: {}", response.getBody());
                JsonNode jsonNode = objectMapper.readTree(response.getBody());
                
                // Check for successful response
                if (jsonNode.has("status") && "OK".equals(jsonNode.get("status").asText())) {
                    JsonNode results = jsonNode.get("results");
                    logger.info("🔍 DEBUGGING: Polygon results array size: {}", results != null && results.isArray() ? results.size() : "null");
                    
                    if (results != null && results.isArray() && results.size() > 0) {
                        JsonNode result = results.get(0);
                        
                        if (result.has("c")) { // 'c' is the closing price
                            Double closePrice = result.get("c").asDouble();
                            logger.info("💰 DEBUGGING: Polygon closing price found: ${} for {}", closePrice, symbol);
                            
                            if (closePrice > 0) {
                                logger.info("✅ DEBUGGING: Successfully fetched Polygon end-of-day price for {}: ${} (date: {})", symbol, closePrice, dateStr);
                                return new PriceData(closePrice, DataTier.END_OF_DAY, Instant.now(),
                                    "End-of-day closing price from Polygon (free tier) for " + dateStr);
                            }
                        }
                    }
                } else {
                    logger.warn("❌ DEBUGGING: Polygon API status not OK for {}: {}", symbol, jsonNode.get("status"));
                }
                
                // Check for API limit or error messages
                if (jsonNode.has("error")) {
                    logger.warn("Polygon API error for {}: {}", symbol, jsonNode.get("error").asText());
                } else if (jsonNode.has("message")) {
                    logger.warn("Polygon API message for {}: {}", symbol, jsonNode.get("message").asText());
                }
            }
            
            logger.debug("No Polygon data available for {} on {}", symbol, dateStr);
            return null;
            
        } catch (RestClientException e) {
            logger.error("HTTP error fetching from Polygon for {}: {}", symbol, e.getMessage());
            return null;
        } catch (Exception e) {
            logger.error("Error fetching from Polygon for {}: {}", symbol, e.getMessage());
            return null;
        }
    }
    
    /**
     * Get the previous trading day (skips weekends)
     */
    private LocalDate getPreviousTradingDay() {
        LocalDate date = LocalDate.now(ZoneId.of("America/New_York"));
        
        // Go back one day
        date = date.minusDays(1);
        
        // Skip weekends - if it's Sunday, go to Friday; if Saturday, go to Friday
        while (date.getDayOfWeek().getValue() > 5) { // Saturday = 6, Sunday = 7
            date = date.minusDays(1);
        }
        
        return date;
    }
    
    
    
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