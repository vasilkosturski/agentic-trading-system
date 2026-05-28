package com.trading.messaging.event;

import com.trading.dto.websocket.TradeExecutedMessage;

/**
 * Domain event signaling that a trade was successfully executed.
 *
 * <p>Published by the service layer when a trade succeeds; consumed by
 * {@link com.trading.messaging.TradeEventListener} which forwards the
 * payload to the WebSocket broadcast pipeline after the surrounding
 * transaction commits.</p>
 */
public record TradeExecutedEvent(TradeExecutedMessage message) {
}
