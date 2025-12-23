package com.trading.exception;

import com.trading.dto.response.ToolResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.RestClientException;

import java.util.NoSuchElementException;

/**
 * Global exception handler for all REST controllers.
 *
 * Handles common/generic exceptions that occur across multiple endpoints.
 * Endpoint-specific business logic errors should remain in their respective
 * controllers for clarity.
 *
 * Uses @RestControllerAdvice to automatically handle exceptions thrown from
 * any @RestController in the application.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger logger = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /**
     * Handles illegal argument exceptions (invalid input parameters).
     * Returns 400 Bad Request.
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ToolResponse<Void>> handleIllegalArgument(IllegalArgumentException ex) {
        logger.warn("Invalid argument: {}", ex.getMessage());
        return ResponseEntity.badRequest()
                .body(ToolResponse.error(ex.getMessage()));
    }

    /**
     * Handles not found exceptions (missing resources).
     * Returns 404 Not Found.
     */
    @ExceptionHandler(NoSuchElementException.class)
    public ResponseEntity<ToolResponse<Void>> handleNotFound(NoSuchElementException ex) {
        logger.warn("Resource not found: {}", ex.getMessage());
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(ToolResponse.error(ex.getMessage()));
    }

    /**
     * Handles REST client exceptions (external service calls).
     * Returns 503 Service Unavailable.
     *
     * Note: Endpoint-specific RestClientException handling can override this
     * by catching the exception in the controller before it reaches here.
     */
    @ExceptionHandler(RestClientException.class)
    public ResponseEntity<ToolResponse<Void>> handleRestClientException(RestClientException ex) {
        logger.error("External service call failed: {}", ex.getMessage());
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(ToolResponse.error("External service unavailable: " + ex.getMessage()));
    }

    /**
     * Fallback handler for any unexpected exceptions.
     * Returns 500 Internal Server Error.
     *
     * This should catch any exceptions not handled by more specific handlers.
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ToolResponse<Void>> handleGenericException(Exception ex) {
        logger.error("Unexpected error occurred: {}", ex.getMessage(), ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ToolResponse.error(ex.getMessage() != null ? ex.getMessage() : "An unexpected error occurred"));
    }
}
