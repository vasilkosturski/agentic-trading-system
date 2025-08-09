package com.trading.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "account_transactions", schema = "trading")
public class AccountTransaction {
    
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
    
    @Column(nullable = false, precision = 15, scale = 2)
    private Double price;
    
    @Column(nullable = false)
    private LocalDateTime timestamp;
    
    @Column(columnDefinition = "TEXT")
    private String rationale;
    
    @Column(name = "transaction_type", nullable = false)
    private String transactionType; // BUY, SELL
    
    @Column(name = "total_amount", nullable = false, precision = 15, scale = 2)
    private Double totalAmount;
    
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();
    
    // Constructors
    public AccountTransaction() {}
    
    public AccountTransaction(TradingAccount account, String symbol, Integer quantity, 
                            Double price, LocalDateTime timestamp, String rationale) {
        this.account = account;
        this.symbol = symbol;
        this.quantity = quantity;
        this.price = price;
        this.timestamp = timestamp;
        this.rationale = rationale;
        this.transactionType = quantity > 0 ? "BUY" : "SELL";
        this.totalAmount = Math.abs(quantity) * price;
    }
    
    // Business methods
    public Double calculateTotal() {
        return Math.abs(quantity) * price;
    }
    
    public boolean isBuy() {
        return quantity > 0;
    }
    
    public boolean isSell() {
        return quantity < 0;
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
        this.transactionType = quantity > 0 ? "BUY" : "SELL";
        if (this.price != null) {
            this.totalAmount = Math.abs(quantity) * this.price;
        }
    }
    
    public Double getPrice() { return price; }
    public void setPrice(Double price) { 
        this.price = price;
        if (this.quantity != null) {
            this.totalAmount = Math.abs(this.quantity) * price;
        }
    }
    
    public LocalDateTime getTimestamp() { return timestamp; }
    public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }
    
    public String getRationale() { return rationale; }
    public void setRationale(String rationale) { this.rationale = rationale; }
    
    public String getTransactionType() { return transactionType; }
    public void setTransactionType(String transactionType) { this.transactionType = transactionType; }
    
    public Double getTotalAmount() { return totalAmount; }
    public void setTotalAmount(Double totalAmount) { this.totalAmount = totalAmount; }
    
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}