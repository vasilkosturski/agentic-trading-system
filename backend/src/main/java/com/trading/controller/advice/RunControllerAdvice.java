package com.trading.controller.advice;

import com.trading.controller.RunController;
import com.trading.exception.BusinessRuleException;
import com.trading.exception.ProblemDetailFactory;
import com.trading.exception.ResourceNotFoundException;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * Global exception handler for RunController.
 * Centralizes error handling logic and provides consistent RFC 7807 ProblemDetail responses.
 */
@RestControllerAdvice(assignableTypes = RunController.class)
public class RunControllerAdvice {

    private static final Logger logger = LoggerFactory.getLogger(RunControllerAdvice.class);

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
