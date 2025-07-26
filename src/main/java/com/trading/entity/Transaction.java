package com.trading.entity;

public class Transaction {
    private String symbol;
    private Integer quantity;
    private Double price;
    private String timestamp;
    private String rationale;
    
    // Constructors
    public Transaction() {}
    
    public Transaction(String symbol, Integer quantity, Double price, String timestamp, String rationale) {
        this.symbol = symbol;
        this.quantity = quantity;
        this.price = price;
        this.timestamp = timestamp;
        this.rationale = rationale;
    }
    
    public Double total() {
        return quantity * price;
    }
    
    @Override
    public String toString() {
        return Math.abs(quantity) + " shares of " + symbol + " at " + price + " each.";
    }
    
    // Getters and Setters
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { this.quantity = quantity; }
    
    public Double getPrice() { return price; }
    public void setPrice(Double price) { this.price = price; }
    
    public String getTimestamp() { return timestamp; }
    public void setTimestamp(String timestamp) { this.timestamp = timestamp; }
    
    public String getRationale() { return rationale; }
    public void setRationale(String rationale) { this.rationale = rationale; }
}