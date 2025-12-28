package com.trading.dto.request;

/**
 * Enum for trade types in unified trade endpoint.
 * Used to distinguish between buy and sell operations.
 */
public enum TradeType {
    /**
     * Buy shares
     */
    BUY,

    /**
     * Sell shares
     */
    SELL
}
