package com.trading.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "trading_agents", schema = "agents")
public class TradingAgent {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(unique = true, nullable = false)
    private String name;
    
    @Column(nullable = false)
    private String strategy;
    
    @Column(columnDefinition = "TEXT")
    private String description;
    
    @Column(name = "is_active", nullable = false)
    private Boolean isActive = true;
    
    @Column(name = "risk_tolerance", precision = 5, scale = 2)
    private Double riskTolerance;
    
    @Column(name = "max_position_size", precision = 15, scale = 2)
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
    
    @Column(name = "total_pnl", precision = 15, scale = 2)
    private Double totalPnl = 0.0;
    
    @Column(name = "win_rate", precision = 5, scale = 2)
    private Double winRate = 0.0;
    
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();
    
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt = LocalDateTime.now();
    
    // One-to-one relationship with trading account
    @OneToOne(mappedBy = "agent", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private TradingAccount tradingAccount;
    
    // Constructors
    public TradingAgent() {}
    
    public TradingAgent(String name, String strategy, String description) {
        this.name = name;
        this.strategy = strategy;
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
    
    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public String getStrategy() { return strategy; }
    public void setStrategy(String strategy) { this.strategy = strategy; }
    
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    
    public Boolean getIsActive() { return isActive; }
    public void setIsActive(Boolean isActive) { this.isActive = isActive; }
    
    public Double getRiskTolerance() { return riskTolerance; }
    public void setRiskTolerance(Double riskTolerance) { this.riskTolerance = riskTolerance; }
    
    public Double getMaxPositionSize() { return maxPositionSize; }
    public void setMaxPositionSize(Double maxPositionSize) { this.maxPositionSize = maxPositionSize; }
    
    public String getTradingFrequency() { return tradingFrequency; }
    public void setTradingFrequency(String tradingFrequency) { this.tradingFrequency = tradingFrequency; }
    
    public String getPreferredSectors() { return preferredSectors; }
    public void setPreferredSectors(String preferredSectors) { this.preferredSectors = preferredSectors; }
    
    public LocalDateTime getLastActivity() { return lastActivity; }
    public void setLastActivity(LocalDateTime lastActivity) { this.lastActivity = lastActivity; }
    
    public Integer getTotalTrades() { return totalTrades; }
    public void setTotalTrades(Integer totalTrades) { this.totalTrades = totalTrades; }
    
    public Integer getSuccessfulTrades() { return successfulTrades; }
    public void setSuccessfulTrades(Integer successfulTrades) { this.successfulTrades = successfulTrades; }
    
    public Double getTotalPnl() { return totalPnl; }
    public void setTotalPnl(Double totalPnl) { this.totalPnl = totalPnl; }
    
    public Double getWinRate() { return winRate; }
    public void setWinRate(Double winRate) { this.winRate = winRate; }
    
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
    
    public TradingAccount getTradingAccount() { return tradingAccount; }
    public void setTradingAccount(TradingAccount tradingAccount) { this.tradingAccount = tradingAccount; }
}