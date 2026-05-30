package com.trading.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * Configuration for trading-domain typed properties.
 *
 * <p>Registers {@link AgentProperties} (bound to {@code trading.agents.*})
 * and {@link TradingPublicProperties} (bound to {@code trading.public.*}).
 * Mirrors the registration pattern used by {@link SecurityConfig} for
 * {@link SecurityProperties} and {@link RestClientConfig} for
 * {@link AgentsApiProperties}.
 */
@Configuration
@EnableConfigurationProperties({AgentProperties.class, TradingPublicProperties.class})
public class TradingConfig {
}
