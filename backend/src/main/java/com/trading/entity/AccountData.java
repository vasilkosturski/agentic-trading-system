package com.trading.entity;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class AccountData {
    private String name;
    private Double balance;
    private String strategy;
    private Map<String, Integer> holdings;
    private List<Transaction> transactions;
    private List<PortfolioSnapshot> portfolioValueTimeSeries;
    
    // Constructors
    public AccountData() {}
    
    public AccountData(String name, Double balance, String strategy, 
                      Map<String, Integer> holdings, List<Transaction> transactions, 
                      List<PortfolioSnapshot> portfolioValueTimeSeries) {
        this.name = name;
        this.balance = balance;
        this.strategy = strategy;
        this.holdings = holdings;
        this.transactions = transactions;
        this.portfolioValueTimeSeries = portfolioValueTimeSeries;
    }
    
    // Getters and Setters
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public Double getBalance() { return balance; }
    public void setBalance(Double balance) { this.balance = balance; }
    
    public String getStrategy() { return strategy; }
    public void setStrategy(String strategy) { this.strategy = strategy; }
    
    public Map<String, Integer> getHoldings() { return holdings; }
    public void setHoldings(Map<String, Integer> holdings) { this.holdings = holdings; }
    
    public List<Transaction> getTransactions() { return transactions; }
    public void setTransactions(List<Transaction> transactions) { this.transactions = transactions; }
    
    public List<PortfolioSnapshot> getPortfolioValueTimeSeries() { return portfolioValueTimeSeries; }
    public void setPortfolioValueTimeSeries(List<PortfolioSnapshot> portfolioValueTimeSeries) { 
        this.portfolioValueTimeSeries = portfolioValueTimeSeries; 
    }
}