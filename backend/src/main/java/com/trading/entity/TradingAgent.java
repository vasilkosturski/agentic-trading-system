package com.trading.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.time.LocalDateTime;

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
    private LocalDateTime lastActivity;
    
    @Column(name = "total_trades")
    private Integer totalTrades = 0;
    
    @Column(name = "successful_trades")
    private Integer successfulTrades = 0;
    
    @Column(name = "total_pnl")
    private Double totalPnl = 0.0;

    @Column(name = "win_rate")
    private Double winRate = 0.0;
    
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();
    
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt = LocalDateTime.now();
    
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
        this.updatedAt = LocalDateTime.now();
    }
    
    // Business methods
    public void updateActivity() {
        this.lastActivity = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }
    
    public void recordTrade(boolean successful, Double pnl) {
        this.totalTrades++;
        if (successful) {
            this.successfulTrades++;
        }
        if (pnl != null) {
            this.totalPnl += pnl;
        }
        updateWinRate();
        updateActivity();
    }
    
    private void updateWinRate() {
        if (totalTrades > 0) {
            this.winRate = (double) successfulTrades / totalTrades * 100;
        }
    }
    
    public boolean isPerformingWell() {
        return winRate != null && winRate > 60.0 && totalPnl > 0;
    }
    
    public boolean needsAttention() {
        return winRate != null && winRate < 40.0 || 
               (lastActivity != null && lastActivity.isBefore(LocalDateTime.now().minusDays(7)));
    }
}