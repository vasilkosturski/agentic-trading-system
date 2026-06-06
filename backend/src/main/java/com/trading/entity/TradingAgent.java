package com.trading.entity;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToOne;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

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

    @Column(name = "style")
    private String style; // Short style for UI display (e.g., "Value Investor")

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

    @OneToOne(mappedBy = "agent", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private TradingAccount tradingAccount;

    public TradingAgent(String name, String description) {
        this.name = name;
        this.description = description;
    }

    @PreUpdate
    public void preUpdate() {
        this.updatedAt = Instant.now();
    }

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
        return (returnPercent != null && returnPercent < -10.0)
                || (lastActivity != null && lastActivity.isBefore(Instant.now().minus(7, ChronoUnit.DAYS)));
    }
}
