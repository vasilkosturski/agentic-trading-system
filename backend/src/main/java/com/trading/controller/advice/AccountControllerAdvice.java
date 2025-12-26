package com.trading.controller.advice;

import com.trading.controller.AccountController;
import com.trading.dto.response.ToolResponse;
import com.trading.exception.BusinessRuleException;
import com.trading.exception.ResourceNotFoundException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * Global exception handler for AccountController.
 * Centralizes error handling logic and provides consistent error responses.
 */
@RestControllerAdvice(assignableTypes = AccountController.class)
public class AccountControllerAdvice {

    private static final Logger logger = LoggerFactory.getLogger(AccountControllerAdvice.class);

    /**
     * Handles ResourceNotFoundException - when a requested resource is not found.
     * Maps to HTTP 404 Not Found.
     */
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ToolResponse<Object>> handleResourceNotFound(ResourceNotFoundException ex) {
        logger.warn("Resource not found: {}", ex.getMessage());
        return ResponseEntity.status(404).body(ToolResponse.error(ex.getMessage()));
    }

    /**
     * Handles BusinessRuleException - when a business rule is violated.
     * Examples: insufficient funds, position limits, invalid operations.
     * Maps to HTTP 409 Conflict.
     */
    @ExceptionHandler(BusinessRuleException.class)
    public ResponseEntity<ToolResponse<Object>> handleBusinessRule(BusinessRuleException ex) {
        logger.warn("Business rule violation: {}", ex.getMessage());
        return ResponseEntity.status(409).body(ToolResponse.error(ex.getMessage()));
    }

    /**
     * Handles MethodArgumentNotValidException - Spring validation failures.
     * Thrown when @Valid annotation finds validation errors in request DTOs.
     * Returns 400 Bad Request.
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ToolResponse<Object>> handleValidationException(MethodArgumentNotValidException ex) {
        String errorMessage = ex.getBindingResult().getFieldErrors().stream()
            .map(error -> error.getField() + ": " + error.getDefaultMessage())
            .findFirst()
            .orElse("Validation failed");
        logger.warn("Validation error: {}", errorMessage);
        return ResponseEntity.badRequest().body(ToolResponse.error(errorMessage));
    }

    /**
     * Handles IllegalArgumentException - typically validation errors or bad input.
     * Returns 400 Bad Request.
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ToolResponse<Object>> handleIllegalArgument(IllegalArgumentException ex) {
        logger.warn("Bad request: {}", ex.getMessage());
        return ResponseEntity.badRequest().body(ToolResponse.error(ex.getMessage()));
    }

    /**
     * Handles generic Exception - catch-all for unexpected errors.
     * Returns 500 Internal Server Error.
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ToolResponse<Object>> handleGenericException(Exception ex) {
        logger.error("Unexpected error", ex);
        return ResponseEntity.status(500).body(ToolResponse.error("Internal server error: " + ex.getMessage()));
    }
}
