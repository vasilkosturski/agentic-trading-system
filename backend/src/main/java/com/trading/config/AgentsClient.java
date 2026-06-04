package com.trading.config;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
import org.springframework.beans.factory.annotation.Qualifier;

/**
 * Type-safe qualifier for the agents service REST client.
 *
 * This custom qualifier annotation provides compile-time safety
 * and IDE support, avoiding string-based bean matching with @Qualifier.
 *
 * Usage:
 * <pre>
 * // Bean definition
 * {@literal @}Bean
 * {@literal @}AgentsClient
 * public RestClient agentsRestClient(...) { }
 *
 * // Injection
 * public TradingController({@literal @}AgentsClient RestClient client) { }
 * </pre>
 */
@Target({ElementType.FIELD, ElementType.METHOD, ElementType.PARAMETER, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Qualifier
public @interface AgentsClient {}
