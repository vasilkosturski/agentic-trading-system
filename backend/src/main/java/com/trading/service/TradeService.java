package com.trading.service;

import com.trading.dto.response.TradeResult;
import com.trading.entity.AccountHolding;
import com.trading.entity.AccountTransaction;
import com.trading.entity.TradingAccount;
import com.trading.entity.TransactionType;
import com.trading.enums.TradeRejectionType;
import com.trading.exception.BusinessRuleException;
import com.trading.exception.ResourceNotFoundException;
import com.trading.repository.AccountHoldingRepository;
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.TradingAccountRepository;
import java.time.Instant;
import java.util.List;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Owns the transactional trade-execution flow for both buy and sell operations.
 * Each public method runs inside a {@code @Transactional} boundary so all row
 * writes — trade insert, balance update, holding upsert/delete, portfolio
 * snapshot — either commit together or roll back together.
 *
 * <p>The price is fetched from {@link MarketService} internally — callers
 * supply only the agent, symbol, quantity, and run identifier. A
 * {@link BusinessRuleException} thrown by a validation step short-circuits the
 * happy path and propagates out so callers can map it to an HTTP response; the
 * surrounding transaction rolls back automatically.</p>
 */
@Service
public class TradeService {

    private static final Logger logger = LoggerFactory.getLogger(TradeService.class);
    private static final int MAX_POSITIONS_PER_AGENT = 10;

    private final TradingAccountRepository tradingAccountRepository;
    private final AccountTransactionRepository transactionRepository;
    private final AccountHoldingRepository holdingRepository;
    private final MarketService marketService;
    private final PortfolioSnapshotService portfolioSnapshotService;

    public TradeService(
            TradingAccountRepository tradingAccountRepository,
            AccountTransactionRepository transactionRepository,
            AccountHoldingRepository holdingRepository,
            MarketService marketService,
            PortfolioSnapshotService portfolioSnapshotService) {
        this.tradingAccountRepository = tradingAccountRepository;
        this.transactionRepository = transactionRepository;
        this.holdingRepository = holdingRepository;
        this.marketService = marketService;
        this.portfolioSnapshotService = portfolioSnapshotService;
    }

    /**
     * Buy shares for an agent within a transactional boundary.
     *
     * @param runId REQUIRED - Every transaction must be linked to an agent run
     * @return TradeResult with transaction details and updated balance
     */
    @Transactional
    public TradeResult buyShares(String agentName, String symbol, Integer quantity, Long runId) {
        if (runId == null) {
            throw new IllegalArgumentException("runId is required - every transaction must be linked to an agent run");
        }

        TradingAccount account = getAccount(agentName);
        validatePositionLimit(account, symbol);

        Double price = marketService.getSharePrice(symbol).getPrice();
        if (price == null || price <= 0) {
            throw new IllegalArgumentException(
                    "price must be positive - fetch from MarketService before calling this method");
        }

        Double totalCost = price * quantity;
        validateSufficientFunds(account, symbol, quantity, totalCost);

        account.setBalance(account.getBalance() - totalCost);
        TradingAccount savedAccount = tradingAccountRepository.save(account);

        AccountTransaction transaction =
                createTransaction(account, symbol, quantity, price, runId, TransactionType.BUY);
        updateHoldingForBuy(account, symbol, quantity, price, totalCost, agentName);

        portfolioSnapshotService.createSnapshot(agentName);
        logger.debug("Executed buy for run {}: {} {} @ {}", runId, "buy", symbol, price);

        return new TradeResult(transaction.getId(), symbol, quantity, price, savedAccount.getBalance());
    }

    /**
     * Sell shares for an agent within a transactional boundary.
     *
     * @param runId REQUIRED - Every transaction must be linked to an agent run
     * @return TradeResult with transaction details and updated balance
     */
    @Transactional
    public TradeResult sellShares(String agentName, String symbol, Integer quantity, Long runId) {
        if (runId == null) {
            throw new IllegalArgumentException("runId is required - every transaction must be linked to an agent run");
        }

        TradingAccount account = getAccount(agentName);
        AccountHolding holding = validateSufficientShares(account, symbol, quantity);

        Double price = marketService.getSharePrice(symbol).getPrice();
        if (price == null || price <= 0) {
            throw new IllegalArgumentException(
                    "price must be positive - fetch from MarketService before calling this method");
        }

        Double totalProceeds = price * quantity;

        account.setBalance(account.getBalance() + totalProceeds);
        TradingAccount savedAccount = tradingAccountRepository.save(account);

        AccountTransaction transaction =
                createTransaction(account, symbol, quantity, price, runId, TransactionType.SELL);
        updateHoldingForSell(holding, quantity, agentName, symbol);

        portfolioSnapshotService.createSnapshot(agentName);
        logger.debug("Executed sell for run {}: {} {} @ {}", runId, "sell", symbol, price);

        return new TradeResult(transaction.getId(), symbol, quantity, price, savedAccount.getBalance());
    }

    // ==================== Shared helpers ====================

    private TradingAccount getAccount(String agentName) {
        return tradingAccountRepository
                .findByAgentName(agentName)
                .orElseThrow(() -> new ResourceNotFoundException("Trading account not found for agent: " + agentName
                        + ". Agent must be initialized before trading operations."));
    }

    private AccountTransaction createTransaction(
            TradingAccount account,
            String symbol,
            Integer quantity,
            Double price,
            Long runId,
            TransactionType transactionType) {
        AccountTransaction transaction = new AccountTransaction();
        transaction.setAccount(account);
        transaction.setSymbol(symbol);
        transaction.setTransactionType(transactionType);
        transaction.setQuantity(quantity);
        transaction.setPrice(price);
        transaction.setTimestamp(Instant.now());

        return transactionRepository.save(transaction);
    }

    // ==================== Buy path ====================

    private void validatePositionLimit(TradingAccount account, String symbol) {
        List<AccountHolding> currentHoldings = holdingRepository.findActiveHoldingsByAccount(account);
        long activePositions = currentHoldings.size();

        boolean isNewPosition =
                currentHoldings.stream().noneMatch(h -> h.getSymbol().equals(symbol));

        if (isNewPosition && activePositions >= MAX_POSITIONS_PER_AGENT) {
            String holdingsList =
                    currentHoldings.stream().map(h -> h.getSymbol()).collect(Collectors.joining(", "));

            throw new BusinessRuleException(
                    TradeRejectionType.POSITION_LIMIT_REACHED,
                    "❌ POSITION LIMIT REACHED: You currently hold " + MAX_POSITIONS_PER_AGENT + " positions ("
                            + holdingsList + "). " + "Maximum allowed is "
                            + MAX_POSITIONS_PER_AGENT + " positions per agent. " + "To buy "
                            + symbol + ", you must first sell one of your existing positions. "
                            + "Review your holdings and sell your weakest/lowest-conviction position, then retry this purchase.");
        }
    }

    private void validateSufficientFunds(TradingAccount account, String symbol, Integer quantity, Double totalCost) {
        if (totalCost > account.getBalance()) {
            throw new BusinessRuleException(
                    TradeRejectionType.INSUFFICIENT_FUNDS,
                    "Insufficient funds to buy " + quantity + " shares of " + symbol + ". Required: $"
                            + String.format("%.2f", totalCost) + ", Available: $"
                            + String.format("%.2f", account.getBalance()));
        }
    }

    private void updateHoldingForBuy(
            TradingAccount account, String symbol, Integer quantity, Double price, Double totalCost, String agentName) {
        AccountHolding holding = holdingRepository.findByAccountAndSymbol(account, symbol);

        if (holding != null) {
            updateExistingHolding(holding, quantity, totalCost, agentName, symbol);
        } else {
            holding = createNewHolding(account, symbol, quantity, price, agentName);
        }

        AccountHolding savedHolding = holdingRepository.save(holding);
        logger.info(
                "✅ Successfully saved holding for {} - {}: id={}, qty={}",
                agentName,
                symbol,
                savedHolding.getId(),
                savedHolding.getQuantity());
    }

    private void updateExistingHolding(
            AccountHolding holding, Integer quantity, Double totalCost, String agentName, String symbol) {
        logger.info(
                "📊 Updating existing holding for {} - {}: current qty={}, adding qty={}",
                agentName,
                symbol,
                holding.getQuantity(),
                quantity);

        double currentValue = holding.getQuantity() * holding.getAveragePrice();
        double newValue = currentValue + totalCost;
        int newQuantity = holding.getQuantity() + quantity;

        holding.setQuantity(newQuantity);
        holding.setAveragePrice(newValue / newQuantity);
    }

    private AccountHolding createNewHolding(
            TradingAccount account, String symbol, Integer quantity, Double price, String agentName) {
        logger.info("🆕 Creating NEW holding for {} - {}: qty={}, avgPrice=${}", agentName, symbol, quantity, price);

        AccountHolding holding = new AccountHolding();
        holding.setAccount(account);
        holding.setSymbol(symbol);
        holding.setQuantity(quantity);
        holding.setAveragePrice(price);

        return holding;
    }

    // ==================== Sell path ====================

    private AccountHolding validateSufficientShares(TradingAccount account, String symbol, Integer quantity) {
        AccountHolding holding = holdingRepository.findByAccountAndSymbol(account, symbol);
        if (holding == null || holding.getQuantity() < quantity) {
            int available = holding != null ? holding.getQuantity() : 0;
            throw new BusinessRuleException(
                    TradeRejectionType.INSUFFICIENT_SHARES,
                    "Cannot sell " + quantity + " shares of " + symbol + ". Only have " + available
                            + " shares available");
        }
        return holding;
    }

    private void updateHoldingForSell(AccountHolding holding, Integer quantity, String agentName, String symbol) {
        int newQuantity = holding.getQuantity() - quantity;

        if (newQuantity == 0) {
            logger.info("🗑️ Removing holding for {} - {}: sold all shares", agentName, symbol);
            holdingRepository.delete(holding);
        } else {
            logger.info(
                    "📊 Updating holding for {} - {}: current qty={}, selling qty={}, remaining={}",
                    agentName,
                    symbol,
                    holding.getQuantity(),
                    quantity,
                    newQuantity);
            holding.setQuantity(newQuantity);
            holdingRepository.save(holding);
        }
    }
}
