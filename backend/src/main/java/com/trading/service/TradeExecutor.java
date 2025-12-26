package com.trading.service;

import com.trading.entity.*;
import com.trading.exception.ResourceNotFoundException;
import com.trading.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;

/**
 * Base class for trade executors (buy/sell).
 * Contains shared infrastructure: account lookup, price fetching, transaction creation.
 * Uses constructor injection for better testability and immutability.
 */
@Transactional
public abstract class TradeExecutor {

    private static final Logger logger = LoggerFactory.getLogger(TradeExecutor.class);

    protected final TradingAccountRepository tradingAccountRepository;
    protected final AccountTransactionRepository transactionRepository;
    protected final AccountHoldingRepository holdingRepository;
    protected final MarketService marketService;
    protected final AgentRunRepository agentRunRepository;

    /**
     * Constructor injection for all dependencies.
     * Ensures immutability and makes dependencies explicit.
     */
    protected TradeExecutor(
            TradingAccountRepository tradingAccountRepository,
            AccountTransactionRepository transactionRepository,
            AccountHoldingRepository holdingRepository,
            MarketService marketService,
            AgentRunRepository agentRunRepository) {
        this.tradingAccountRepository = tradingAccountRepository;
        this.transactionRepository = transactionRepository;
        this.holdingRepository = holdingRepository;
        this.marketService = marketService;
        this.agentRunRepository = agentRunRepository;
    }

    /**
     * Get trading account for an agent - expects account to already exist
     */
    protected TradingAccount getAccount(String agentName) {
        return tradingAccountRepository.findByAgentName(agentName)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Trading account not found for agent: " + agentName +
                ". Agent must be initialized before trading operations."));
    }

    /**
     * Fetch market price for a symbol with debug logging
     */
    protected Double fetchMarketPrice(String symbol) {
        logger.info("🔍 DEBUGGING: Requesting real market price for {} from MarketService", symbol);
        MarketService.PriceData priceData = marketService.getSharePrice(symbol);
        Double price = priceData.getPrice();
        logger.info("💰 DEBUGGING: Received price for {}: ${} from {} ({})",
            symbol, price, priceData.getDataSource(), priceData.getDataTier());
        return price;
    }

    /**
     * Create and save a transaction record
     * @param transactionType BUY or SELL - explicit enum value
     * @return The saved transaction (with generated ID)
     */
    protected AccountTransaction createTransaction(TradingAccount account, String symbol, Integer quantity,
                                     Double price, Long runId, TransactionType transactionType) {
        AccountTransaction transaction = new AccountTransaction();
        transaction.setAccount(account);
        transaction.setSymbol(symbol);
        transaction.setTransactionType(transactionType);
        transaction.setQuantity(quantity);
        transaction.setPrice(price);
        transaction.setTimestamp(Instant.now());

        // Link transaction to agent run (REQUIRED)
        AgentRun agentRun = agentRunRepository.findById(runId)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Agent run with id " + runId + " not found"));
        transaction.setAgentRun(agentRun);

        return transactionRepository.save(transaction);
    }
}
