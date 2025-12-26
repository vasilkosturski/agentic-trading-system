package com.trading.service;

import com.trading.dto.response.TradeResult;
import com.trading.entity.*;
import com.trading.exception.BusinessRuleException;
import com.trading.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Executes sell trade operations.
 * Extracted from AccountService for better testability and single responsibility.
 */
@Service
@Transactional
public class SellTradeExecutor extends TradeExecutor {

    private static final Logger logger = LoggerFactory.getLogger(SellTradeExecutor.class);

    /**
     * Constructor injection - passes dependencies to base class.
     * Spring auto-wires this constructor (no @Autowired needed since Spring 4.3+).
     */
    public SellTradeExecutor(
            TradingAccountRepository tradingAccountRepository,
            AccountTransactionRepository transactionRepository,
            AccountHoldingRepository holdingRepository,
            MarketService marketService,
            AgentRunRepository agentRunRepository) {
        super(tradingAccountRepository, transactionRepository, holdingRepository, marketService, agentRunRepository);
    }

    /**
     * Execute a sell trade for an agent
     * @param agentName Name of the agent
     * @param symbol Stock symbol to sell
     * @param quantity Number of shares to sell
     * @param runId REQUIRED - Every transaction must be linked to an agent run
     * @return TradeResult with symbol, quantity, price, and updated balance
     */
    public TradeResult executeSell(String agentName, String symbol, Integer quantity, Long runId) {
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
        TradingAccount savedAccount = tradingAccountRepository.save(account);

        // Create and save transaction
        createTransaction(account, symbol, quantity, price, runId, TransactionType.SELL);

        // Update holding (reduce quantity or delete if 0)
        updateHolding(holding, quantity, agentName, symbol);

        // Return essential trade details for LLM
        return new TradeResult(symbol, quantity, price, savedAccount.getBalance());
    }

    /**
     * Validate that account has sufficient shares to sell
     * @return The holding if valid
     */
    private AccountHolding validateSufficientShares(TradingAccount account, String symbol, Integer quantity) {
        AccountHolding holding = holdingRepository.findByAccountAndSymbol(account, symbol);
        if (holding == null || holding.getQuantity() < quantity) {
            int available = holding != null ? holding.getQuantity() : 0;
            throw new BusinessRuleException(
                "Cannot sell " + quantity + " shares of " + symbol +
                ". Only have " + available + " shares available");
        }
        return holding;
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
}
