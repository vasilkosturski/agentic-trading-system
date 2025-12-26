package com.trading.exception;

/**
 * Exception thrown when a business rule is violated.
 * Examples: insufficient funds, position limits, invalid operations.
 * Maps to HTTP 409 Conflict.
 */
public class BusinessRuleException extends RuntimeException {

    public BusinessRuleException(String message) {
        super(message);
    }

    public BusinessRuleException(String message, Throwable cause) {
        super(message, cause);
    }
}
