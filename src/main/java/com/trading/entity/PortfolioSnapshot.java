package com.trading.entity;

public class PortfolioSnapshot {
    private String timestamp;
    private Double value;
    
    // Constructors
    public PortfolioSnapshot() {}
    
    public PortfolioSnapshot(String timestamp, Double value) {
        this.timestamp = timestamp;
        this.value = value;
    }
    
    // Getters and Setters
    public String getTimestamp() { return timestamp; }
    public void setTimestamp(String timestamp) { this.timestamp = timestamp; }
    
    public Double getValue() { return value; }
    public void setValue(Double value) { this.value = value; }
}