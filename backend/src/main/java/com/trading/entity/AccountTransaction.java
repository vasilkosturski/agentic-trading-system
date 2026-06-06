package com.trading.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

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

    @Enumerated(EnumType.STRING)
    @Column(name = "transaction_type", nullable = false)
    private TransactionType transactionType; // BUY, SELL - MUST be set explicitly!

    @Column(name = "total_amount", nullable = false)
    private Double totalAmount;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    public AccountTransaction(
            TradingAccount account, String symbol, Integer quantity, Double price, Instant timestamp) {
        this.account = account;
        this.symbol = symbol;
        this.quantity = quantity;
        this.price = price;
        this.timestamp = timestamp;
        this.totalAmount = Math.abs(quantity) * price;
    }

    public Double calculateTotal() {
        return Math.abs(quantity) * price;
    }

    public boolean isBuy() {
        return transactionType == TransactionType.BUY;
    }

    public boolean isSell() {
        return transactionType == TransactionType.SELL;
    }

    public void setQuantity(Integer quantity) {
        this.quantity = quantity;
        // Do NOT auto-set transactionType from quantity sign here — service layer
        // must set it explicitly. Inferring from sign caused SELL transactions to
        // be recorded as BUY when quantity was positive.
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
