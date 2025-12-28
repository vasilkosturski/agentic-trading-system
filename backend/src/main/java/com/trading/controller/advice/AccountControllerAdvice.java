package com.trading.controller.advice;

import com.trading.controller.AccountController;
import com.trading.exception.BusinessRuleException;
import com.trading.exception.ProblemDetailFactory;
import com.trading.exception.ResourceNotFoundException;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.HashMap;
import java.util.Map;

/**
 * Global exception handler for AccountController.
 * Centralizes error handling logic and provides consistent RFC 7807 ProblemDetail responses.
 */
@RestControllerAdvice(assignableTypes = AccountController.class)
public class AccountControllerAdvice {

    private static final Logger logger = LoggerFactory.getLogger(AccountControllerAdvice.class);

    /**
     * Handles ResourceNotFoundException - when a requested resource is not found.
     * Maps to HTTP 404 Not Found.
     */
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ProblemDetail> handleResourceNotFound(ResourceNotFoundException ex, HttpServletRequest request) {
        logger.warn("Resource not found: {}", ex.getMessage());
        ProblemDetail problem = ProblemDetailFactory.resourceNotFound(ex.getMessage(), request.getRequestURI());
        return ResponseEntity.status(404).body(problem);
    }

    /**
     * Handles BusinessRuleException - when a business rule is violated.
     * Examples: insufficient funds, position limits, invalid operations.
     * Maps to HTTP 409 Conflict.
     */
    @ExceptionHandler(BusinessRuleException.class)
    public ResponseEntity<ProblemDetail> handleBusinessRule(BusinessRuleException ex, HttpServletRequest request) {
        logger.warn("Business rule violation: {}", ex.getMessage());
        ProblemDetail problem = ProblemDetailFactory.businessRuleViolation(ex.getMessage(), request.getRequestURI());
        return ResponseEntity.status(409).body(problem);
    }

    /**
     * Handles MethodArgumentNotValidException - Spring validation failures.
     * Thrown when @Valid annotation finds validation errors in request DTOs.
     * Returns 400 Bad Request.
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ProblemDetail> handleValidationException(MethodArgumentNotValidException ex, HttpServletRequest request) {
        Map<String, String> validationErrors = new HashMap<>();
        ex.getBindingResult().getFieldErrors().forEach(error ->
            validationErrors.put(error.getField(), error.getDefaultMessage())
        );
        String errorMessage = "Validation failed for " + validationErrors.size() + " field(s)";
        logger.warn("Validation error: {}", validationErrors);
        ProblemDetail problem = ProblemDetailFactory.validationError(errorMessage, request.getRequestURI(), validationErrors);
        return ResponseEntity.badRequest().body(problem);
    }

    /**
     * Handles IllegalArgumentException - typically validation errors or bad input.
     * Returns 400 Bad Request.
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ProblemDetail> handleIllegalArgument(IllegalArgumentException ex, HttpServletRequest request) {
        logger.warn("Bad request: {}", ex.getMessage());
        ProblemDetail problem = ProblemDetailFactory.invalidRequest(ex.getMessage(), request.getRequestURI());
        return ResponseEntity.badRequest().body(problem);
    }

    /**
     * Handles generic Exception - catch-all for unexpected errors.
     * Returns 500 Internal Server Error.
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ProblemDetail> handleGenericException(Exception ex, HttpServletRequest request) {
        logger.error("Unexpected error", ex);
        ProblemDetail problem = ProblemDetailFactory.internalError("Internal server error: " + ex.getMessage(), request.getRequestURI());
        return ResponseEntity.status(500).body(problem);
    }
}
