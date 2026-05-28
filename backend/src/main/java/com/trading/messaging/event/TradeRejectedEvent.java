package com.trading.messaging.event;

import com.trading.dto.websocket.TradeRejectedMessage;

/**
 * Domain event signaling that a trade was rejected by a business rule.
 *
 * <p>Published by the service layer when a trade fails validation;
 * consumed by {@link com.trading.messaging.TradeEventListener} which
 * forwards the payload to the WebSocket broadcast pipeline after the
 * surrounding transaction commits.</p>
 */
public record TradeRejectedEvent(TradeRejectedMessage message) {
}
