package com.trading.config;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

/**
 * Type-safe configuration properties for Agents API.
 *
 * Binds properties from application.yml with prefix "agents.api" to this class.
 * Provides validation, IDE autocomplete, and centralized configuration.
 *
 * All default values are defined in application.yml, not here.
 * This keeps configuration in one place where it's visible and easy to change.
 *
 * Configuration in application.yml:
 * <pre>
 * agents:
 *   api:
 *     url: ${AGENTS_API_URL:http://agents-service:8000}
 *     connect-timeout: 30000
 *     read-timeout: 60000
 * </pre>
 */
@ConfigurationProperties(prefix = "agents.api")
@Validated
public class AgentsApiProperties {

    /**
     * Base URL of the agents service API.
     * Default defined in application.yml.
     */
    @NotBlank
    private String url;

    /**
     * Connection timeout in milliseconds.
     * Default defined in application.yml.
     */
    @Positive
    private int connectTimeout;

    /**
     * Read timeout in milliseconds.
     * Default defined in application.yml.
     */
    @Positive
    private int readTimeout;

    // Getters and setters required for @ConfigurationProperties

    public String getUrl() {
        return url;
    }

    public void setUrl(String url) {
        this.url = url;
    }

    public int getConnectTimeout() {
        return connectTimeout;
    }

    public void setConnectTimeout(int connectTimeout) {
        this.connectTimeout = connectTimeout;
    }

    public int getReadTimeout() {
        return readTimeout;
    }

    public void setReadTimeout(int readTimeout) {
        this.readTimeout = readTimeout;
    }
}
