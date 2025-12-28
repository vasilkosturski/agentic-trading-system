package com.trading.exception;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;

import java.net.URI;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class ProblemDetailFactoryTest {

    @Test
    void testResourceNotFound() {
        // Given
        String detail = "Agent not found: Warren";
        String instance = "/api/accounts/999";

        // When
        ProblemDetail problem = ProblemDetailFactory.resourceNotFound(detail, instance);

        // Then
        assertThat(problem.getStatus()).isEqualTo(HttpStatus.NOT_FOUND.value());
        assertThat(problem.getTitle()).isEqualTo("Resource Not Found");
        assertThat(problem.getDetail()).isEqualTo(detail);
        assertThat(problem.getType()).isEqualTo(URI.create("https://trading.example.com/errors/resource-not-found"));
        assertThat(problem.getInstance()).isEqualTo(URI.create(instance));
    }

    @Test
    void testBusinessRuleViolation() {
        // Given
        String detail = "Insufficient funds: Need $1500.00, have $1000.00";
        String instance = "/api/accounts/1/trades";

        // When
        ProblemDetail problem = ProblemDetailFactory.businessRuleViolation(detail, instance);

        // Then
        assertThat(problem.getStatus()).isEqualTo(HttpStatus.CONFLICT.value());
        assertThat(problem.getTitle()).isEqualTo("Business Rule Violation");
        assertThat(problem.getDetail()).isEqualTo(detail);
        assertThat(problem.getType()).isEqualTo(URI.create("https://trading.example.com/errors/business-rule-violation"));
        assertThat(problem.getInstance()).isEqualTo(URI.create(instance));
    }

    @Test
    void testInvalidRequest() {
        // Given
        String detail = "Invalid agent ID: must be positive";
        String instance = "/api/accounts/-1/balance";

        // When
        ProblemDetail problem = ProblemDetailFactory.invalidRequest(detail, instance);

        // Then
        assertThat(problem.getStatus()).isEqualTo(HttpStatus.BAD_REQUEST.value());
        assertThat(problem.getTitle()).isEqualTo("Invalid Request");
        assertThat(problem.getDetail()).isEqualTo(detail);
        assertThat(problem.getType()).isEqualTo(URI.create("https://trading.example.com/errors/invalid-request"));
        assertThat(problem.getInstance()).isEqualTo(URI.create(instance));
    }

    @Test
    void testValidationError() {
        // Given
        String detail = "Validation failed for request";
        String instance = "/api/accounts";
        Map<String, String> validationErrors = Map.of(
            "name", "must not be blank",
            "initialBalance", "must be positive"
        );

        // When
        ProblemDetail problem = ProblemDetailFactory.validationError(detail, instance, validationErrors);

        // Then
        assertThat(problem.getStatus()).isEqualTo(HttpStatus.BAD_REQUEST.value());
        assertThat(problem.getTitle()).isEqualTo("Validation Error");
        assertThat(problem.getDetail()).isEqualTo(detail);
        assertThat(problem.getType()).isEqualTo(URI.create("https://trading.example.com/errors/validation-error"));
        assertThat(problem.getInstance()).isEqualTo(URI.create(instance));
        assertThat(problem.getProperties()).containsEntry("validationErrors", validationErrors);
    }

    @Test
    void testInternalError() {
        // Given
        String detail = "Database connection failed";
        String instance = "/api/accounts/1/balance";

        // When
        ProblemDetail problem = ProblemDetailFactory.internalError(detail, instance);

        // Then
        assertThat(problem.getStatus()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR.value());
        assertThat(problem.getTitle()).isEqualTo("Internal Server Error");
        assertThat(problem.getDetail()).isEqualTo(detail);
        assertThat(problem.getType()).isEqualTo(URI.create("https://trading.example.com/errors/internal-error"));
        assertThat(problem.getInstance()).isEqualTo(URI.create(instance));
    }
}
