package com.trading.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.time.Instant;

@Entity
@Table(name = "account_transactions", schema = "trading")
@Getter
@Setter
@NoArgsConstructor
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
    
    @Column(nullable = false)
    private Double price;
    
    @Column(nullable = false)
    private Instant timestamp;

    @Column(columnDefinition = "TEXT")
    private String rationale;

    @Column(name = "full_reasoning", columnDefinition = "TEXT")
    private String fullReasoning;

    @Column(name = "research_sources", columnDefinition = "TEXT")
    private String researchSources; // JSON array of research sources

    @Column(name = "agent_context", columnDefinition = "TEXT")
    private String agentContext; // JSON object with portfolio state before trade

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "agent_run_id")
    private AgentRun agentRun; // Link to the agent run that created this transaction

    @Enumerated(EnumType.STRING)
    @Column(name = "transaction_type", nullable = false)
    private TransactionType transactionType; // BUY, SELL - MUST be set explicitly!

    @Column(name = "total_amount", nullable = false)
    private Double totalAmount;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();
    
    // Constructor with parameters
    // NOTE: This constructor does NOT set transactionType - it must be set explicitly
    public AccountTransaction(TradingAccount account, String symbol, Integer quantity,
                            Double price, Instant timestamp, String rationale) {
        this.account = account;
        this.symbol = symbol;
        this.quantity = quantity;
        this.price = price;
        this.timestamp = timestamp;
        this.rationale = rationale;
        // transactionType must be set explicitly after construction
        this.totalAmount = Math.abs(quantity) * price;
    }
    
    // Business methods
    public Double calculateTotal() {
        return Math.abs(quantity) * price;
    }
    
    public boolean isBuy() {
        return transactionType == TransactionType.BUY;
    }
    
    public boolean isSell() {
        return transactionType == TransactionType.SELL;
    }
    
    // Custom setters that need business logic
    public void setQuantity(Integer quantity) { 
        this.quantity = quantity;
        // IMPORTANT: Do NOT auto-set transactionType here!
        // Transaction type must be set explicitly by the service layer.
        // Setting it based on quantity sign caused critical bug where SELL 
        // transactions were recorded as BUY because quantity was positive.
        if (this.price != null) {
            this.totalAmount = Math.abs(quantity) * this.price;
        }
    }
    
    public void setPrice(Double price) { 
        this.price = price;
        if (this.quantity != null) {
            this.totalAmount = Math.abs(this.quantity) * price;
        }
    }
}