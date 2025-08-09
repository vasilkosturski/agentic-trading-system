package com.trading.entity;

import jakarta.persistence.*;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "market_data", schema = "trading")
public class MarketData {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "market_date", nullable = false, unique = true)
    private LocalDate marketDate;
    
    @Column(name = "data_json", columnDefinition = "JSONB")
    private String dataJson;
    
    @Column(name = "data_source")
    private String dataSource = "UNKNOWN";
    
    @Column(name = "symbols_count")
    private Integer symbolsCount;
    
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();
    
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt = LocalDateTime.now();
    
    // Constructors
    public MarketData() {}
    
    public MarketData(LocalDate marketDate, String dataJson) {
        this.marketDate = marketDate;
        this.dataJson = dataJson;
    }
    
    public MarketData(String date, String data) {
        // Backward compatibility constructor
        this.marketDate = LocalDate.parse(date);
        this.dataJson = data;
    }
    
    // JPA lifecycle callbacks
    @PreUpdate
    public void preUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
    
    // Business methods
    public boolean hasData() {
        return dataJson != null && !dataJson.trim().isEmpty();
    }
    
    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    
    public LocalDate getMarketDate() { return marketDate; }
    public void setMarketDate(LocalDate marketDate) { this.marketDate = marketDate; }
    
    public String getDataJson() { return dataJson; }
    public void setDataJson(String dataJson) { this.dataJson = dataJson; }
    
    public String getDataSource() { return dataSource; }
    public void setDataSource(String dataSource) { this.dataSource = dataSource; }
    
    public Integer getSymbolsCount() { return symbolsCount; }
    public void setSymbolsCount(Integer symbolsCount) { this.symbolsCount = symbolsCount; }
    
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
    
    // Backward compatibility methods
    public String getDate() {
        return marketDate != null ? marketDate.toString() : null;
    }
    
    public void setDate(String date) {
        this.marketDate = LocalDate.parse(date);
    }
    
    public String getData() { return dataJson; }
    public void setData(String data) { this.dataJson = data; }
}