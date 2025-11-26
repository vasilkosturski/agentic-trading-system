package com.trading.service;

import com.trading.entity.*;
import com.trading.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

@Service
@Transactional
public class AccountService {
    
    private static final Logger logger = LoggerFactory.getLogger(AccountService.class);

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
    
    @Autowired
    private MarketService marketService;

    @Autowired
    private AgentRunRepository agentRunRepository;

    /**
     * Initialize agent and create trading account - should be called when agent starts
     * @param agentName Name of the agent (validated at controller layer)
     * @param initialBalance Initial cash balance (validated at controller layer)
     * @return TradingAccount for the agent
     */
    public TradingAccount initializeAgent(String agentName, Double initialBalance) {
        // Step 1: Check if TradingAgent exists
        Optional<TradingAgent> agentOpt = agentRepository.findByName(agentName);

        if (agentOpt.isPresent()) {
            // Agent exists - check if account exists
            TradingAgent agent = agentOpt.get();
            Optional<TradingAccount> accountOpt = tradingAccountRepository.findByAgentName(agentName);

            if (accountOpt.isPresent()) {
                // Account exists - return it
                return accountOpt.get();
            }
            else {
                return tradingAccountRepository.save(new TradingAccount(agent, initialBalance));
            }
        }

        // Agent doesn't exist - create agent and account
        TradingAgent agent = new TradingAgent(agentName, "Autonomous trading agent");
        agent.setInitialCapital(initialBalance);
        agent = agentRepository.save(agent);

        return tradingAccountRepository.save(new TradingAccount(agent, initialBalance));
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
        Optional<TradingAccount> accountOpt = tradingAccountRepository.findByAgentName(agentName);
        if (accountOpt.isEmpty()) {
            return new HashMap<>();
        }

        List<AccountHolding> holdings = holdingRepository.findByAccount(accountOpt.get());
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
        return buyShares(agentName, symbol, quantity, rationale, null, null, null, null);
    }

    /**
     * Buy shares for an agent with detailed metadata
     */
    public String buyShares(String agentName, String symbol, Integer quantity, String rationale,
                           String fullReasoning, String researchSources, String agentContext, Long runId) {
        TradingAccount account = getAccount(agentName);

        // Check position limit BEFORE buying (max 10 positions per agent)
        List<AccountHolding> currentHoldings = holdingRepository.findByAccount(account);
        long activePositions = currentHoldings.stream()
            .filter(h -> h.getQuantity() > 0)
            .count();

        // Check if adding new position (not adding to existing)
        boolean isNewPosition = currentHoldings.stream()
            .noneMatch(h -> h.getSymbol().equals(symbol) && h.getQuantity() > 0);

        if (isNewPosition && activePositions >= 10) {
            // List current holdings in error message to help agent decide what to sell
            String holdingsList = currentHoldings.stream()
                .filter(h -> h.getQuantity() > 0)
                .map(h -> h.getSymbol())
                .collect(Collectors.joining(", "));

            throw new RuntimeException(
                "❌ POSITION LIMIT REACHED: You currently hold 10 positions (" + holdingsList + "). " +
                "Maximum allowed is 10 positions per agent. " +
                "To buy " + symbol + ", you must first sell one of your existing positions. " +
                "Review your holdings and sell your weakest/lowest-conviction position, then retry this purchase."
            );
        }

        // Get current market price from MarketService
        logger.info("🔍 DEBUGGING: Requesting real market price for {} from MarketService", symbol);
        MarketService.PriceData priceData = marketService.getSharePrice(symbol);
        Double price = priceData.getPrice();
        logger.info("💰 DEBUGGING: Received price for {}: ${} from {} ({})",
            symbol, price, priceData.getDataSource(), priceData.getDataTier());
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
        transaction.setTransactionType(TransactionType.BUY);  // EXPLICIT enum - never derived!
        transaction.setQuantity(quantity);
        transaction.setPrice(price);
        transaction.setRationale(rationale);
        transaction.setFullReasoning(fullReasoning);
        transaction.setResearchSources(researchSources);
        transaction.setAgentContext(agentContext);
        transaction.setTimestamp(Instant.now());

        // Link transaction to agent run if provided
        if (runId != null) {
            AgentRun agentRun = agentRunRepository.findById(runId)
                .orElseThrow(() -> new RuntimeException("Agent run not found: " + runId));
            transaction.setAgentRun(agentRun);
        }

        transactionRepository.save(transaction);
        
        // Update or create holding
        AccountHolding holding = holdingRepository.findByAccountAndSymbol(account, symbol);

        if (holding != null) {
            logger.info("📊 Updating existing holding for {} - {}: current qty={}, adding qty={}",
                agentName, symbol, holding.getQuantity(), quantity);
            // Calculate new average cost
            double currentValue = holding.getQuantity() * holding.getAveragePrice();
            double newValue = currentValue + totalCost;
            int newQuantity = holding.getQuantity() + quantity;

            holding.setQuantity(newQuantity);
            holding.setAveragePrice(newValue / newQuantity);
        } else {
            logger.info("🆕 Creating NEW holding for {} - {}: qty={}, avgPrice=${}",
                agentName, symbol, quantity, price);
            holding = new AccountHolding();
            holding.setAccount(account);
            holding.setSymbol(symbol);
            holding.setQuantity(quantity);
            holding.setAveragePrice(price);
        }

        try {
            AccountHolding savedHolding = holdingRepository.save(holding);
            logger.info("✅ Successfully saved holding for {} - {}: id={}, qty={}",
                agentName, symbol, savedHolding.getId(), savedHolding.getQuantity());
        } catch (Exception e) {
            logger.error("❌ CRITICAL: Failed to save holding for {} - {}: {}",
                agentName, symbol, e.getMessage(), e);
            throw new RuntimeException("Failed to save holding: " + e.getMessage(), e);
        }

        return "Successfully bought " + quantity + " shares of " + symbol + " at $" + String.format("%.2f", price) + " each";
    }

    /**
     * Sell shares for an agent
     */
    public String sellShares(String agentName, String symbol, Integer quantity, String rationale) {
        return sellShares(agentName, symbol, quantity, rationale, null, null, null, null);
    }

    /**
     * Sell shares for an agent with detailed metadata
     */
    public String sellShares(String agentName, String symbol, Integer quantity, String rationale,
                            String fullReasoning, String researchSources, String agentContext, Long runId) {
        TradingAccount account = getAccount(agentName);

        // Check if we have enough shares
        AccountHolding holding = holdingRepository.findByAccountAndSymbol(account, symbol);
        if (holding == null || holding.getQuantity() < quantity) {
            int available = holding != null ? holding.getQuantity() : 0;
            throw new RuntimeException("Cannot sell " + quantity + " shares of " + symbol + 
                ". Only have " + available + " shares available");
        }
        
        // Get current market price from MarketService
        logger.info("🔍 DEBUGGING: Requesting real market price for {} from MarketService", symbol);
        MarketService.PriceData priceData = marketService.getSharePrice(symbol);
        Double price = priceData.getPrice();
        logger.info("💰 DEBUGGING: Received price for {}: ${} from {} ({})",
            symbol, price, priceData.getDataSource(), priceData.getDataTier());
        Double totalProceeds = price * quantity;
        
        // Update account balance
        account.setBalance(account.getBalance() + totalProceeds);
        tradingAccountRepository.save(account);
        
        // Create transaction record
        AccountTransaction transaction = new AccountTransaction();
        transaction.setAccount(account);
        transaction.setSymbol(symbol);
        transaction.setTransactionType(TransactionType.SELL);  // EXPLICIT enum - never derived!
        transaction.setQuantity(quantity);
        transaction.setPrice(price);
        transaction.setRationale(rationale);
        transaction.setFullReasoning(fullReasoning);
        transaction.setResearchSources(researchSources);
        transaction.setAgentContext(agentContext);
        transaction.setTimestamp(Instant.now());

        // Link transaction to agent run if provided
        if (runId != null) {
            AgentRun agentRun = agentRunRepository.findById(runId)
                .orElseThrow(() -> new RuntimeException("Agent run not found: " + runId));
            transaction.setAgentRun(agentRun);
        }

        transactionRepository.save(transaction);
        
        // Update holding
        holding.setQuantity(holding.getQuantity() - quantity);

        if (holding.getQuantity() == 0) {
            holdingRepository.delete(holding);
        } else {
            holdingRepository.save(holding);
        }

        return "Successfully sold " + quantity + " shares of " + symbol + " at $" + String.format("%.2f", price) + " each";
    }

    // changeStrategy method removed - using hardcoded strategies only

    /**
     * Get account report for an agent
     */
    public String getAccountReport(String agentName) {
        try {
            TradingAccount account = getAccount(agentName);
            
            // Get current holdings with live market prices
            List<AccountHolding> holdings = holdingRepository.findByAccount(account);
            Double holdingsValue = holdings.stream()
                .mapToDouble(h -> {
                    try {
                        MarketService.PriceData priceData = marketService.getSharePrice(h.getSymbol());
                        return h.getQuantity() * priceData.getPrice();
                    } catch (Exception e) {
                        // Fallback to average purchase price if API fails
                        return h.getQuantity() * h.getAveragePrice();
                    }
                })
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
        Optional<TradingAccount> accountOpt = tradingAccountRepository.findByAgentName(agentName);
        if (accountOpt.isEmpty()) {
            return balance;
        }

        // Calculate holdings value using LIVE market prices (cached for 60 minutes)
        Double holdingsValue = holdingRepository.findByAccount(accountOpt.get()).stream()
            .mapToDouble(h -> {
                try {
                    MarketService.PriceData priceData = marketService.getSharePrice(h.getSymbol());
                    return h.getQuantity() * priceData.getPrice();
                } catch (Exception e) {
                    // Fallback to average purchase price if API fails
                    return h.getQuantity() * h.getAveragePrice();
                }
            })
            .sum();

        return balance + holdingsValue;
    }

    /**
     * Create portfolio snapshot for an agent
     */
    public void createPortfolioSnapshot(String agentName) {
        TradingAccount account = getAccount(agentName);
        createPortfolioSnapshot(account);
    }

    /**
     * Get trading account for an agent - expects account to already exist
     */
    private TradingAccount getAccount(String agentName) {
        return tradingAccountRepository.findByAgentName(agentName)
            .orElseThrow(() -> new RuntimeException("Trading account not found for agent: " + agentName +
                ". Agent must be initialized before trading operations."));
    }


    /**
     * Update agent activity timestamp (called on every cycle check via trading_system.py)
     * Single source of truth for lastActivity updates
     */
    public void updateAgentActivity(String agentName) {
        Optional<TradingAgent> agentOpt = agentRepository.findByName(agentName);
        if (agentOpt.isPresent()) {
            TradingAgent agent = agentOpt.get();
            agent.updateActivity();
            agentRepository.save(agent);
            logger.debug("Updated activity timestamp for agent: {}", agentName);
        } else {
            throw new RuntimeException("Agent not found: " + agentName);
        }
    }

    /**
     * Create portfolio snapshot for an account
     */
    private void createPortfolioSnapshot(TradingAccount account) {
        // Calculate total portfolio value using live market prices
        List<AccountHolding> holdings = holdingRepository.findByAccount(account);
        double holdingsValue = holdings.stream()
            .mapToDouble(h -> {
                try {
                    MarketService.PriceData priceData = marketService.getSharePrice(h.getSymbol());
                    return h.getQuantity() * priceData.getPrice();
                } catch (Exception e) {
                    // Fallback to average purchase price if API fails
                    return h.getQuantity() * h.getAveragePrice();
                }
            })
            .sum();

        double totalValue = account.getBalance() + holdingsValue;

        AccountPortfolioSnapshot snapshot = new AccountPortfolioSnapshot();
        snapshot.setAccount(account);
        snapshot.setTimestamp(Instant.now());
        snapshot.setTotalValue(totalValue);
        snapshot.setCashBalance(account.getBalance());
        snapshot.setHoldingsValue(holdingsValue);

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