package com.trading.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "market")
public class MarketData {
    @Id
    private String date;
    
    @Column(columnDefinition = "TEXT")
    private String data;
    
    // Constructors
    public MarketData() {}
    
    public MarketData(String date, String data) {
        this.date = date;
        this.data = data;
    }
    
    // Getters and Setters
    public String getDate() { return date; }
    public void setDate(String date) { this.date = date; }
    
    public String getData() { return data; }
    public void setData(String data) { this.data = data; }
}