package com.trading.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

/**
 * HTTP client beans for simple outbound calls.
 *
 * <p>Exposes a {@link RestTemplate} bean so consumers can constructor-inject it instead of
 * instantiating {@code new RestTemplate()} inline. This keeps service classes free of
 * test-only constructor overloads.</p>
 */
@Configuration
class HttpConfig {

    @Bean
    RestTemplate restTemplate() {
        return new RestTemplate();
    }
}
