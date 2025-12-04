package com.trading.service;

import com.trading.entity.*;
import com.trading.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Executes buy trade operations.
 * Extracted from AccountService for better testability and single responsibility.
 */
@Service
@Transactional
public class BuyTradeExecutor {
    
    private static final Logger logger = LoggerFactory.getLogger(BuyTradeExecutor.class);
    private static final int MAX_POSITIONS_PER_AGENT = 10;

    @Autowired
    private TradingAccountRepository tradingAccountRepository;
    
    @Autowired
    private AccountTransactionRepository transactionRepository;
    
    @Autowired
    private AccountHoldingRepository holdingRepository;
    
    @Autowired
    private MarketService marketService;

    @Autowired
    private AgentRunRepository agentRunRepository;

    /**
     * Execute a buy trade for an agent
     * @param agentName Name of the agent
     * @param symbol Stock symbol to buy
     * @param quantity Number of shares to buy
     * @param runId REQUIRED - Every transaction must be linked to an agent run
     * @return Success message
     */
    public String executeBuy(String agentName, String symbol, Integer quantity, Long runId) {
        if (runId == null) {
            throw new IllegalArgumentException("runId is required - every transaction must be linked to an agent run");
        }
        
        TradingAccount account = getAccount(agentName);

        // Check position limit BEFORE buying (max 10 positions per agent)
        validatePositionLimit(account, symbol);

        // Get current market price from MarketService
        Double price = fetchMarketPrice(symbol);
        Double totalCost = price * quantity;

        // Check if sufficient funds
        validateSufficientFunds(account, symbol, quantity, totalCost);
        
        // Update account balance
        account.setBalance(account.getBalance() - totalCost);
        tradingAccountRepository.save(account);
        
        // Create and save transaction
        createTransaction(account, symbol, quantity, price, runId);
        
        // Update or create holding
        updateHolding(account, symbol, quantity, price, totalCost, agentName);

        return "Successfully bought " + quantity + " shares of " + symbol + " at $" + String.format("%.2f", price) + " each";
    }

    /**
     * Validate that adding this position won't exceed the 10 position limit
     */
    private void validatePositionLimit(TradingAccount account, String symbol) {
        List<AccountHolding> currentHoldings = holdingRepository.findActiveHoldingsByAccount(account);
        long activePositions = currentHoldings.size();

        // Check if adding new position (not adding to existing)
        boolean isNewPosition = currentHoldings.stream()
            .noneMatch(h -> h.getSymbol().equals(symbol));

        if (isNewPosition && activePositions >= MAX_POSITIONS_PER_AGENT) {
            // List current holdings in error message to help agent decide what to sell
            String holdingsList = currentHoldings.stream()
                .map(h -> h.getSymbol())
                .collect(Collectors.joining(", "));

            throw new RuntimeException(
                "❌ POSITION LIMIT REACHED: You currently hold " + MAX_POSITIONS_PER_AGENT + " positions (" + holdingsList + "). " +
                "Maximum allowed is " + MAX_POSITIONS_PER_AGENT + " positions per agent. " +
                "To buy " + symbol + ", you must first sell one of your existing positions. " +
                "Review your holdings and sell your weakest/lowest-conviction position, then retry this purchase."
            );
        }
    }

    /**
     * Validate that account has sufficient funds for the purchase
     */
    private void validateSufficientFunds(TradingAccount account, String symbol, Integer quantity, Double totalCost) {
        if (totalCost > account.getBalance()) {
            throw new RuntimeException("Insufficient funds to buy " + quantity + " shares of " + symbol +
                ". Required: $" + String.format("%.2f", totalCost) + ", Available: $" + String.format("%.2f", account.getBalance()));
        }
    }

    /**
     * Create and save the transaction record
     */
    private void createTransaction(TradingAccount account, String symbol, Integer quantity, Double price, Long runId) {
        AccountTransaction transaction = new AccountTransaction();
        transaction.setAccount(account);
        transaction.setSymbol(symbol);
        transaction.setTransactionType(TransactionType.BUY);
        transaction.setQuantity(quantity);
        transaction.setPrice(price);
        transaction.setTimestamp(Instant.now());

        // Link transaction to agent run (REQUIRED)
        AgentRun agentRun = agentRunRepository.findById(runId)
            .orElseThrow(() -> new RuntimeException("Agent run not found: " + runId));
        transaction.setAgentRun(agentRun);

        transactionRepository.save(transaction);
    }

    /**
     * Update or create the holding for this buy trade
     */
    private void updateHolding(TradingAccount account, String symbol, Integer quantity, Double price, Double totalCost, String agentName) {
        AccountHolding holding = holdingRepository.findByAccountAndSymbol(account, symbol);

        if (holding != null) {
            updateExistingHolding(holding, quantity, totalCost, agentName, symbol);
        } else {
            holding = createNewHolding(account, symbol, quantity, price, agentName);
        }

        AccountHolding savedHolding = holdingRepository.save(holding);
        logger.info("✅ Successfully saved holding for {} - {}: id={}, qty={}",
            agentName, symbol, savedHolding.getId(), savedHolding.getQuantity());
    }

    /**
     * Update an existing holding with new shares
     */
    private void updateExistingHolding(AccountHolding holding, Integer quantity, Double totalCost, String agentName, String symbol) {
        logger.info("📊 Updating existing holding for {} - {}: current qty={}, adding qty={}",
            agentName, symbol, holding.getQuantity(), quantity);
        
        double currentValue = holding.getQuantity() * holding.getAveragePrice();
        double newValue = currentValue + totalCost;
        int newQuantity = holding.getQuantity() + quantity;

        holding.setQuantity(newQuantity);
        holding.setAveragePrice(newValue / newQuantity);
    }

    /**
     * Create a new holding for this symbol
     */
    private AccountHolding createNewHolding(TradingAccount account, String symbol, Integer quantity, Double price, String agentName) {
        logger.info("🆕 Creating NEW holding for {} - {}: qty={}, avgPrice=${}",
            agentName, symbol, quantity, price);
        
        AccountHolding holding = new AccountHolding();
        holding.setAccount(account);
        holding.setSymbol(symbol);
        holding.setQuantity(quantity);
        holding.setAveragePrice(price);
        
        return holding;
    }

    /**
     * Fetch market price for a symbol with debug logging
     */
    private Double fetchMarketPrice(String symbol) {
        logger.info("🔍 DEBUGGING: Requesting real market price for {} from MarketService", symbol);
        MarketService.PriceData priceData = marketService.getSharePrice(symbol);
        Double price = priceData.getPrice();
        logger.info("💰 DEBUGGING: Received price for {}: ${} from {} ({})",
            symbol, price, priceData.getDataSource(), priceData.getDataTier());
        return price;
    }

    /**
     * Get trading account for an agent - expects account to already exist
     */
    private TradingAccount getAccount(String agentName) {
        return tradingAccountRepository.findByAgentName(agentName)
            .orElseThrow(() -> new RuntimeException("Trading account not found for agent: " + agentName +
                ". Agent must be initialized before trading operations."));
    }
}

