package com.trading.service;

import com.trading.dto.response.TradeResult;
import com.trading.entity.*;
import com.trading.enums.TradeRejectionType;
import com.trading.exception.BusinessRuleException;
import com.trading.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Executes buy trade operations.
 * Extracted from AccountService for better testability and single responsibility.
 */
@Service
public class BuyTradeExecutor extends TradeExecutor {

    private static final Logger logger = LoggerFactory.getLogger(BuyTradeExecutor.class);
    private static final int MAX_POSITIONS_PER_AGENT = 10;

    /**
     * Constructor injection - passes dependencies to base class.
     * Spring auto-wires this constructor (no @Autowired needed since Spring 4.3+).
     */
    public BuyTradeExecutor(
            TradingAccountRepository tradingAccountRepository,
            AccountTransactionRepository transactionRepository,
            AccountHoldingRepository holdingRepository,
            MarketService marketService) {
        super(tradingAccountRepository, transactionRepository, holdingRepository, marketService);
    }

    /**
     * Execute a buy trade for an agent.
     *
     * @param agentName Name of the agent
     * @param symbol Stock symbol to buy
     * @param quantity Number of shares to buy
     * @param price Pre-fetched market price
     * @param runId REQUIRED - Every transaction must be linked to an agent run
     * @return TradeResult with symbol, quantity, price, and updated balance
     */
    @Transactional
    public TradeResult executeBuy(String agentName, String symbol, Integer quantity, Double price, Long runId) {
        if (runId == null) {
            throw new IllegalArgumentException("runId is required - every transaction must be linked to an agent run");
        }
        if (price == null || price <= 0) {
            throw new IllegalArgumentException("price must be positive - fetch from MarketService before calling this method");
        }

        TradingAccount account = getAccount(agentName);
        validatePositionLimit(account, symbol);

        Double totalCost = price * quantity;
        validateSufficientFunds(account, symbol, quantity, totalCost);

        account.setBalance(account.getBalance() - totalCost);
        TradingAccount savedAccount = tradingAccountRepository.save(account);

        AccountTransaction transaction = createTransaction(account, symbol, quantity, price, runId, TransactionType.BUY);
        updateHolding(account, symbol, quantity, price, totalCost, agentName);

        return new TradeResult(transaction.getId(), symbol, quantity, price, savedAccount.getBalance());
    }

    private void validatePositionLimit(TradingAccount account, String symbol) {
        List<AccountHolding> currentHoldings = holdingRepository.findActiveHoldingsByAccount(account);
        long activePositions = currentHoldings.size();

        boolean isNewPosition = currentHoldings.stream()
            .noneMatch(h -> h.getSymbol().equals(symbol));

        if (isNewPosition && activePositions >= MAX_POSITIONS_PER_AGENT) {
            String holdingsList = currentHoldings.stream()
                .map(h -> h.getSymbol())
                .collect(Collectors.joining(", "));

            throw new BusinessRuleException(
                TradeRejectionType.POSITION_LIMIT_REACHED,
                "❌ POSITION LIMIT REACHED: You currently hold " + MAX_POSITIONS_PER_AGENT + " positions (" + holdingsList + "). " +
                "Maximum allowed is " + MAX_POSITIONS_PER_AGENT + " positions per agent. " +
                "To buy " + symbol + ", you must first sell one of your existing positions. " +
                "Review your holdings and sell your weakest/lowest-conviction position, then retry this purchase."
            );
        }
    }

    private void validateSufficientFunds(TradingAccount account, String symbol, Integer quantity, Double totalCost) {
        if (totalCost > account.getBalance()) {
            throw new BusinessRuleException(
                TradeRejectionType.INSUFFICIENT_FUNDS,
                "Insufficient funds to buy " + quantity + " shares of " + symbol +
                ". Required: $" + String.format("%.2f", totalCost) + ", Available: $" + String.format("%.2f", account.getBalance()));
        }
    }

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

    private void updateExistingHolding(AccountHolding holding, Integer quantity, Double totalCost, String agentName, String symbol) {
        logger.info("📊 Updating existing holding for {} - {}: current qty={}, adding qty={}",
            agentName, symbol, holding.getQuantity(), quantity);
        
        double currentValue = holding.getQuantity() * holding.getAveragePrice();
        double newValue = currentValue + totalCost;
        int newQuantity = holding.getQuantity() + quantity;

        holding.setQuantity(newQuantity);
        holding.setAveragePrice(newValue / newQuantity);
    }

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
}

