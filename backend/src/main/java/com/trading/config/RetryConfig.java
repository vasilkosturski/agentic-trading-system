package com.trading.config;

import java.util.Map;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.retry.annotation.EnableRetry;
import org.springframework.retry.backoff.ExponentialBackOffPolicy;
import org.springframework.retry.policy.SimpleRetryPolicy;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.web.client.HttpClientErrorException;
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

        // 429s are per-minute rate-limit signals: the bucket is already exhausted, so an
        // immediate retry within the same window is mechanically futile. PriceCacheService
        // handles 429s separately via a process-local cool-down + stale-cache fallback.
        // Other RestClientException subtypes (5xx, network failures, timeouts) still get
        // 3 retries with the exponential back-off below.
        SimpleRetryPolicy retryPolicy = new SimpleRetryPolicy(4, Map.of(RestClientException.class, true), true) {
            @Override
            public boolean canRetry(org.springframework.retry.RetryContext context) {
                Throwable lastThrowable = context.getLastThrowable();
                if (isRateLimit(lastThrowable)) {
                    return false;
                }
                return super.canRetry(context);
            }
        };
        template.setRetryPolicy(retryPolicy);

        // Exponential backoff: 500ms → 1s → 2s
        ExponentialBackOffPolicy backOff = new ExponentialBackOffPolicy();
        backOff.setInitialInterval(500L);
        backOff.setMultiplier(2.0);
        backOff.setMaxInterval(5000L);
        template.setBackOffPolicy(backOff);

        return template;
    }

    private static boolean isRateLimit(Throwable t) {
        if (t == null) {
            return false;
        }
        if (t instanceof HttpClientErrorException.TooManyRequests) {
            return true;
        }
        String msg = t.getMessage();
        return msg != null && msg.contains("429");
    }
}
