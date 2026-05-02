package com.trading.exception;

import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
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
 *
 * Returns RFC 7807 ProblemDetail responses for consistent error formatting.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger logger = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /**
     * Handles illegal argument exceptions (invalid input parameters).
     * Returns 400 Bad Request.
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ProblemDetail> handleIllegalArgument(IllegalArgumentException ex, HttpServletRequest request) {
        logger.warn("Invalid argument: {}", ex.getMessage());
        ProblemDetail problem = ProblemDetailFactory.invalidRequest(ex.getMessage(), request.getRequestURI());
        return ResponseEntity.badRequest().body(problem);
    }

    /**
     * Handles not found exceptions (missing resources).
     * Returns 404 Not Found.
     */
    @ExceptionHandler(NoSuchElementException.class)
    public ResponseEntity<ProblemDetail> handleNotFound(NoSuchElementException ex, HttpServletRequest request) {
        logger.warn("Resource not found: {}", ex.getMessage());
        ProblemDetail problem = ProblemDetailFactory.resourceNotFound(ex.getMessage(), request.getRequestURI());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(problem);
    }

    /**
     * Handles ResourceNotFoundException (custom not found exception).
     * Returns 404 Not Found.
     */
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ProblemDetail> handleResourceNotFound(ResourceNotFoundException ex, HttpServletRequest request) {
        logger.warn("Resource not found: {}", ex.getMessage());
        ProblemDetail problem = ProblemDetailFactory.resourceNotFound(ex.getMessage(), request.getRequestURI());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(problem);
    }

    /**
     * Handles REST client exceptions (external service calls).
     * Returns 503 Service Unavailable.
     *
     * Note: Endpoint-specific RestClientException handling can override this
     * by catching the exception in the controller before it reaches here.
     */
    @ExceptionHandler(RestClientException.class)
    public ResponseEntity<ProblemDetail> handleRestClientException(RestClientException ex, HttpServletRequest request) {
        logger.error("External service call failed: {}", ex.getMessage());
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
            HttpStatus.SERVICE_UNAVAILABLE,
            "External service unavailable: " + ex.getMessage()
        );
        problem.setTitle("Service Unavailable");
        problem.setInstance(java.net.URI.create(request.getRequestURI()));
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(problem);
    }

    /**
     * Handles Spring Security access denied exceptions.
     * Re-throws the exception so Spring Security's ExceptionTranslationFilter can handle it.
     * This ensures proper 403 Forbidden responses for @PreAuthorize violations.
     *
     * Without this handler, the generic Exception handler below would catch AccessDeniedException
     * and return 500 Internal Server Error instead of 403 Forbidden.
     */
    @ExceptionHandler(AccessDeniedException.class)
    public void handleAccessDenied(AccessDeniedException ex) throws AccessDeniedException {
        logger.warn("Access denied: {}", ex.getMessage());
        throw ex;  // Re-throw for Spring Security to handle
    }

    /**
     * Fallback handler for any unexpected exceptions.
     * Returns 500 Internal Server Error.
     *
     * This should catch any exceptions not handled by more specific handlers.
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ProblemDetail> handleGenericException(Exception ex, HttpServletRequest request) {
        logger.error("Unexpected error occurred: {}", ex.getMessage(), ex);
        String message = ex.getMessage() != null ? ex.getMessage() : "An unexpected error occurred";
        ProblemDetail problem = ProblemDetailFactory.internalError(message, request.getRequestURI());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(problem);
    }
}
