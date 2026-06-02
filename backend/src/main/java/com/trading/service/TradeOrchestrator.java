package com.trading.service;

import com.trading.dto.response.TradeResult;
import com.trading.exception.BusinessRuleException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Owns the transactional trade-execution flow. Each public method runs inside
 * a {@code @Transactional} boundary so all row writes — trade insert, balance
 * update, portfolio snapshot — either commit together or roll back together.
 *
 * <p>The flow is identical for both buy and sell: fetch the current price,
 * delegate the row writes to the matching executor, then persist a portfolio
 * snapshot. A {@link BusinessRuleException} thrown by the executor short
 * circuits the happy path and propagates out so callers can map it to an HTTP
 * response; the surrounding transaction rolls back automatically.</p>
 */
@Component
public class TradeOrchestrator {

    private static final Logger logger = LoggerFactory.getLogger(TradeOrchestrator.class);

    private final BuyTradeExecutor buyTradeExecutor;
    private final SellTradeExecutor sellTradeExecutor;
    private final MarketService marketService;
    private final PortfolioSnapshotService portfolioSnapshotService;

    public TradeOrchestrator(
            BuyTradeExecutor buyTradeExecutor,
            SellTradeExecutor sellTradeExecutor,
            MarketService marketService,
            PortfolioSnapshotService portfolioSnapshotService) {
        this.buyTradeExecutor = buyTradeExecutor;
        this.sellTradeExecutor = sellTradeExecutor;
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
        Double price = marketService.getSharePrice(symbol).getPrice();
        TradeResult result = buyTradeExecutor.executeBuy(agentName, symbol, quantity, price, runId);
        portfolioSnapshotService.createSnapshot(agentName);
        logger.debug("Executed buy for run {}: {} {} @ {}", runId, "buy", result.symbol(), result.price());
        return result;
    }

    /**
     * Sell shares for an agent within a transactional boundary.
     *
     * @param runId REQUIRED - Every transaction must be linked to an agent run
     * @return TradeResult with transaction details and updated balance
     */
    @Transactional
    public TradeResult sellShares(String agentName, String symbol, Integer quantity, Long runId) {
        Double price = marketService.getSharePrice(symbol).getPrice();
        TradeResult result = sellTradeExecutor.executeSell(agentName, symbol, quantity, price, runId);
        portfolioSnapshotService.createSnapshot(agentName);
        logger.debug("Executed sell for run {}: {} {} @ {}", runId, "sell", result.symbol(), result.price());
        return result;
    }
}
