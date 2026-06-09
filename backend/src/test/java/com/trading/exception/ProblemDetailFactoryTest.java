package com.trading.exception;

import static org.assertj.core.api.Assertions.assertThat;

import java.net.URI;
import java.util.Map;
import java.util.function.BiFunction;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;

class ProblemDetailFactoryTest {

    // The 4 single-shape factories all populate (status, title, type) from
    // hard-coded values and pass detail/instance through unchanged — parametrize
    // over the factory reference + expected status/title/type triple.
    private static Stream<Arguments> simpleFactories() {
        BiFunction<String, String, ProblemDetail> resourceNotFound = ProblemDetailFactory::resourceNotFound;
        BiFunction<String, String, ProblemDetail> businessRuleViolation = ProblemDetailFactory::businessRuleViolation;
        BiFunction<String, String, ProblemDetail> invalidRequest = ProblemDetailFactory::invalidRequest;
        BiFunction<String, String, ProblemDetail> internalError = ProblemDetailFactory::internalError;
        return Stream.of(
                Arguments.of(
                        resourceNotFound,
                        HttpStatus.NOT_FOUND,
                        "Resource Not Found",
                        "https://trading.example.com/errors/resource-not-found",
                        "Agent not found: Warren",
                        "/api/accounts/999"),
                Arguments.of(
                        businessRuleViolation,
                        HttpStatus.CONFLICT,
                        "Business Rule Violation",
                        "https://trading.example.com/errors/business-rule-violation",
                        "Insufficient funds: Need $1500.00, have $1000.00",
                        "/api/accounts/1/trades"),
                Arguments.of(
                        invalidRequest,
                        HttpStatus.BAD_REQUEST,
                        "Invalid Request",
                        "https://trading.example.com/errors/invalid-request",
                        "Invalid agent ID: must be positive",
                        "/api/accounts/-1/balance"),
                Arguments.of(
                        internalError,
                        HttpStatus.INTERNAL_SERVER_ERROR,
                        "Internal Server Error",
                        "https://trading.example.com/errors/internal-error",
                        "Database connection failed",
                        "/api/accounts/1/balance"));
    }

    @ParameterizedTest(name = "{2} → {1}")
    @MethodSource("simpleFactories")
    void simpleFactory_PopulatesStatusTitleTypeAndPassesThroughDetailInstance(
            BiFunction<String, String, ProblemDetail> factory,
            HttpStatus expectedStatus,
            String expectedTitle,
            String expectedType,
            String detail,
            String instance) {
        ProblemDetail problem = factory.apply(detail, instance);

        assertThat(problem.getStatus()).isEqualTo(expectedStatus.value());
        assertThat(problem.getTitle()).isEqualTo(expectedTitle);
        assertThat(problem.getDetail()).isEqualTo(detail);
        assertThat(problem.getType()).isEqualTo(URI.create(expectedType));
        assertThat(problem.getInstance()).isEqualTo(URI.create(instance));
    }

    @Test
    void testValidationError() {
        // Given
        String detail = "Validation failed for request";
        String instance = "/api/accounts";
        Map<String, String> validationErrors = Map.of(
                "name", "must not be blank",
                "initialBalance", "must be positive");

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
}
