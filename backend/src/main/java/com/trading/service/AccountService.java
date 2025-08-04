package com.trading.service;

import com.trading.entity.Account;
import com.trading.entity.AccountData;
import com.trading.entity.Transaction;
import com.trading.entity.PortfolioSnapshot;
import com.trading.repository.AccountRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;
import java.util.ArrayList;
import java.util.List;

@Service
@Transactional
public class AccountService {
    
    @Autowired
    private AccountRepository accountRepository;
    
    @Autowired
    private MarketService marketService;
    
    @Value("${trading.initial-balance:100000.0}")
    private Double initialBalance;
    
    private static final DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    
    public AccountData getAccount(String name) {
        Account account = accountRepository.findByName(name.toLowerCase());
        if (account == null) {
            account = createNewAccount(name);
        }
        return account.toAccountData();
    }
    
    private Account createNewAccount(String name) {
        AccountData accountData = new AccountData(
            name.toLowerCase(),
            initialBalance,
            getDefaultStrategy(name),
            new HashMap<>(),
            new ArrayList<>(),
            new ArrayList<>()
        );
        Account account = Account.fromAccountData(name.toLowerCase(), accountData);
        return accountRepository.save(account);
    }
    
    private String getDefaultStrategy(String name) {
        // Set default strategies based on trader names
        switch (name.toLowerCase()) {
            case "warren": return "Value investing focused on undervalued companies with strong fundamentals";
            case "george": return "Momentum trading with focus on market trends and technical analysis";
            case "ray": return "Systematic approach using quantitative analysis and risk management";
            case "cathie": return "Innovation-focused investing in disruptive technologies and growth companies";
            default: return "Balanced investment approach";
        }
    }
    
    public Double getBalance(String name) {
        return getAccount(name).getBalance();
    }
    
    public Map<String, Integer> getHoldings(String name) {
        return getAccount(name).getHoldings();
    }
    
    public String buyShares(String name, String symbol, Integer quantity, String rationale) {
        try {
            AccountData accountData = getAccount(name);
            Double currentPrice = marketService.getSharePrice(symbol.toUpperCase()).getPrice();
            Double totalCost = currentPrice * quantity;
            
            // Check if account has sufficient balance
            if (accountData.getBalance() < totalCost) {
                return String.format("Insufficient funds. Required: $%.2f, Available: $%.2f",
                    totalCost, accountData.getBalance());
            }
            
            // Update balance
            accountData.setBalance(accountData.getBalance() - totalCost);
            
            // Update holdings
            Map<String, Integer> holdings = accountData.getHoldings();
            holdings.put(symbol.toUpperCase(), holdings.getOrDefault(symbol.toUpperCase(), 0) + quantity);
            
            // Add transaction record
            Transaction transaction = new Transaction(
                symbol.toUpperCase(),
                quantity,
                currentPrice,
                LocalDateTime.now().format(formatter),
                rationale
            );
            accountData.getTransactions().add(transaction);
            
            // Update portfolio snapshot
            updatePortfolioSnapshot(accountData);
            
            // Save to database
            Account account = Account.fromAccountData(name.toLowerCase(), accountData);
            accountRepository.save(account);
            
            return String.format("Successfully bought %d shares of %s at $%.2f each. Total cost: $%.2f",
                quantity, symbol.toUpperCase(), currentPrice, totalCost);
                
        } catch (Exception e) {
            return "Error executing buy order: " + e.getMessage();
        }
    }
    
    public String sellShares(String name, String symbol, Integer quantity, String rationale) {
        try {
            AccountData accountData = getAccount(name);
            Map<String, Integer> holdings = accountData.getHoldings();
            String upperSymbol = symbol.toUpperCase();
            
            // Check if account has sufficient shares
            Integer currentHolding = holdings.getOrDefault(upperSymbol, 0);
            if (currentHolding < quantity) {
                return String.format("Insufficient shares. Requested: %d, Available: %d",
                    quantity, currentHolding);
            }
            
            Double currentPrice = marketService.getSharePrice(upperSymbol).getPrice();
            Double totalRevenue = currentPrice * quantity;
            
            // Update balance
            accountData.setBalance(accountData.getBalance() + totalRevenue);
            
            // Update holdings
            Integer newHolding = currentHolding - quantity;
            if (newHolding == 0) {
                holdings.remove(upperSymbol);
            } else {
                holdings.put(upperSymbol, newHolding);
            }
            
            // Add transaction record (negative quantity for sell)
            Transaction transaction = new Transaction(
                upperSymbol,
                -quantity,
                currentPrice,
                LocalDateTime.now().format(formatter),
                rationale
            );
            accountData.getTransactions().add(transaction);
            
            // Update portfolio snapshot
            updatePortfolioSnapshot(accountData);
            
            // Save to database
            Account account = Account.fromAccountData(name.toLowerCase(), accountData);
            accountRepository.save(account);
            
            return String.format("Successfully sold %d shares of %s at $%.2f each. Total revenue: $%.2f",
                quantity, upperSymbol, currentPrice, totalRevenue);
                
        } catch (Exception e) {
            return "Error executing sell order: " + e.getMessage();
        }
    }
    
    public String changeStrategy(String name, String strategy) {
        try {
            AccountData accountData = getAccount(name);
            accountData.setStrategy(strategy);
            
            Account account = Account.fromAccountData(name.toLowerCase(), accountData);
            accountRepository.save(account);
            
            return String.format("Strategy updated for %s: %s", name, strategy);
        } catch (Exception e) {
            return "Error updating strategy: " + e.getMessage();
        }
    }
    
    public String getAccountReport(String name) {
        try {
            AccountData accountData = getAccount(name);
            Double portfolioValue = calculatePortfolioValue(accountData);
            Double totalInvested = initialBalance - accountData.getBalance();
            Double profitLoss = portfolioValue - initialBalance;
            
            StringBuilder report = new StringBuilder();
            report.append(String.format("=== Account Report for %s ===\n", name.toUpperCase()));
            report.append(String.format("Cash Balance: $%.2f\n", accountData.getBalance()));
            report.append(String.format("Portfolio Value: $%.2f\n", portfolioValue));
            report.append(String.format("Total Account Value: $%.2f\n", accountData.getBalance() + portfolioValue));
            report.append(String.format("Total Invested: $%.2f\n", totalInvested));
            report.append(String.format("Profit/Loss: $%.2f (%.2f%%)\n", profitLoss, (profitLoss/initialBalance)*100));
            report.append(String.format("Strategy: %s\n", accountData.getStrategy()));
            
            report.append("\n=== Holdings ===\n");
            if (accountData.getHoldings().isEmpty()) {
                report.append("No current holdings\n");
            } else {
                for (Map.Entry<String, Integer> holding : accountData.getHoldings().entrySet()) {
                    String symbol = holding.getKey();
                    Integer shares = holding.getValue();
                    Double currentPrice = marketService.getSharePrice(symbol).getPrice();
                    Double value = shares * currentPrice;
                    report.append(String.format("%s: %d shares @ $%.2f = $%.2f\n",
                        symbol, shares, currentPrice, value));
                }
            }
            
            report.append(String.format("\n=== Recent Transactions (Last 5) ===\n"));
            List<Transaction> transactions = accountData.getTransactions();
            if (transactions.isEmpty()) {
                report.append("No transactions yet\n");
            } else {
                int start = Math.max(0, transactions.size() - 5);
                for (int i = start; i < transactions.size(); i++) {
                    Transaction tx = transactions.get(i);
                    String action = tx.getQuantity() > 0 ? "BUY" : "SELL";
                    report.append(String.format("%s: %s %d %s @ $%.2f - %s\n",
                        tx.getTimestamp(), action, Math.abs(tx.getQuantity()),
                        tx.getSymbol(), tx.getPrice(), tx.getRationale()));
                }
            }
            
            return report.toString();
        } catch (Exception e) {
            return "Error generating account report: " + e.getMessage();
        }
    }
    
    public String getStrategy(String name) {
        return getAccount(name).getStrategy();
    }
    
    private Double calculatePortfolioValue(AccountData accountData) {
        Double totalValue = 0.0;
        for (Map.Entry<String, Integer> holding : accountData.getHoldings().entrySet()) {
            String symbol = holding.getKey();
            Integer shares = holding.getValue();
            Double currentPrice = marketService.getSharePrice(symbol).getPrice();
            totalValue += shares * currentPrice;
        }
        return totalValue;
    }
    
    private void updatePortfolioSnapshot(AccountData accountData) {
        Double portfolioValue = calculatePortfolioValue(accountData);
        Double totalValue = accountData.getBalance() + portfolioValue;
        
        PortfolioSnapshot snapshot = new PortfolioSnapshot(
            LocalDateTime.now().format(formatter),
            totalValue
        );
        
        accountData.getPortfolioValueTimeSeries().add(snapshot);
        
        // Keep only last 100 snapshots to avoid excessive data growth
        List<PortfolioSnapshot> snapshots = accountData.getPortfolioValueTimeSeries();
        if (snapshots.size() > 100) {
            snapshots.subList(0, snapshots.size() - 100).clear();
        }
    }
}