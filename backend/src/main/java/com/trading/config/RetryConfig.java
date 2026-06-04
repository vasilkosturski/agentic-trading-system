package com.trading.config;

import java.util.Map;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.retry.annotation.EnableRetry;
import org.springframework.retry.backoff.ExponentialBackOffPolicy;
import org.springframework.retry.policy.SimpleRetryPolicy;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.web.client.RestClientException;

/**
 * Centralized retry configuration for all external API calls.
 * Uses spring-retry with exponential backoff.
 *
 * Inject RetryTemplate into any service making network calls:
 *   retryTemplate.execute(ctx -> restTemplate.getForObject(...))
 */
@Configuration
@EnableRetry
public class RetryConfig {

    @Bean
    public RetryTemplate retryTemplate() {
        RetryTemplate template = new RetryTemplate();

        // Retry up to 3 times on transient HTTP errors
        SimpleRetryPolicy retryPolicy = new SimpleRetryPolicy(3, Map.of(RestClientException.class, true), true);
        template.setRetryPolicy(retryPolicy);

        // Exponential backoff: 500ms → 1s → 2s
        ExponentialBackOffPolicy backOff = new ExponentialBackOffPolicy();
        backOff.setInitialInterval(500L);
        backOff.setMultiplier(2.0);
        backOff.setMaxInterval(5000L);
        template.setBackOffPolicy(backOff);

        return template;
    }
}
