package com.trading.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.LocalDateTime;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(
        name = "account_holdings",
        schema = "trading",
        uniqueConstraints = @UniqueConstraint(columnNames = {"account_id", "symbol"}))
@Getter
@Setter
@NoArgsConstructor
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

    // Removed current_price, market_value, unrealized_pnl columns
    // These are now calculated dynamically using live market data

    @Column(name = "last_updated", nullable = false)
    private LocalDateTime lastUpdated = LocalDateTime.now();

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();

    // Constructor with parameters
    public AccountHolding(TradingAccount account, String symbol, Integer quantity, Double averagePrice) {
        this.account = account;
        this.symbol = symbol;
        this.quantity = quantity;
        this.averagePrice = averagePrice;
        // Note: market value and P&L are calculated dynamically using live prices
    }

    // Business methods
    public void updateQuantity(Integer newQuantity, Double newAveragePrice) {
        this.quantity = newQuantity;
        this.averagePrice = newAveragePrice;
        this.lastUpdated = LocalDateTime.now();
    }

    public boolean isEmpty() {
        return quantity == null || quantity == 0;
    }

    // JPA lifecycle callbacks
    @PreUpdate
    public void preUpdate() {
        this.lastUpdated = LocalDateTime.now();
    }

    // Custom setters that need business logic
    public void setQuantity(Integer quantity) {
        this.quantity = quantity;
    }

    public void setAveragePrice(Double averagePrice) {
        this.averagePrice = averagePrice;
    }
}
