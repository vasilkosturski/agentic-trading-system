package com.trading.dto;

import java.time.LocalDateTime;

/**
 * DTO for recent trade display in the frontend
 */
public class RecentTradeDto {
    private String agentName;
    private String transactionType; // BUY or SELL
    private String symbol;
    private Integer quantity;
    private Double price;
    private Double totalAmount;
    private LocalDateTime timestamp;
    private String rationale;
    
    // Constructors
    public RecentTradeDto() {}
    
    public RecentTradeDto(String agentName, String transactionType, String symbol, 
                         Integer quantity, Double price, Double totalAmount,
                         LocalDateTime timestamp, String rationale) {
        this.agentName = agentName;
        this.transactionType = transactionType;
        this.symbol = symbol;
        this.quantity = quantity;
        this.price = price;
        this.totalAmount = totalAmount;
        this.timestamp = timestamp;
        this.rationale = rationale;
    }
    
    // Getters and Setters
    public String getAgentName() { return agentName; }
    public void setAgentName(String agentName) { this.agentName = agentName; }
    
    public String getTransactionType() { return transactionType; }
    public void setTransactionType(String transactionType) { this.transactionType = transactionType; }
    
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { this.quantity = quantity; }
    
    public Double getPrice() { return price; }
    public void setPrice(Double price) { this.price = price; }
    
    public Double getTotalAmount() { return totalAmount; }
    public void setTotalAmount(Double totalAmount) { this.totalAmount = totalAmount; }
    
    public LocalDateTime getTimestamp() { return timestamp; }
    public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }
    
    public String getRationale() { return rationale; }
    public void setRationale(String rationale) { this.rationale = rationale; }
}