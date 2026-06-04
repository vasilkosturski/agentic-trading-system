package com.trading.config;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

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
 *         style: "Value Investor"
 *       george:
 *         initial-capital: 100000
 *         style: "Contrarian Macro"
 * </pre>
 *
 * <p>YAML keys MUST be lowercase. Spring's relaxed-binding rules do not normalize
 * {@code Map<String, ?>} keys — they're preserved as written. {@link #getInitialCapital(String)}
 * and {@link #getStyle(String)} lowercase the caller's input before lookup, so callers
 * may pass any case (e.g. {@code "Warren"} or {@code "warren"}), but YAML keys with
 * uppercase characters will not resolve.
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
     * Resolve the display style for the given agent name. The caller's name is lowercased
     * before lookup, so any case is accepted (e.g. {@code "Warren"} or {@code "warren"}).
     *
     * <p>Returns empty if no profile is registered — style is display-only metadata; absence
     * is harmless. This is intentionally asymmetric with {@link #getInitialCapital(String)},
     * which throws because a missing initial capital would silently break PnL math.
     *
     * @param agentName the agent name to look up (any case); {@code null} is accepted and yields empty
     * @return the configured style, or {@link Optional#empty()} if no profile is registered
     */
    public Optional<String> getStyle(String agentName) {
        if (agentName == null) {
            return Optional.empty();
        }
        AgentConfig cfg = profiles.get(agentName.toLowerCase());
        return cfg == null ? Optional.empty() : Optional.ofNullable(cfg.getStyle());
    }

    /**
     * Per-agent configuration values. Public static nested class is required so
     * Spring Boot's relaxed binder can instantiate map values.
     */
    public static class AgentConfig {

        @NotNull
        @Positive
        private Double initialCapital;

        @NotBlank
        private String style;

        public Double getInitialCapital() {
            return initialCapital;
        }

        public void setInitialCapital(Double initialCapital) {
            this.initialCapital = initialCapital;
        }

        public String getStyle() {
            return style;
        }

        public void setStyle(String style) {
            this.style = style;
        }
    }
}
