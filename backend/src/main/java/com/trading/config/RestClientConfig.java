package com.trading.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/**
 * Configuration for REST client beans.
 *
 * Uses modern RestClient (Spring 6.1+) instead of deprecated RestTemplate.
 * Combined with Virtual Threads (Java 21), this provides async performance
 * with synchronous code simplicity - no callbacks, no reactive complexity!
 *
 * Virtual Threads: Blocking-style code automatically becomes non-blocking.
 * RestClient: Modern, fluent API with full Spring Boot 3.2+ support.
 */
@Configuration
@EnableConfigurationProperties(AgentsApiProperties.class)
public class RestClientConfig {

    /**
     * Creates a RestClient bean configured for communicating with the agents service.
     *
     * With Virtual Threads enabled, this synchronous client automatically provides
     * async-like performance without callback complexity.
     *
     * Key features:
     * - Type-safe qualifier (@AgentsClient) for injection
     * - Configurable timeouts from AgentsApiProperties
     * - Base URL pre-configured
     * - Works seamlessly with Virtual Threads
     *
     * @param properties Type-safe configuration properties for agents API
     * @return Configured RestClient for agents service communication
     */
    @Bean
    @AgentsClient
    public RestClient agentsRestClient(AgentsApiProperties properties) {
        // Configure request factory with timeouts
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(properties.getConnectTimeout());
        factory.setReadTimeout(properties.getReadTimeout());

        return RestClient.builder()
                .baseUrl(properties.getUrl())
                .requestFactory(factory)
                .build();
    }
}
