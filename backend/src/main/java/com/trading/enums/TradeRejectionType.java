package com.trading.enums;

import com.fasterxml.jackson.annotation.JsonValue;

/**
 * Enum representing the type of trade rejection.
 * Used for explicit error classification instead of string parsing.
 */
public enum TradeRejectionType {
    INSUFFICIENT_FUNDS("INSUFFICIENT_FUNDS"),
    INSUFFICIENT_SHARES("INSUFFICIENT_SHARES"),
    POSITION_LIMIT_REACHED("POSITION_LIMIT_REACHED"),
    VALIDATION_ERROR("VALIDATION_ERROR");

    private final String value;

    TradeRejectionType(String value) {
        this.value = value;
    }

    @JsonValue
    public String getValue() {
        return value;
    }
}
