package com.trading.enums;

public enum TradeDecision {
    BUY,
    SELL,
    HOLD;

    public boolean requiresExecution() {
        return this == BUY || this == SELL;
    }

    public boolean isHold() {
        return this == HOLD;
    }
}
