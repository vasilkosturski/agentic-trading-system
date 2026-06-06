package com.trading.exception;

import java.net.URI;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;

public class ProblemDetailFactory {

    private static final String ERROR_TYPE_BASE_URI = "https://trading.example.com/errors/";

    public static ProblemDetail resourceNotFound(String detail, String instance) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, detail);
        problem.setType(URI.create(ERROR_TYPE_BASE_URI + "resource-not-found"));
        problem.setTitle("Resource Not Found");
        problem.setInstance(URI.create(instance));
        return problem;
    }

    public static ProblemDetail businessRuleViolation(String detail, String instance) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, detail);
        problem.setType(URI.create(ERROR_TYPE_BASE_URI + "business-rule-violation"));
        problem.setTitle("Business Rule Violation");
        problem.setInstance(URI.create(instance));
        return problem;
    }

    public static ProblemDetail invalidRequest(String detail, String instance) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, detail);
        problem.setType(URI.create(ERROR_TYPE_BASE_URI + "invalid-request"));
        problem.setTitle("Invalid Request");
        problem.setInstance(URI.create(instance));
        return problem;
    }

    public static ProblemDetail validationError(String detail, String instance, Map<String, String> validationErrors) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, detail);
        problem.setType(URI.create(ERROR_TYPE_BASE_URI + "validation-error"));
        problem.setTitle("Validation Error");
        problem.setInstance(URI.create(instance));
        problem.setProperty("validationErrors", validationErrors);
        return problem;
    }

    public static ProblemDetail internalError(String detail, String instance) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR, detail);
        problem.setType(URI.create(ERROR_TYPE_BASE_URI + "internal-error"));
        problem.setTitle("Internal Server Error");
        problem.setInstance(URI.create(instance));
        return problem;
    }
}
