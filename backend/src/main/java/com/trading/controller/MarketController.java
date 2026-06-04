package com.trading.controller;

import com.trading.service.MarketService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/market")
public class MarketController {

    private final MarketService marketService;

    public MarketController(MarketService marketService) {
        this.marketService = marketService;
    }

    @GetMapping("/{symbol}")
    public ResponseEntity<MarketService.PriceData> getMarketData(
            @PathVariable String symbol, @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(marketService.getSharePrice(symbol));
    }
}
