package com.trading.enums;

import com.fasterxml.jackson.annotation.JsonValue;

/**
 * Types of WebSocket messages broadcast by the trading system.
 * Used for type-safe message construction and consistent JSON serialization.
 */
public enum WebSocketMessageType {

    PHASE_UPDATE("phase_update"),
    DECISION_COMPLETED("decision_completed"),
    TRADE_EXECUTED("trade_executed"),
    TRADE_REJECTED("trade_rejected");

    private final String value;

    WebSocketMessageType(String value) {
        this.value = value;
    }

    /**
     * Returns the snake_case string value for JSON serialization.
     * Jackson uses this via @JsonValue to serialize enum as string.
     */
    @JsonValue
    public String getValue() {
        return value;
    }
}
