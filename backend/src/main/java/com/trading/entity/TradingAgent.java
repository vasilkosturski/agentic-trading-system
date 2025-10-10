package com.trading.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.time.Instant;
import java.time.temporal.ChronoUnit;

@Entity
@Table(name = "trading_agents", schema = "agents")
@Getter
@Setter
@NoArgsConstructor
public class TradingAgent {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(unique = true, nullable = false)
    private String name;
    
    @Column(columnDefinition = "TEXT")
    private String description;
    
    @Column(name = "is_active", nullable = false)
    private Boolean isActive = true;
    
    @Column(name = "risk_tolerance")
    private Double riskTolerance;

    @Column(name = "max_position_size")
    private Double maxPositionSize;
    
    @Column(name = "trading_frequency")
    private String tradingFrequency; // DAILY, WEEKLY, MONTHLY, INTRADAY
    
    @Column(name = "preferred_sectors", columnDefinition = "TEXT")
    private String preferredSectors; // JSON array of sectors

    @Column(name = "last_activity")
    private Instant lastActivity;

    @Column(name = "total_trades")
    private Integer totalTrades = 0;

    @Column(name = "total_pnl")
    private Double totalPnl = 0.0;

    @Column(name = "initial_capital")
    private Double initialCapital;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();
    
    // One-to-one relationship with trading account
    @OneToOne(mappedBy = "agent", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private TradingAccount tradingAccount;
    
    // Constructor with parameters
    public TradingAgent(String name, String description) {
        this.name = name;
        this.description = description;
    }
    
    // JPA lifecycle callbacks
    @PreUpdate
    public void preUpdate() {
        this.updatedAt = Instant.now();
    }

    // Business methods
    public void updateActivity() {
        this.lastActivity = Instant.now();
        this.updatedAt = Instant.now();
    }
    
    public void recordTrade(Double pnl) {
        this.totalTrades++;
        if (pnl != null) {
            this.totalPnl += pnl;
        }
        updateActivity();
    }

    public Double getTotalReturnPercent() {
        if (initialCapital != null && initialCapital > 0 && tradingAccount != null) {
            double currentValue = tradingAccount.getBalance();
            return ((currentValue - initialCapital) / initialCapital) * 100;
        }
        return 0.0;
    }

    public boolean isPerformingWell() {
        Double returnPercent = getTotalReturnPercent();
        return returnPercent != null && returnPercent > 5.0 && totalPnl > 0;
    }

    public boolean needsAttention() {
        Double returnPercent = getTotalReturnPercent();
        return (returnPercent != null && returnPercent < -10.0) ||
               (lastActivity != null && lastActivity.isBefore(Instant.now().minus(7, ChronoUnit.DAYS)));
    }
}