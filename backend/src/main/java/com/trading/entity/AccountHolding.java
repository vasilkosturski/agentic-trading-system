package com.trading.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "account_holdings", schema = "trading",
       uniqueConstraints = @UniqueConstraint(columnNames = {"account_id", "symbol"}))
public class AccountHolding {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "account_id", nullable = false)
    private TradingAccount account;
    
    @Column(nullable = false)
    private String symbol;
    
    @Column(nullable = false)
    private Integer quantity;
    
    @Column(name = "average_price")
    private Double averagePrice;

    @Column(name = "current_price")
    private Double currentPrice;

    @Column(name = "market_value")
    private Double marketValue;

    @Column(name = "unrealized_pnl")
    private Double unrealizedPnl;
    
    @Column(name = "last_updated", nullable = false)
    private LocalDateTime lastUpdated = LocalDateTime.now();
    
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();
    
    // Constructors
    public AccountHolding() {}
    
    public AccountHolding(TradingAccount account, String symbol, Integer quantity, Double averagePrice) {
        this.account = account;
        this.symbol = symbol;
        this.quantity = quantity;
        this.averagePrice = averagePrice;
        this.currentPrice = averagePrice; // Initialize with average price
        updateCalculatedFields();
    }
    
    // Business methods
    public void updateQuantity(Integer newQuantity, Double newAveragePrice) {
        this.quantity = newQuantity;
        this.averagePrice = newAveragePrice;
        this.lastUpdated = LocalDateTime.now();
        updateCalculatedFields();
    }
    
    public void updateCurrentPrice(Double currentPrice) {
        this.currentPrice = currentPrice;
        this.lastUpdated = LocalDateTime.now();
        updateCalculatedFields();
    }
    
    private void updateCalculatedFields() {
        if (this.quantity != null && this.currentPrice != null) {
            this.marketValue = this.quantity * this.currentPrice;
            
            if (this.averagePrice != null) {
                this.unrealizedPnl = this.quantity * (this.currentPrice - this.averagePrice);
            }
        }
    }
    
    /**
     * Calculate market metrics (market value and unrealized P&L)
     */
    public void calculateMarketMetrics() {
        updateCalculatedFields();
    }
    
    public boolean isEmpty() {
        return quantity == null || quantity == 0;
    }
    
    // JPA lifecycle callbacks
    @PreUpdate
    public void preUpdate() {
        this.lastUpdated = LocalDateTime.now();
        updateCalculatedFields();
    }
    
    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    
    public TradingAccount getAccount() { return account; }
    public void setAccount(TradingAccount account) { this.account = account; }
    
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { 
        this.quantity = quantity;
        updateCalculatedFields();
    }
    
    public Double getAveragePrice() { return averagePrice; }
    public void setAveragePrice(Double averagePrice) { 
        this.averagePrice = averagePrice;
        updateCalculatedFields();
    }
    
    public Double getCurrentPrice() { return currentPrice; }
    public void setCurrentPrice(Double currentPrice) { 
        this.currentPrice = currentPrice;
        updateCalculatedFields();
    }
    
    public Double getMarketValue() { return marketValue; }
    public void setMarketValue(Double marketValue) { this.marketValue = marketValue; }
    
    public Double getUnrealizedPnl() { return unrealizedPnl; }
    public void setUnrealizedPnl(Double unrealizedPnl) { this.unrealizedPnl = unrealizedPnl; }
    
    public LocalDateTime getLastUpdated() { return lastUpdated; }
    public void setLastUpdated(LocalDateTime lastUpdated) { this.lastUpdated = lastUpdated; }
    
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}