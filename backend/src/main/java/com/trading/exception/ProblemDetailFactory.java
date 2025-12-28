package com.trading.exception;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;

import java.net.URI;
import java.util.Map;

/**
 * Factory for creating RFC 7807 ProblemDetail responses.
 * Provides standardized error responses across the API.
 */
public class ProblemDetailFactory {

    private static final String ERROR_TYPE_BASE_URI = "https://trading.example.com/errors/";

    /**
     * Creates a ProblemDetail for resource not found errors (404).
     *
     * @param detail   detailed error message
     * @param instance the request URI where the error occurred
     * @return ProblemDetail with status 404
     */
    public static ProblemDetail resourceNotFound(String detail, String instance) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, detail);
        problem.setType(URI.create(ERROR_TYPE_BASE_URI + "resource-not-found"));
        problem.setTitle("Resource Not Found");
        problem.setInstance(URI.create(instance));
        return problem;
    }

    /**
     * Creates a ProblemDetail for business rule violations (409).
     * Examples: insufficient funds, position limits exceeded, invalid operations.
     *
     * @param detail   detailed error message
     * @param instance the request URI where the error occurred
     * @return ProblemDetail with status 409
     */
    public static ProblemDetail businessRuleViolation(String detail, String instance) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, detail);
        problem.setType(URI.create(ERROR_TYPE_BASE_URI + "business-rule-violation"));
        problem.setTitle("Business Rule Violation");
        problem.setInstance(URI.create(instance));
        return problem;
    }

    /**
     * Creates a ProblemDetail for invalid request errors (400).
     * Used for IllegalArgumentException and similar validation errors.
     *
     * @param detail   detailed error message
     * @param instance the request URI where the error occurred
     * @return ProblemDetail with status 400
     */
    public static ProblemDetail invalidRequest(String detail, String instance) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, detail);
        problem.setType(URI.create(ERROR_TYPE_BASE_URI + "invalid-request"));
        problem.setTitle("Invalid Request");
        problem.setInstance(URI.create(instance));
        return problem;
    }

    /**
     * Creates a ProblemDetail for validation errors (400).
     * Includes field-level validation errors in the response.
     *
     * @param detail           general validation error message
     * @param instance         the request URI where the error occurred
     * @param validationErrors map of field names to error messages
     * @return ProblemDetail with status 400 and validation errors
     */
    public static ProblemDetail validationError(String detail, String instance, Map<String, String> validationErrors) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, detail);
        problem.setType(URI.create(ERROR_TYPE_BASE_URI + "validation-error"));
        problem.setTitle("Validation Error");
        problem.setInstance(URI.create(instance));
        problem.setProperty("validationErrors", validationErrors);
        return problem;
    }

    /**
     * Creates a ProblemDetail for internal server errors (500).
     *
     * @param detail   detailed error message (should be sanitized in production)
     * @param instance the request URI where the error occurred
     * @return ProblemDetail with status 500
     */
    public static ProblemDetail internalError(String detail, String instance) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR, detail);
        problem.setType(URI.create(ERROR_TYPE_BASE_URI + "internal-error"));
        problem.setTitle("Internal Server Error");
        problem.setInstance(URI.create(instance));
        return problem;
    }
}
