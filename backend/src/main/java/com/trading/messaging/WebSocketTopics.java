package com.trading.messaging;

/**
 * STOMP topic constants shared across services that broadcast over WebSocket.
 */
public final class WebSocketTopics {

    private WebSocketTopics() {
        // utility class — no instances
    }

    public static final String TOPIC_TRADES = "/topic/runs/trades";
    public static final String TOPIC_PHASES = "/topic/runs/phases";
    public static final String TOPIC_DECISIONS = "/topic/runs/decisions";
}
