package com.trading.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.RestClientException;

import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class MarketService {
    
    private static final Logger logger = LoggerFactory.getLogger(MarketService.class);
    
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;
    private final Random random = new Random();
    
    // Configuration
    @Value("${market.alpha-vantage.api-key:demo}")
    private String alphaVantageApiKey;
    
    @Value("${market.cache.ttl-minutes:5}")
    private int cacheTtlMinutes;
    
    @Value("${market.fallback-to-mock:true}")
    private boolean fallbackToMock;
    
    // Cache for stock prices with timestamps
    private final Map<String, CachedPrice> priceCache = new ConcurrentHashMap<>();
    
    // Mock stock prices for fallback
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
        put("BRK.B", 350.0);
        put("JNJ", 160.0);
        put("V", 250.0);
        put("WMT", 145.0);
        put("PG", 155.0);
    }};
    
    public MarketService(ObjectMapper objectMapper) {
        this.restTemplate = new RestTemplate();
        this.objectMapper = objectMapper;
    }
    
    /**
     * Get current stock price with caching and fallback mechanisms
     */
    public Double getSharePrice(String symbol) {
        if (symbol == null || symbol.trim().isEmpty()) {
            throw new IllegalArgumentException("Symbol cannot be null or empty");
        }
        
        String upperSymbol = symbol.toUpperCase();
        
        // Check cache first
        CachedPrice cachedPrice = priceCache.get(upperSymbol);
        if (cachedPrice != null && !cachedPrice.isExpired(cacheTtlMinutes)) {
            logger.debug("Returning cached price for {}: ${}", upperSymbol, cachedPrice.price);
            return cachedPrice.price;
        }
        
        // Try to fetch real price
        Double realPrice = fetchRealPrice(upperSymbol);
        if (realPrice != null) {
            priceCache.put(upperSymbol, new CachedPrice(realPrice, LocalDateTime.now()));
            logger.info("Fetched real price for {}: ${}", upperSymbol, realPrice);
            return realPrice;
        }
        
        // Fallback to mock price if enabled
        if (fallbackToMock) {
            Double mockPrice = getMockPrice(upperSymbol);
            logger.warn("Using mock price for {} (real data unavailable): ${}", upperSymbol, mockPrice);
            return mockPrice;
        }
        
        throw new RuntimeException("Unable to fetch price for symbol: " + upperSymbol);
    }
    
    /**
     * Fetch real stock price from external APIs
     */
    private Double fetchRealPrice(String symbol) {
        // Try Alpha Vantage first
        Double price = fetchFromAlphaVantage(symbol);
        if (price != null) {
            return price;
        }
        
        // Try Yahoo Finance as fallback
        price = fetchFromYahooFinance(symbol);
        if (price != null) {
            return price;
        }
        
        logger.warn("Failed to fetch real price for {} from all sources", symbol);
        return null;
    }
    
    /**
     * Fetch price from Alpha Vantage API
     */
    private Double fetchFromAlphaVantage(String symbol) {
        try {
            String url = String.format(
                "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=%s&apikey=%s",
                symbol, alphaVantageApiKey
            );
            
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                JsonNode jsonNode = objectMapper.readTree(response.getBody());
                JsonNode quote = jsonNode.get("Global Quote");
                
                if (quote != null && quote.has("05. price")) {
                    return quote.get("05. price").asDouble();
                }
                
                // Check for API limit error
                if (jsonNode.has("Note") || jsonNode.has("Information")) {
                    logger.warn("Alpha Vantage API limit reached for {}", symbol);
                }
            }
        } catch (RestClientException e) {
            logger.error("HTTP error fetching from Alpha Vantage for {}: {}", symbol, e.getMessage());
        } catch (Exception e) {
            logger.error("Error fetching from Alpha Vantage for {}: {}", symbol, e.getMessage());
        }
        
        return null;
    }
    
    /**
     * Fetch price from Yahoo Finance (unofficial API)
     */
    private Double fetchFromYahooFinance(String symbol) {
        try {
            String url = String.format(
                "https://query1.finance.yahoo.com/v8/finance/chart/%s",
                symbol
            );
            
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                JsonNode jsonNode = objectMapper.readTree(response.getBody());
                JsonNode chart = jsonNode.get("chart");
                
                if (chart != null && chart.has("result") && chart.get("result").isArray()) {
                    JsonNode result = chart.get("result").get(0);
                    JsonNode meta = result.get("meta");
                    
                    if (meta != null && meta.has("regularMarketPrice")) {
                        return meta.get("regularMarketPrice").asDouble();
                    }
                }
            }
        } catch (RestClientException e) {
            logger.error("HTTP error fetching from Yahoo Finance for {}: {}", symbol, e.getMessage());
        } catch (Exception e) {
            logger.error("Error fetching from Yahoo Finance for {}: {}", symbol, e.getMessage());
        }
        
        return null;
    }
    
    /**
     * Generate mock price with realistic variation
     */
    private Double getMockPrice(String symbol) {
        Double basePrice = basePrices.getOrDefault(symbol, 100.0);
        
        // Add some random variation (+/- 5%)
        double variation = (random.nextDouble() - 0.5) * 0.1; // -5% to +5%
        double currentPrice = basePrice * (1 + variation);
        
        // Round to 2 decimal places
        return Math.round(currentPrice * 100.0) / 100.0;
    }
    
    /**
     * Get historical prices for a symbol (mock implementation for now)
     */
    public List<HistoricalPrice> getHistoricalPrices(String symbol, int days) {
        List<HistoricalPrice> prices = new ArrayList<>();
        Double currentPrice = getSharePrice(symbol);
        
        for (int i = days; i >= 0; i--) {
            LocalDateTime date = LocalDateTime.now().minusDays(i);
            double variation = (random.nextDouble() - 0.5) * 0.1; // +/- 5%
            double price = currentPrice * (1 + variation);
            
            prices.add(new HistoricalPrice(
                date.format(DateTimeFormatter.ISO_LOCAL_DATE),
                Math.round(price * 100.0) / 100.0
            ));
        }
        
        return prices;
    }
    
    /**
     * Get market indicators for a symbol
     */
    public MarketIndicators getMarketIndicators(String symbol) {
        List<HistoricalPrice> prices = getHistoricalPrices(symbol, 20);
        
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
        
        return new MarketIndicators(
            Math.round(sma5 * 100.0) / 100.0,
            Math.round(sma20 * 100.0) / 100.0,
            Math.round(volatility * 100.0) / 100.0
        );
    }
    
    /**
     * Check if market is currently open (US Eastern Time)
     */
    public boolean isMarketOpen() {
        LocalTime now = LocalTime.now(ZoneId.of("America/New_York"));
        LocalTime marketOpen = LocalTime.of(9, 30);
        LocalTime marketClose = LocalTime.of(16, 0);
        
        // Check if it's a weekday
        int dayOfWeek = LocalDateTime.now(ZoneId.of("America/New_York")).getDayOfWeek().getValue();
        boolean isWeekday = dayOfWeek >= 1 && dayOfWeek <= 5;
        
        return isWeekday && now.isAfter(marketOpen) && now.isBefore(marketClose);
    }
    
    /**
     * Get market status information
     */
    public MarketStatus getMarketStatus() {
        boolean isOpen = isMarketOpen();
        LocalDateTime now = LocalDateTime.now(ZoneId.of("America/New_York"));
        
        String status = isOpen ? "OPEN" : "CLOSED";
        String nextEvent = isOpen ? "Market closes at 4:00 PM ET" : "Market opens at 9:30 AM ET";
        
        return new MarketStatus(status, nextEvent, now.format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
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
        final LocalDateTime timestamp;
        
        CachedPrice(Double price, LocalDateTime timestamp) {
            this.price = price;
            this.timestamp = timestamp;
        }
        
        boolean isExpired(int ttlMinutes) {
            return LocalDateTime.now().isAfter(timestamp.plusMinutes(ttlMinutes));
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
    
    public static class MarketStatus {
        public final String status;
        public final String nextEvent;
        public final String currentTime;
        
        public MarketStatus(String status, String nextEvent, String currentTime) {
            this.status = status;
            this.nextEvent = nextEvent;
            this.currentTime = currentTime;
        }
    }
}