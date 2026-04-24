package com.trading.service;

import com.trading.entity.*;
import com.trading.exception.ResourceNotFoundException;
import com.trading.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;

/**
 * Base class for trade executors (buy/sell).
 */
public abstract class TradeExecutor {

    private static final Logger logger = LoggerFactory.getLogger(TradeExecutor.class);

    protected final TradingAccountRepository tradingAccountRepository;
    protected final AccountTransactionRepository transactionRepository;
    protected final AccountHoldingRepository holdingRepository;
    protected final MarketService marketService;

    protected TradeExecutor(
            TradingAccountRepository tradingAccountRepository,
            AccountTransactionRepository transactionRepository,
            AccountHoldingRepository holdingRepository,
            MarketService marketService) {
        this.tradingAccountRepository = tradingAccountRepository;
        this.transactionRepository = transactionRepository;
        this.holdingRepository = holdingRepository;
        this.marketService = marketService;
    }

    protected TradingAccount getAccount(String agentName) {
        return tradingAccountRepository.findByAgentName(agentName)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Trading account not found for agent: " + agentName +
                ". Agent must be initialized before trading operations."));
    }

    protected Double fetchMarketPrice(String symbol) {
        logger.info("🔍 DEBUGGING: Requesting real market price for {} from MarketService", symbol);
        MarketService.PriceData priceData = marketService.getSharePrice(symbol);
        Double price = priceData.getPrice();
        logger.info("💰 DEBUGGING: Received price for {}: ${} from {} (cached: {})",
            symbol, price, priceData.getSource(), priceData.isCached());
        return price;
    }

    protected AccountTransaction createTransaction(TradingAccount account, String symbol, Integer quantity,
                                     Double price, Long runId, TransactionType transactionType) {
        AccountTransaction transaction = new AccountTransaction();
        transaction.setAccount(account);
        transaction.setSymbol(symbol);
        transaction.setTransactionType(transactionType);
        transaction.setQuantity(quantity);
        transaction.setPrice(price);
        transaction.setTimestamp(Instant.now());

        return transactionRepository.save(transaction);
    }
}
