package com.trading.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

public class Account {
    private String name;
    private double balance;
    private String strategy;
    private Map<String, Integer> holdings;
    private List<Transaction> transactions;
    
    @JsonProperty("portfolio_value_time_series")
    private List<List<Object>> portfolioValueTimeSeries; // [timestamp, value] pairs
    
    @JsonProperty("total_portfolio_value")
    private Double totalPortfolioValue;
    
    @JsonProperty("total_profit_loss")
    private Double totalProfitLoss;
    
    // Default constructor for Jackson
    public Account() {}
    
    public Account(String name, double balance, String strategy, 
                   Map<String, Integer> holdings, List<Transaction> transactions,
                   List<List<Object>> portfolioValueTimeSeries) {
        this.name = name;
        this.balance = balance;
        this.strategy = strategy;
        this.holdings = holdings;
        this.transactions = transactions;
        this.portfolioValueTimeSeries = portfolioValueTimeSeries;
    }
    
    // Calculate derived values
    public double calculatePortfolioValue() {
        // This would need market data to calculate properly
        // For now, return the stored value or balance
        return totalPortfolioValue != null ? totalPortfolioValue : balance;
    }
    
    public double calculateProfitLoss() {
        return totalProfitLoss != null ? totalProfitLoss : 0.0;
    }
    
    // Getters and setters
    public String getName() {
        return name;
    }
    
    public void setName(String name) {
        this.name = name;
    }
    
    public double getBalance() {
        return balance;
    }
    
    public void setBalance(double balance) {
        this.balance = balance;
    }
    
    public String getStrategy() {
        return strategy;
    }
    
    public void setStrategy(String strategy) {
        this.strategy = strategy;
    }
    
    public Map<String, Integer> getHoldings() {
        return holdings;
    }
    
    public void setHoldings(Map<String, Integer> holdings) {
        this.holdings = holdings;
    }
    
    public List<Transaction> getTransactions() {
        return transactions;
    }
    
    public void setTransactions(List<Transaction> transactions) {
        this.transactions = transactions;
    }
    
    public List<List<Object>> getPortfolioValueTimeSeries() {
        return portfolioValueTimeSeries;
    }
    
    public void setPortfolioValueTimeSeries(List<List<Object>> portfolioValueTimeSeries) {
        this.portfolioValueTimeSeries = portfolioValueTimeSeries;
    }
    
    public Double getTotalPortfolioValue() {
        return totalPortfolioValue;
    }
    
    public void setTotalPortfolioValue(Double totalPortfolioValue) {
        this.totalPortfolioValue = totalPortfolioValue;
    }
    
    public Double getTotalProfitLoss() {
        return totalProfitLoss;
    }
    
    public void setTotalProfitLoss(Double totalProfitLoss) {
        this.totalProfitLoss = totalProfitLoss;
    }
    
    @Override
    public String toString() {
        return "Account{" +
                "name='" + name + '\'' +
                ", balance=" + balance +
                ", strategy='" + strategy + '\'' +
                ", holdings=" + holdings +
                ", totalPortfolioValue=" + totalPortfolioValue +
                ", totalProfitLoss=" + totalProfitLoss +
                '}';
    }
}