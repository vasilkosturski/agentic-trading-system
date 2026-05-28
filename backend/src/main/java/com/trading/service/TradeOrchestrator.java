package com.trading.service;

import com.trading.dto.response.TradeResult;
import com.trading.dto.websocket.TradeExecutedMessage;
import com.trading.dto.websocket.TradeRejectedMessage;
import com.trading.exception.BusinessRuleException;
import com.trading.messaging.event.TradeExecutedEvent;
import com.trading.messaging.event.TradeRejectedEvent;
import com.trading.repository.TradingRunRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Owns the transactional trade-execution flow. Each public method runs inside
 * a {@code @Transactional} boundary; broadcast events fire AFTER_COMMIT via
 * {@link com.trading.messaging.TradeEventListener}, so rolled-back trades never
 * surface in the client.
 *
 * <p>The flow is identical for both buy and sell: resolve the agent id from the
 * run, fetch the current price, delegate the row writes to the matching
 * executor, persist a portfolio snapshot, then publish a domain event the
 * listener forwards to the WebSocket broadcast pipeline once the transaction
 * commits. Any {@link BusinessRuleException} thrown by the executor short
 * circuits the happy path and publishes a rejection event instead — still
 * inside the transaction, so the rejection broadcast also obeys
 * commit-semantics.</p>
 */
@Component
public class TradeOrchestrator {

    private static final Logger logger = LoggerFactory.getLogger(TradeOrchestrator.class);

    private final BuyTradeExecutor buyTradeExecutor;
    private final SellTradeExecutor sellTradeExecutor;
    private final MarketService marketService;
    private final TradingRunRepository tradingRunRepository;
    private final PortfolioSnapshotService portfolioSnapshotService;
    private final ApplicationEventPublisher applicationEventPublisher;

    public TradeOrchestrator(
            BuyTradeExecutor buyTradeExecutor,
            SellTradeExecutor sellTradeExecutor,
            MarketService marketService,
            TradingRunRepository tradingRunRepository,
            PortfolioSnapshotService portfolioSnapshotService,
            ApplicationEventPublisher applicationEventPublisher) {
        this.buyTradeExecutor = buyTradeExecutor;
        this.sellTradeExecutor = sellTradeExecutor;
        this.marketService = marketService;
        this.tradingRunRepository = tradingRunRepository;
        this.portfolioSnapshotService = portfolioSnapshotService;
        this.applicationEventPublisher = applicationEventPublisher;
    }

    /**
     * Buy shares for an agent within a transactional boundary.
     *
     * @param runId REQUIRED - Every transaction must be linked to an agent run
     * @return TradeResult with transaction details and updated balance
     */
    @Transactional
    public TradeResult buyShares(String agentName, String symbol, Integer quantity, Long runId) {
        Long agentId = getAgentIdFromRun(runId);
        try {
            Double price = marketService.getSharePrice(symbol).getPrice();
            TradeResult result = buyTradeExecutor.executeBuy(agentName, symbol, quantity, price, runId);
            portfolioSnapshotService.createSnapshot(agentName);

            publishTradeExecuted(agentId, runId, "buy", result);
            return result;
        } catch (BusinessRuleException e) {
            publishTradeRejected(agentId, runId, e);
            throw e;
        }
    }

    /**
     * Sell shares for an agent within a transactional boundary.
     *
     * @param runId REQUIRED - Every transaction must be linked to an agent run
     * @return TradeResult with transaction details and updated balance
     */
    @Transactional
    public TradeResult sellShares(String agentName, String symbol, Integer quantity, Long runId) {
        Long agentId = getAgentIdFromRun(runId);
        try {
            Double price = marketService.getSharePrice(symbol).getPrice();
            TradeResult result = sellTradeExecutor.executeSell(agentName, symbol, quantity, price, runId);
            portfolioSnapshotService.createSnapshot(agentName);

            publishTradeExecuted(agentId, runId, "sell", result);
            return result;
        } catch (BusinessRuleException e) {
            publishTradeRejected(agentId, runId, e);
            throw e;
        }
    }

    /**
     * Resolve the agent id for a given run id. Returns {@code null} if the run
     * cannot be found so the rejection broadcast can still be published with a
     * best-effort payload.
     */
    private Long getAgentIdFromRun(Long runId) {
        return tradingRunRepository.findById(runId)
            .map(run -> run.getAgent().getId())
            .orElse(null);
    }

    /**
     * Publish a trade-executed domain event. The listener forwards the payload to
     * the WebSocket broadcast pipeline after the surrounding transaction commits.
     */
    private void publishTradeExecuted(Long agentId, Long runId, String side, TradeResult result) {
        TradeExecutedMessage.TradeDetails tradeDetails = new TradeExecutedMessage.TradeDetails(
            side,
            result.symbol(),
            result.quantity(),
            result.price()
        );

        TradeExecutedMessage message = new TradeExecutedMessage(agentId, runId, tradeDetails);
        applicationEventPublisher.publishEvent(new TradeExecutedEvent(message));
        logger.debug("Published TradeExecutedEvent for run {}: {} {} @ {}",
            runId, side, result.symbol(), result.price());
    }

    /**
     * Publish a trade-rejected domain event. The listener forwards the payload to
     * the WebSocket broadcast pipeline after the surrounding transaction commits.
     */
    private void publishTradeRejected(Long agentId, Long runId, BusinessRuleException e) {
        TradeRejectedMessage message = new TradeRejectedMessage(
            agentId,
            runId,
            e.getRejectionType(),
            e.getMessage()
        );

        applicationEventPublisher.publishEvent(new TradeRejectedEvent(message));
        logger.debug("Published TradeRejectedEvent for run {}: {} - {}",
            runId, e.getRejectionType(), e.getMessage());
    }
}
