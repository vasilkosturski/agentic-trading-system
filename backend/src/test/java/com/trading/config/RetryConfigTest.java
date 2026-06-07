package com.trading.config;

import static org.junit.jupiter.api.Assertions.*;

import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.retry.backoff.NoBackOffPolicy;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;

@DisplayName("RetryConfig Tests")
class RetryConfigTest {

    private RetryTemplate buildTemplate() {
        RetryTemplate template = new RetryConfig().retryTemplate();
        // Disable the exponential back-off in tests so we don't pay 500ms+1s+2s per case.
        template.setBackOffPolicy(new NoBackOffPolicy());
        return template;
    }

    @Test
    @DisplayName("retryTemplate does not retry on HTTP 429 - callable invoked exactly once")
    void retryTemplate_doesNotRetry_on429() {
        RetryTemplate template = buildTemplate();
        AtomicInteger count = new AtomicInteger();

        assertThrows(
                HttpClientErrorException.class,
                () -> template.execute(ctx -> {
                    count.incrementAndGet();
                    throw HttpClientErrorException.create(
                            HttpStatus.TOO_MANY_REQUESTS, "Too Many Requests", null, null, null);
                }));

        assertEquals(1, count.get(), "429s must not be retried");
    }

    @Test
    @DisplayName("retryTemplate retries 3 times on HTTP 500 - callable invoked 4 times")
    void retryTemplate_retries3Times_on500() {
        RetryTemplate template = buildTemplate();
        AtomicInteger count = new AtomicInteger();

        assertThrows(
                HttpServerErrorException.class,
                () -> template.execute(ctx -> {
                    count.incrementAndGet();
                    throw HttpServerErrorException.create(
                            HttpStatus.INTERNAL_SERVER_ERROR, "Server Error", null, null, null);
                }));

        assertEquals(4, count.get(), "non-429 RestClientException should be retried 3 times (4 total)");
    }
}
