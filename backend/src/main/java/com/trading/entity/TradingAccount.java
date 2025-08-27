package com.trading.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "trading_accounts", schema = "trading")
public class TradingAccount {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(unique = true, nullable = false)
    private String name;
    
    @Column(nullable = false)
    private Double balance;
    
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();
    
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt = LocalDateTime.now();
    
    @Column(name = "is_active", nullable = false)
    private Boolean isActive = true;
    
    // One-to-many relationships
    @OneToMany(mappedBy = "account", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<AccountTransaction> transactions = new ArrayList<>();
    
    @OneToMany(mappedBy = "account", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<AccountHolding> holdings = new ArrayList<>();
    
    @OneToMany(mappedBy = "account", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<AccountPortfolioSnapshot> portfolioSnapshots = new ArrayList<>();
    
    // One-to-one relationship with trading agent
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "agent_id")
    private TradingAgent agent;
    
    // Constructors
    public TradingAccount() {}
    
    public TradingAccount(String name, Double balance) {
        this.name = name;
        this.balance = balance;
    }
    
    // JPA lifecycle callbacks
    @PreUpdate
    public void preUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
    
    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public Double getBalance() { return balance; }
    public void setBalance(Double balance) { this.balance = balance; }
    
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
    
    public Boolean getIsActive() { return isActive; }
    public void setIsActive(Boolean isActive) { this.isActive = isActive; }
    
    public List<AccountTransaction> getTransactions() { return transactions; }
    public void setTransactions(List<AccountTransaction> transactions) { this.transactions = transactions; }
    
    public List<AccountHolding> getHoldings() { return holdings; }
    public void setHoldings(List<AccountHolding> holdings) { this.holdings = holdings; }
    
    public List<AccountPortfolioSnapshot> getPortfolioSnapshots() { return portfolioSnapshots; }
    public void setPortfolioSnapshots(List<AccountPortfolioSnapshot> portfolioSnapshots) {
        this.portfolioSnapshots = portfolioSnapshots;
    }
    
    public TradingAgent getAgent() { return agent; }
    public void setAgent(TradingAgent agent) { this.agent = agent; }
}