package com.trading.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.trading.model.Account;
import com.trading.model.Transaction;
import com.trading.repository.AccountRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Service
public class AccountService {

    @Autowired
    private AccountRepository accountRepository;

    private final ObjectMapper objectMapper = new ObjectMapper();

    public Double getBalance(String name) {
        Optional<Account> accountOpt = accountRepository.findByName(name.toLowerCase());
        if (accountOpt.isEmpty()) {
            throw new RuntimeException("Account not found: " + name);
        }
        return accountOpt.get().getBalance();
    }

    public Map<String, Integer> getHoldings(String name) {
        Optional<Account> accountOpt = accountRepository.findByName(name.toLowerCase());
        if (accountOpt.isEmpty()) {
            throw new RuntimeException("Account not found: " + name);
        }
        Map<String, Integer> holdings = accountOpt.get().getHoldings();
        return holdings != null ? holdings : new HashMap<>();
    }

    public String buyShares(String name, String symbol, Integer quantity, String rationale) {
        Optional<Account> accountOpt = accountRepository.findByName(name.toLowerCase());
        if (accountOpt.isEmpty()) {
            throw new RuntimeException("Account not found: " + name);
        }
        
        Account account = accountOpt.get();
        
        // Get current balance and holdings
        double balance = account.getBalance();
        Map<String, Integer> holdings = account.getHoldings();
        if (holdings == null) holdings = new HashMap<>();
        
        List<Transaction> transactions = account.getTransactions();
        if (transactions == null) transactions = new ArrayList<>();
        
        // Mock price calculation (in real system, would get from market data)
        Double price = getMockPrice(symbol);
        Double totalCost = price * quantity;
        
        if (totalCost > balance) {
            throw new RuntimeException("Insufficient funds to buy " + quantity + " shares of " + symbol);
        }
        
        // Update balance and holdings
        account.setBalance(balance - totalCost);
        holdings.put(symbol, holdings.getOrDefault(symbol, 0) + quantity);
        account.setHoldings(holdings);
        
        // Add transaction
        Transaction transaction = new Transaction();
        transaction.setSymbol(symbol);
        transaction.setQuantity(quantity);
        transaction.setPrice(price);
        transaction.setTimestamp(LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
        transaction.setRationale(rationale);
        transactions.add(transaction);
        account.setTransactions(transactions);
        
        // Save updated account
        accountRepository.save(account);
        
        return "Successfully bought " + quantity + " shares of " + symbol + " at $" + price + " each";
    }

    public String sellShares(String name, String symbol, Integer quantity, String rationale) {
        Optional<Account> accountOpt = accountRepository.findByName(name.toLowerCase());
        if (accountOpt.isEmpty()) {
            throw new RuntimeException("Account not found: " + name);
        }
        
        Account account = accountOpt.get();
        
        // Get current balance and holdings
        double balance = account.getBalance();
        Map<String, Integer> holdings = account.getHoldings();
        if (holdings == null) holdings = new HashMap<>();
        
        List<Transaction> transactions = account.getTransactions();
        if (transactions == null) transactions = new ArrayList<>();
        
        // Check if we have enough shares
        Integer currentHoldings = holdings.getOrDefault(symbol, 0);
        if (currentHoldings < quantity) {
            throw new RuntimeException("Cannot sell " + quantity + " shares of " + symbol + ". Only have " + currentHoldings + " shares");
        }
        
        // Mock price calculation (in real system, would get from market data)
        Double price = getMockPrice(symbol);
        Double totalProceeds = price * quantity;
        
        // Update balance and holdings
        account.setBalance(balance + totalProceeds);
        holdings.put(symbol, currentHoldings - quantity);
        if (holdings.get(symbol) == 0) {
            holdings.remove(symbol);
        }
        account.setHoldings(holdings);
        
        // Add transaction (negative quantity for sell)
        Transaction transaction = new Transaction();
        transaction.setSymbol(symbol);
        transaction.setQuantity(-quantity);
        transaction.setPrice(price);
        transaction.setTimestamp(LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
        transaction.setRationale(rationale);
        transactions.add(transaction);
        account.setTransactions(transactions);
        
        // Save updated account
        accountRepository.save(account);
        
        return "Successfully sold " + quantity + " shares of " + symbol + " at $" + price + " each";
    }

    public String changeStrategy(String name, String strategy) {
        Optional<Account> accountOpt = accountRepository.findByName(name.toLowerCase());
        if (accountOpt.isEmpty()) {
            throw new RuntimeException("Account not found: " + name);
        }
        
        Account account = accountOpt.get();
        account.setStrategy(strategy);
        
        // Save updated account
        accountRepository.save(account);
        
        return "Successfully changed strategy for " + name;
    }

    public String getAccountReport(String name) {
        try {
            Optional<Account> accountOpt = accountRepository.findByName(name.toLowerCase());
            if (accountOpt.isEmpty()) {
                throw new RuntimeException("Account not found: " + name);
            }
            
            Account account = accountOpt.get();
            
            // Calculate portfolio value
            double balance = account.getBalance();
            Map<String, Integer> holdings = account.getHoldings();
            if (holdings == null) holdings = new HashMap<>();
            
            double portfolioValue = balance;
            for (Map.Entry<String, Integer> holding : holdings.entrySet()) {
                portfolioValue += getMockPrice(holding.getKey()) * holding.getValue();
            }
            
            account.setTotalPortfolioValue(portfolioValue);
            account.setTotalProfitLoss(portfolioValue - 10000.0); // Assuming initial balance was 10000
            
            return objectMapper.writeValueAsString(account);
        } catch (Exception e) {
            throw new RuntimeException("Error getting account report for " + name + ": " + e.getMessage());
        }
    }

    public String getStrategy(String name) {
        Optional<Account> accountOpt = accountRepository.findByName(name.toLowerCase());
        if (accountOpt.isEmpty()) {
            throw new RuntimeException("Account not found: " + name);
        }
        
        return accountOpt.get().getStrategy();
    }

    private Double getMockPrice(String symbol) {
        // Mock prices for testing - in real system would get from market data service
        Map<String, Double> mockPrices = new HashMap<>();
        mockPrices.put("AAPL", 155.0);
        mockPrices.put("GOOGL", 2800.0);
        mockPrices.put("MSFT", 380.0);
        mockPrices.put("TSLA", 210.0);
        mockPrices.put("AMZN", 3200.0);
        mockPrices.put("NVDA", 450.0);
        mockPrices.put("META", 320.0);
        mockPrices.put("NFLX", 400.0);
        mockPrices.put("SPY", 425.0);
        mockPrices.put("QQQ", 350.0);
        mockPrices.put("BRK.B", 410.0);
        mockPrices.put("GLD", 185.0);
        mockPrices.put("VTI", 225.0);
        mockPrices.put("BND", 87.0);
        mockPrices.put("VEA", 52.0);
        mockPrices.put("ARKK", 65.0);
        mockPrices.put("COIN", 125.0);
        
        return mockPrices.getOrDefault(symbol, 100.0);
    }
}