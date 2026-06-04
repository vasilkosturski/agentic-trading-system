package com.trading.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import java.time.Instant;

/**
 * Database-backed price cache to persist market data across backend restarts.
 * Reduces API calls by caching prices with configurable TTL.
 */
@Entity
@Table(
        name = "price_cache",
        schema = "analytics",
        indexes = {
            @Index(name = "idx_price_cache_symbol", columnList = "symbol"),
            @Index(name = "idx_price_cache_timestamp", columnList = "cached_at")
        })
public class PriceCache {

    @Id
    @Column(name = "symbol", nullable = false, length = 10)
    private String symbol;

    @Column(name = "price", nullable = false)
    private double price;

    @Column(name = "cached_at", nullable = false)
    private Instant cachedAt;

    @Column(name = "source", length = 50)
    private String source;

    // Constructors
    public PriceCache() {}

    public PriceCache(String symbol, double price, Instant cachedAt, String source) {
        this.symbol = symbol;
        this.price = price;
        this.cachedAt = cachedAt;
        this.source = source;
    }

    // Getters and Setters
    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public double getPrice() {
        return price;
    }

    public void setPrice(double price) {
        this.price = price;
    }

    public Instant getCachedAt() {
        return cachedAt;
    }

    public void setCachedAt(Instant cachedAt) {
        this.cachedAt = cachedAt;
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }
}
