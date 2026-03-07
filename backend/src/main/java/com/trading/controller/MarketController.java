package com.trading.controller;

import com.trading.service.MarketService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * REST controller for market data operations.
 * Single consolidated endpoint returning price + historical + indicators.
 * Exceptions are handled by GlobalExceptionHandler.
 */
@RestController
@RequestMapping("/api/market")
public class MarketController {

    @Autowired
    private MarketService marketService;

    /**
     * Get combined market data for a symbol: current price with metadata,
     * historical prices, and technical indicators.
     *
     * @param symbol stock symbol (e.g., AAPL, GOOGL, TSLA)
     * @param days   number of days of historical data (default 30)
     * @return MarketDataResponse with price, metadata, historical prices, and indicators
     */
    @GetMapping("/{symbol}")
    public ResponseEntity<MarketService.MarketDataResponse> getMarketData(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "30") int days) {
        MarketService.MarketDataResponse response = marketService.getMarketData(symbol, days);
        return ResponseEntity.ok(response);
    }

}
