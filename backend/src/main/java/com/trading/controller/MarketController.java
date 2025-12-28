package com.trading.controller;

import com.trading.service.MarketService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * REST controller for market data operations.
 * Returns data directly without ToolResponse wrapper.
 * Exceptions are handled by GlobalExceptionHandler.
 */
@RestController
@RequestMapping("/api/market")
public class MarketController {

    @Autowired
    private MarketService marketService;

    /**
     * Get current price data for a symbol.
     *
     * @param symbol stock symbol
     * @return PriceData with current price and metadata
     */
    @GetMapping("/price/{symbol}")
    public ResponseEntity<MarketService.PriceData> getSharePrice(@PathVariable String symbol) {
        MarketService.PriceData priceData = marketService.getSharePrice(symbol);
        return ResponseEntity.ok(priceData);
    }

    /**
     * Backward compatibility endpoint - returns just the price value.
     *
     * @param symbol stock symbol
     * @return current price as Double
     */
    @GetMapping("/price/{symbol}/value")
    public ResponseEntity<Double> getSharePriceValue(@PathVariable String symbol) {
        MarketService.PriceData priceData = marketService.getSharePrice(symbol);
        return ResponseEntity.ok(priceData.getPrice());
    }

    /**
     * Get historical price data for a symbol.
     *
     * @param symbol stock symbol
     * @param days   number of days of historical data (default 30)
     * @return HistoricalPriceData with price history
     */
    @GetMapping("/historical/{symbol}")
    public ResponseEntity<MarketService.HistoricalPriceData> getHistoricalPrices(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "30") int days) {
        MarketService.HistoricalPriceData historicalData = marketService.getHistoricalPrices(symbol, days);
        return ResponseEntity.ok(historicalData);
    }

    /**
     * Backward compatibility endpoint - returns just the price list.
     *
     * @param symbol stock symbol
     * @param days   number of days of historical data (default 30)
     * @return List of HistoricalPrice
     */
    @GetMapping("/historical/{symbol}/prices")
    public ResponseEntity<List<MarketService.HistoricalPrice>> getHistoricalPricesList(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "30") int days) {
        MarketService.HistoricalPriceData historicalData = marketService.getHistoricalPrices(symbol, days);
        return ResponseEntity.ok(historicalData.getPrices());
    }

    /**
     * Get market indicators for a symbol.
     *
     * @param symbol stock symbol
     * @return MarketIndicatorsData with technical indicators
     */
    @GetMapping("/indicators/{symbol}")
    public ResponseEntity<MarketService.MarketIndicatorsData> getMarketIndicators(@PathVariable String symbol) {
        MarketService.MarketIndicatorsData indicatorsData = marketService.getMarketIndicators(symbol);
        return ResponseEntity.ok(indicatorsData);
    }

    /**
     * Backward compatibility endpoint - returns just the indicators.
     *
     * @param symbol stock symbol
     * @return MarketIndicators with technical indicators
     */
    @GetMapping("/indicators/{symbol}/values")
    public ResponseEntity<MarketService.MarketIndicators> getMarketIndicatorsValues(@PathVariable String symbol) {
        MarketService.MarketIndicatorsData indicatorsData = marketService.getMarketIndicators(symbol);
        return ResponseEntity.ok(indicatorsData.getIndicators());
    }

    /**
     * Clear the market data cache.
     *
     * @return success message
     */
    @PostMapping("/cache/clear")
    public ResponseEntity<String> clearCache() {
        marketService.clearCache();
        return ResponseEntity.ok("Cache cleared successfully");
    }

    /**
     * Health check endpoint.
     *
     * @return health status message
     */
    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("Market service is running");
    }
}