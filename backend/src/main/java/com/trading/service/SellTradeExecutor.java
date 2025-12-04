package com.trading.service;

import com.trading.entity.*;
import com.trading.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;

/**
 * Executes sell trade operations.
 * Extracted from AccountService for better testability and single responsibility.
 */
@Service
@Transactional
public class SellTradeExecutor {

    private static final Logger logger = LoggerFactory.getLogger(SellTradeExecutor.class);

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
     * Execute a sell trade for an agent
     * @param agentName Name of the agent
     * @param symbol Stock symbol to sell
     * @param quantity Number of shares to sell
     * @param runId REQUIRED - Every transaction must be linked to an agent run
     * @return Success message
     */
    public String executeSell(String agentName, String symbol, Integer quantity, Long runId) {
        if (runId == null) {
            throw new IllegalArgumentException("runId is required - every transaction must be linked to an agent run");
        }

        TradingAccount account = getAccount(agentName);

        // Check if we have enough shares
        AccountHolding holding = validateSufficientShares(account, symbol, quantity);

        // Get current market price from MarketService
        Double price = fetchMarketPrice(symbol);
        Double totalProceeds = price * quantity;

        // Update account balance
        account.setBalance(account.getBalance() + totalProceeds);
        tradingAccountRepository.save(account);

        // Create and save transaction
        createTransaction(account, symbol, quantity, price, runId);

        // Update holding (reduce quantity or delete if 0)
        updateHolding(holding, quantity, agentName, symbol);

        return "Successfully sold " + quantity + " shares of " + symbol + " at $" + String.format("%.2f", price) + " each";
    }

    /**
     * Validate that account has sufficient shares to sell
     * @return The holding if valid
     */
    private AccountHolding validateSufficientShares(TradingAccount account, String symbol, Integer quantity) {
        AccountHolding holding = holdingRepository.findByAccountAndSymbol(account, symbol);
        if (holding == null || holding.getQuantity() < quantity) {
            int available = holding != null ? holding.getQuantity() : 0;
            throw new RuntimeException("Cannot sell " + quantity + " shares of " + symbol +
                ". Only have " + available + " shares available");
        }
        return holding;
    }

    /**
     * Create and save the transaction record
     */
    private void createTransaction(TradingAccount account, String symbol, Integer quantity, Double price, Long runId) {
        AccountTransaction transaction = new AccountTransaction();
        transaction.setAccount(account);
        transaction.setSymbol(symbol);
        transaction.setTransactionType(TransactionType.SELL);  // EXPLICIT enum - never derived!
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
     * Update holding after sell (reduce quantity or delete if 0)
     */
    private void updateHolding(AccountHolding holding, Integer quantity, String agentName, String symbol) {
        int newQuantity = holding.getQuantity() - quantity;

        if (newQuantity == 0) {
            logger.info("🗑️ Removing holding for {} - {}: sold all shares", agentName, symbol);
            holdingRepository.delete(holding);
        } else {
            logger.info("📊 Updating holding for {} - {}: current qty={}, selling qty={}, remaining={}",
                agentName, symbol, holding.getQuantity(), quantity, newQuantity);
            holding.setQuantity(newQuantity);
            holdingRepository.save(holding);
        }
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
