package com.trading.exception;

import com.trading.enums.TradeRejectionType;

/**
 * Exception thrown when a business rule is violated.
 * Examples: insufficient funds, position limits, invalid operations.
 * Maps to HTTP 409 Conflict.
 */
public class BusinessRuleException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    private final TradeRejectionType rejectionType;

    public BusinessRuleException(String message) {
        super(message);
        this.rejectionType = TradeRejectionType.VALIDATION_ERROR;
    }

    public BusinessRuleException(TradeRejectionType rejectionType, String message) {
        super(message);
        this.rejectionType = rejectionType;
    }

    public BusinessRuleException(String message, Throwable cause) {
        super(message, cause);
        this.rejectionType = TradeRejectionType.VALIDATION_ERROR;
    }

    public TradeRejectionType getRejectionType() {
        return rejectionType;
    }
}
