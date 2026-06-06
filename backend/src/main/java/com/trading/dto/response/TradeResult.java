package com.trading.dto.response;

public record TradeResult(Long tradeId, String symbol, Integer quantity, Double price, Double newBalance) {}
