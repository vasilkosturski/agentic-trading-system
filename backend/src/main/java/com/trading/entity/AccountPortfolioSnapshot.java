package com.trading.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "account_portfolio_snapshots", schema = "trading")
public class AccountPortfolioSnapshot {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "account_id", nullable = false)
    private TradingAccount account;
    
    @Column(nullable = false)
    private LocalDateTime timestamp;
    
    @Column(name = "total_value", nullable = false)
    private Double totalValue;

    @Column(name = "cash_balance", nullable = false)
    private Double cashBalance;

    @Column(name = "holdings_value", nullable = false)
    private Double holdingsValue;

    @Column(name = "total_pnl")
    private Double totalPnl;

    @Column(name = "daily_pnl")
    private Double dailyPnl;

    @Column(name = "total_return_percent")
    private Double totalReturnPercent;
    
    @Column(name = "snapshot_type", nullable = false)
    private String snapshotType; // DAILY, HOURLY, TRANSACTION, MANUAL
    
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();
    
    // Constructors
    public AccountPortfolioSnapshot() {}
    
    public AccountPortfolioSnapshot(TradingAccount account, LocalDateTime timestamp, 
                                  Double totalValue, Double cashBalance, Double holdingsValue) {
        this.account = account;
        this.timestamp = timestamp;
        this.totalValue = totalValue;
        this.cashBalance = cashBalance;
        this.holdingsValue = holdingsValue;
        this.snapshotType = "MANUAL";
    }
    
    public AccountPortfolioSnapshot(TradingAccount account, LocalDateTime timestamp, 
                                  Double totalValue, String snapshotType) {
        this.account = account;
        this.timestamp = timestamp;
        this.totalValue = totalValue;
        this.snapshotType = snapshotType;
        this.cashBalance = 0.0;
        this.holdingsValue = totalValue;
    }
    
    // Business methods
    public void calculateMetrics(Double initialValue, Double previousValue) {
        if (initialValue != null && initialValue > 0) {
            this.totalPnl = this.totalValue - initialValue;
            this.totalReturnPercent = (this.totalPnl / initialValue) * 100;
        }
        
        if (previousValue != null) {
            this.dailyPnl = this.totalValue - previousValue;
        }
    }
    
    public boolean isPositiveReturn() {
        return totalPnl != null && totalPnl > 0;
    }
    
    public boolean isNegativeReturn() {
        return totalPnl != null && totalPnl < 0;
    }
    
    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    
    public TradingAccount getAccount() { return account; }
    public void setAccount(TradingAccount account) { this.account = account; }
    
    public LocalDateTime getTimestamp() { return timestamp; }
    public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }
    
    public Double getTotalValue() { return totalValue; }
    public void setTotalValue(Double totalValue) { this.totalValue = totalValue; }
    
    public Double getCashBalance() { return cashBalance; }
    public void setCashBalance(Double cashBalance) { this.cashBalance = cashBalance; }
    
    public Double getHoldingsValue() { return holdingsValue; }
    public void setHoldingsValue(Double holdingsValue) { this.holdingsValue = holdingsValue; }
    
    public Double getTotalPnl() { return totalPnl; }
    public void setTotalPnl(Double totalPnl) { this.totalPnl = totalPnl; }
    
    public Double getDailyPnl() { return dailyPnl; }
    public void setDailyPnl(Double dailyPnl) { this.dailyPnl = dailyPnl; }
    
    public Double getTotalReturnPercent() { return totalReturnPercent; }
    public void setTotalReturnPercent(Double totalReturnPercent) { this.totalReturnPercent = totalReturnPercent; }
    
    public String getSnapshotType() { return snapshotType; }
    public void setSnapshotType(String snapshotType) { this.snapshotType = snapshotType; }
    
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}