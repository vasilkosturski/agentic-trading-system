package com.trading.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public class Transaction {
    private String symbol;
    private int quantity;
    private double price;
    private String timestamp;
    private String rationale;
    
    // Default constructor for Jackson
    public Transaction() {}
    
    public Transaction(String symbol, int quantity, double price, String timestamp, String rationale) {
        this.symbol = symbol;
        this.quantity = quantity;
        this.price = price;
        this.timestamp = timestamp;
        this.rationale = rationale;
    }
    
    public double getTotal() {
        return quantity * price;
    }
    
    // Getters and setters
    public String getSymbol() {
        return symbol;
    }
    
    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }
    
    public int getQuantity() {
        return quantity;
    }
    
    public void setQuantity(int quantity) {
        this.quantity = quantity;
    }
    
    public double getPrice() {
        return price;
    }
    
    public void setPrice(double price) {
        this.price = price;
    }
    
    public String getTimestamp() {
        return timestamp;
    }
    
    public void setTimestamp(String timestamp) {
        this.timestamp = timestamp;
    }
    
    public String getRationale() {
        return rationale;
    }
    
    public void setRationale(String rationale) {
        this.rationale = rationale;
    }
    
    @Override
    public String toString() {
        return Math.abs(quantity) + " shares of " + symbol + " at " + price + " each.";
    }
}