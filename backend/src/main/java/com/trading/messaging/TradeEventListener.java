package com.trading.messaging;

import com.trading.messaging.event.TradeExecutedEvent;
import com.trading.messaging.event.TradeRejectedEvent;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

/**
 * Bridges domain trade events to the WebSocket broadcast pipeline.
 *
 * <p>Uses {@code AFTER_COMMIT} so broadcasts only fire once the surrounding
 * transaction (if any) successfully commits. {@code fallbackExecution = true}
 * ensures the listener still runs when no transaction is active, preserving
 * broadcast behavior for callers that publish outside a transactional context.</p>
 */
@Component
public class TradeEventListener {

    private final TradeEventPublisher tradeEventPublisher;

    public TradeEventListener(TradeEventPublisher tradeEventPublisher) {
        this.tradeEventPublisher = tradeEventPublisher;
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT, fallbackExecution = true)
    public void onTradeExecuted(TradeExecutedEvent event) {
        tradeEventPublisher.publishTradeExecuted(event.message());
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT, fallbackExecution = true)
    public void onTradeRejected(TradeRejectedEvent event) {
        tradeEventPublisher.publishTradeRejected(event.message());
    }
}
