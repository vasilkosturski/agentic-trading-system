package com.trading.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.time.Instant;

@Entity
@Table(name = "account_portfolio_snapshots", schema = "trading")
@Getter
@Setter
@NoArgsConstructor
public class AccountPortfolioSnapshot {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "account_id", nullable = false)
    private TradingAccount account;

    @Column(nullable = false)
    private Instant timestamp;
    
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
    
    @Column(name = "snapshot_type", nullable = true)
    private String snapshotType; // DEPRECATED: No longer used, will be removed in future migration

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    // Constructor with parameters
    public AccountPortfolioSnapshot(TradingAccount account, Instant timestamp,
                                  Double totalValue, Double cashBalance, Double holdingsValue) {
        this.account = account;
        this.timestamp = timestamp;
        this.totalValue = totalValue;
        this.cashBalance = cashBalance;
        this.holdingsValue = holdingsValue;
    }
    
    // DEPRECATED: Constructor kept for backwards compatibility, snapshotType parameter ignored
    public AccountPortfolioSnapshot(TradingAccount account, Instant timestamp,
                                  Double totalValue, String snapshotType) {
        this.account = account;
        this.timestamp = timestamp;
        this.totalValue = totalValue;
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
}