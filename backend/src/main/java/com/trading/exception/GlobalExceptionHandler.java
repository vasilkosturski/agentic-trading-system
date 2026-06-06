package com.trading.exception;

import jakarta.servlet.http.HttpServletRequest;
import java.util.NoSuchElementException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.RestClientException;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger logger = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ProblemDetail> handleIllegalArgument(
            IllegalArgumentException ex, HttpServletRequest request) {
        logger.warn("Invalid argument: {}", ex.getMessage());
        ProblemDetail problem = ProblemDetailFactory.invalidRequest(ex.getMessage(), request.getRequestURI());
        return ResponseEntity.badRequest().body(problem);
    }

    @ExceptionHandler(NoSuchElementException.class)
    public ResponseEntity<ProblemDetail> handleNotFound(NoSuchElementException ex, HttpServletRequest request) {
        logger.warn("Resource not found: {}", ex.getMessage());
        ProblemDetail problem = ProblemDetailFactory.resourceNotFound(ex.getMessage(), request.getRequestURI());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(problem);
    }

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ProblemDetail> handleResourceNotFound(
            ResourceNotFoundException ex, HttpServletRequest request) {
        logger.warn("Resource not found: {}", ex.getMessage());
        ProblemDetail problem = ProblemDetailFactory.resourceNotFound(ex.getMessage(), request.getRequestURI());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(problem);
    }

    @ExceptionHandler(RestClientException.class)
    public ResponseEntity<ProblemDetail> handleRestClientException(RestClientException ex, HttpServletRequest request) {
        logger.error("External service call failed: {}", ex.getMessage());
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.SERVICE_UNAVAILABLE, "External service unavailable: " + ex.getMessage());
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
        throw ex; // Re-throw for Spring Security to handle
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ProblemDetail> handleGenericException(Exception ex, HttpServletRequest request) {
        logger.error("Unexpected error occurred: {}", ex.getMessage(), ex);
        String message = ex.getMessage() != null ? ex.getMessage() : "An unexpected error occurred";
        ProblemDetail problem = ProblemDetailFactory.internalError(message, request.getRequestURI());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(problem);
    }
}
