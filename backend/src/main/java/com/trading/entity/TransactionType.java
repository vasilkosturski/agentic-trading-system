package com.trading.entity;

/**
 * Type of transaction in the trading system.
 * CRITICAL: This must be set explicitly - never derived from quantity sign!
 */
public enum TransactionType {
    BUY,
    SELL
}
