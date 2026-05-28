package com.trading.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

import java.util.HashMap;
import java.util.Map;

/**
 * Type-safe per-agent configuration bound to {@code trading.agents.*}.
 *
 * <p>Configuration in application.yml:
 * <pre>
 * trading:
 *   agents:
 *     profiles:
 *       warren:
 *         initial-capital: 100000
 *       george:
 *         initial-capital: 100000
 * </pre>
 *
 * <p>YAML keys MUST be lowercase. Spring's relaxed-binding rules do not normalize
 * {@code Map<String, ?>} keys — they're preserved as written. {@link #getInitialCapital(String)}
 * lowercases the caller's input before lookup, so callers may pass any case (e.g.
 * {@code "Warren"} or {@code "warren"}), but YAML keys with uppercase characters
 * will not resolve.
 */
@ConfigurationProperties(prefix = "trading.agents")
@Validated
public class AgentProperties {

    /**
     * Per-agent profile map keyed by lowercase agent name.
     * Defaults live in application.yml so configuration stays in one place.
     */
    @Valid
    private Map<String, AgentConfig> profiles = new HashMap<>();

    public Map<String, AgentConfig> getProfiles() {
        return profiles;
    }

    public void setProfiles(Map<String, AgentConfig> profiles) {
        this.profiles = profiles;
    }

    /**
     * Resolve initial capital for the given agent name. The caller's name is lowercased
     * before lookup, so any case is accepted (e.g. {@code "Warren"} or {@code "warren"}).
     * YAML keys must be lowercase for the lookup to resolve — see the class-level Javadoc.
     *
     * @throws IllegalStateException if no profile is registered for the agent
     */
    public double getInitialCapital(String agentName) {
        if (agentName == null) {
            throw new IllegalStateException("No initial-capital configured for agent: null");
        }
        AgentConfig cfg = profiles.get(agentName.toLowerCase());
        if (cfg == null) {
            throw new IllegalStateException("No initial-capital configured for agent: " + agentName);
        }
        return cfg.getInitialCapital();
    }

    /**
     * Per-agent configuration values. Public static nested class is required so
     * Spring Boot's relaxed binder can instantiate map values.
     */
    public static class AgentConfig {

        @NotNull
        @Positive
        private Double initialCapital;

        public Double getInitialCapital() {
            return initialCapital;
        }

        public void setInitialCapital(Double initialCapital) {
            this.initialCapital = initialCapital;
        }
    }
}
