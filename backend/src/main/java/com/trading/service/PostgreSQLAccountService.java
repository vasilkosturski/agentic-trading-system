package com.trading.service;

import com.trading.entity.*;
import com.trading.repository.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
@Transactional
public class PostgreSQLAccountService {

    @Autowired
    private TradingAccountRepository tradingAccountRepository;
    
    @Autowired
    private AccountTransactionRepository transactionRepository;
    
    @Autowired
    private AccountHoldingRepository holdingRepository;
    
    @Autowired
    private AccountPortfolioSnapshotRepository snapshotRepository;
    
    @Autowired
    private TradingAgentRepository agentRepository;

    /**
     * Initialize agent and create trading account - should be called when agent starts
     */
    public TradingAccount initializeAgent(String agentName, Double initialBalance) {
        // Check if agent already exists
        TradingAccount existingAccount = tradingAccountRepository.findByName(agentName);
        if (existingAccount != null) {
            return existingAccount;
        }
        
        // Create or get the trading agent
        Optional<TradingAgent> agentOpt = agentRepository.findByName(agentName);
        TradingAgent agent;
        if (agentOpt.isPresent()) {
            agent = agentOpt.get();
        } else {
            agent = new TradingAgent(agentName, "Autonomous trading agent");
            agent = agentRepository.save(agent);
        }
        
        // Create trading account
        TradingAccount account = new TradingAccount();
        account.setName(agentName);
        account.setBalance(initialBalance != null ? initialBalance : 100000.0);
        account.setAgent(agent);
        
        account = tradingAccountRepository.save(account);
        
        // Create initial portfolio snapshot
        createPortfolioSnapshot(account, "INITIALIZATION");
        
        return account;
    }

    /**
     * Get account balance for an agent
     */
    public Double getBalance(String agentName) {
        TradingAccount account = getAccount(agentName);
        return account.getBalance();
    }

    /**
     * Get holdings for an agent as Map<Symbol, Quantity>
     */
    public Map<String, Integer> getHoldings(String agentName) {
        TradingAccount account = tradingAccountRepository.findByName(agentName);
        if (account == null) {
            return new HashMap<>();
        }
        
        List<AccountHolding> holdings = holdingRepository.findByAccount(account);
        Map<String, Integer> holdingsMap = new HashMap<>();
        
        for (AccountHolding holding : holdings) {
            if (holding.getQuantity() > 0) {
                holdingsMap.put(holding.getSymbol(), holding.getQuantity());
            }
        }
        
        return holdingsMap;
    }

    /**
     * Buy shares for an agent
     */
    public String buyShares(String agentName, String symbol, Integer quantity, String rationale) {
        TradingAccount account = getAccount(agentName);
        
        // Get current market price (mock for now)
        Double price = getMockPrice(symbol);
        Double totalCost = price * quantity;
        
        // Check if sufficient funds
        if (totalCost > account.getBalance()) {
            throw new RuntimeException("Insufficient funds to buy " + quantity + " shares of " + symbol + 
                ". Required: $" + String.format("%.2f", totalCost) + ", Available: $" + String.format("%.2f", account.getBalance()));
        }
        
        // Update account balance
        account.setBalance(account.getBalance() - totalCost);
        tradingAccountRepository.save(account);
        
        // Create transaction record
        AccountTransaction transaction = new AccountTransaction();
        transaction.setAccount(account);
        transaction.setSymbol(symbol);
        transaction.setTransactionType("BUY");
        transaction.setQuantity(quantity);
        transaction.setPrice(price);
        transaction.setRationale(rationale);
        transaction.setTimestamp(LocalDateTime.now());
        transactionRepository.save(transaction);
        
        // Update or create holding
        AccountHolding holding = holdingRepository.findByAccountAndSymbol(account, symbol);
        
        if (holding != null) {
            // Calculate new average cost
            double currentValue = holding.getQuantity() * holding.getAveragePrice();
            double newValue = currentValue + totalCost;
            int newQuantity = holding.getQuantity() + quantity;
            
            holding.setQuantity(newQuantity);
            holding.setAveragePrice(newValue / newQuantity);
            holding.setCurrentPrice(price);
        } else {
            holding = new AccountHolding();
            holding.setAccount(account);
            holding.setSymbol(symbol);
            holding.setQuantity(quantity);
            holding.setAveragePrice(price);
            holding.setCurrentPrice(price);
        }
        
        // Calculate market metrics
        holding.calculateMarketMetrics();
        holdingRepository.save(holding);
        
        // Update agent statistics
        updateAgentStatistics(agentName);
        
        // Create portfolio snapshot
        createPortfolioSnapshot(account, "TRANSACTION");
        
        return "Successfully bought " + quantity + " shares of " + symbol + " at $" + String.format("%.2f", price) + " each";
    }

    /**
     * Sell shares for an agent
     */
    public String sellShares(String agentName, String symbol, Integer quantity, String rationale) {
        TradingAccount account = getAccount(agentName);
        
        // Check if we have enough shares
        AccountHolding holding = holdingRepository.findByAccountAndSymbol(account, symbol);
        if (holding == null || holding.getQuantity() < quantity) {
            int available = holding != null ? holding.getQuantity() : 0;
            throw new RuntimeException("Cannot sell " + quantity + " shares of " + symbol + 
                ". Only have " + available + " shares available");
        }
        
        Double price = getMockPrice(symbol);
        Double totalProceeds = price * quantity;
        
        // Update account balance
        account.setBalance(account.getBalance() + totalProceeds);
        tradingAccountRepository.save(account);
        
        // Create transaction record
        AccountTransaction transaction = new AccountTransaction();
        transaction.setAccount(account);
        transaction.setSymbol(symbol);
        transaction.setTransactionType("SELL");
        transaction.setQuantity(quantity);
        transaction.setPrice(price);
        transaction.setRationale(rationale);
        transaction.setTimestamp(LocalDateTime.now());
        transactionRepository.save(transaction);
        
        // Update holding
        holding.setQuantity(holding.getQuantity() - quantity);
        holding.setCurrentPrice(price);
        
        if (holding.getQuantity() == 0) {
            holdingRepository.delete(holding);
        } else {
            holding.calculateMarketMetrics();
            holdingRepository.save(holding);
        }
        
        // Update agent statistics
        updateAgentStatistics(agentName);
        
        // Create portfolio snapshot
        createPortfolioSnapshot(account, "TRANSACTION");
        
        return "Successfully sold " + quantity + " shares of " + symbol + " at $" + String.format("%.2f", price) + " each";
    }

    // changeStrategy method removed - using hardcoded strategies only

    /**
     * Get account report for an agent
     */
    public String getAccountReport(String agentName) {
        try {
            TradingAccount account = getAccount(agentName);
            
            // Get current holdings
            List<AccountHolding> holdings = holdingRepository.findByAccount(account);
            Double holdingsValue = holdings.stream()
                .mapToDouble(h -> h.getQuantity() * h.getCurrentPrice())
                .sum();
            
            // Calculate total portfolio value
            Double totalValue = account.getBalance() + holdingsValue;
            
            // Get recent transactions
            List<AccountTransaction> recentTransactions = transactionRepository
                .findByAccountOrderByTimestampDesc(account)
                .stream()
                .limit(10)
                .collect(Collectors.toList());
            
            // Build report
            Map<String, Object> report = new HashMap<>();
            report.put("agentName", agentName);
            report.put("balance", account.getBalance());
            report.put("holdingsValue", holdingsValue);
            report.put("totalPortfolioValue", totalValue);
            report.put("initialBalance", 100000.0); // Default initial balance
            report.put("totalProfitLoss", totalValue - 100000.0);
            report.put("profitLossPercent", ((totalValue - 100000.0) / 100000.0) * 100);
            report.put("lastUpdated", account.getUpdatedAt());
            report.put("holdingsCount", holdings.size());
            report.put("transactionCount", transactionRepository.countByAccount(account));
            
            // Convert to JSON-like string (simplified)
            return buildReportString(report);
            
        } catch (Exception e) {
            throw new RuntimeException("Error getting account report for " + agentName + ": " + e.getMessage());
        }
    }

    // getStrategy method removed - using hardcoded strategies only

    /**
     * Get total portfolio value for an agent
     */
    public Double getTotalPortfolioValue(String agentName) {
        Double balance = getBalance(agentName);
        TradingAccount account = tradingAccountRepository.findByName(agentName);
        if (account == null) {
            return balance;
        }
        
        Double holdingsValue = holdingRepository.findByAccount(account).stream()
            .mapToDouble(h -> h.getQuantity() * h.getCurrentPrice())
            .sum();
        
        return balance + holdingsValue;
    }

    /**
     * Create portfolio snapshot for an agent
     */
    public void createPortfolioSnapshot(String agentName) {
        TradingAccount account = getAccount(agentName);
        createPortfolioSnapshot(account, "MANUAL");
    }

    /**
     * Get trading account for an agent - expects account to already exist
     */
    private TradingAccount getAccount(String agentName) {
        TradingAccount account = tradingAccountRepository.findByName(agentName);
        if (account == null) {
            throw new RuntimeException("Trading account not found for agent: " + agentName +
                ". Agent must be initialized before trading operations.");
        }
        return account;
    }

    /**
     * Mock prices for testing
     */
    private Double getMockPrice(String symbol) {
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

    /**
     * Update agent statistics
     */
    private void updateAgentStatistics(String agentName) {
        Optional<TradingAgent> agentOpt = agentRepository.findByName(agentName);
        if (agentOpt.isPresent()) {
            TradingAgent agent = agentOpt.get();
            TradingAccount account = tradingAccountRepository.findByName(agentName);
            if (account != null) {
                Long totalTrades = transactionRepository.countByAccount(account);
                agent.setTotalTrades(totalTrades.intValue());
                
                // Calculate basic performance metrics
                Double totalValue = getTotalPortfolioValue(agentName);
                Double totalPnl = totalValue - 100000.0; // Assume 100k initial
                agent.setTotalPnl(totalPnl);
                
                // Simple win rate calculation (could be improved)
                if (totalTrades > 0) {
                    agent.setWinRate(totalPnl > 0 ? 60.0 : 40.0); // Simplified
                }
                
                agent.updateActivity();
                agentRepository.save(agent);
            }
        }
    }

    /**
     * Create portfolio snapshot for an account
     */
    private void createPortfolioSnapshot(TradingAccount account, String snapshotType) {
        // Calculate total portfolio value
        List<AccountHolding> holdings = holdingRepository.findByAccount(account);
        double holdingsValue = holdings.stream()
            .mapToDouble(h -> h.getQuantity() * h.getCurrentPrice())
            .sum();
        
        double totalValue = account.getBalance() + holdingsValue;
        
        AccountPortfolioSnapshot snapshot = new AccountPortfolioSnapshot();
        snapshot.setAccount(account);
        snapshot.setTimestamp(LocalDateTime.now());
        snapshot.setTotalValue(totalValue);
        snapshot.setCashBalance(account.getBalance());
        snapshot.setHoldingsValue(holdingsValue);
        snapshot.setSnapshotType(snapshotType);
        
        // Calculate P&L if we have previous snapshots
        AccountPortfolioSnapshot previousSnapshot = snapshotRepository
            .findTopByAccountOrderByTimestampDesc(account);
        if (previousSnapshot != null) {
            snapshot.calculateMetrics(100000.0, previousSnapshot.getTotalValue()); // Assume 100k initial
        }
        
        snapshotRepository.save(snapshot);
    }

    /**
     * Build report string from map
     */
    private String buildReportString(Map<String, Object> report) {
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        for (Map.Entry<String, Object> entry : report.entrySet()) {
            sb.append("  \"").append(entry.getKey()).append("\": ");
            if (entry.getValue() instanceof String) {
                sb.append("\"").append(entry.getValue()).append("\"");
            } else {
                sb.append(entry.getValue());
            }
            sb.append(",\n");
        }
        if (sb.length() > 2) {
            sb.setLength(sb.length() - 2); // Remove last comma
        }
        sb.append("\n}");
        return sb.toString();
    }
}