package com.trading.config;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

/**
 * Type-safe configuration for the public-facing slice of the trading API.
 *
 * <p>Centralises the publicly-visible knobs that gate what unauthenticated
 * callers can see. Today this is just the legal-protection display delay;
 * future additions (rate limits, sample-size caps, redaction toggles) belong
 * here too.
 *
 * <p>Configuration in application.yml:
 * <pre>
 * trading:
 *   public:
 *     display-delay-days: 7
 * </pre>
 *
 * <p>Mirrors the registration pattern used by {@link AgentProperties} (bound
 * via {@code @EnableConfigurationProperties} on {@link TradingConfig}).
 */
@ConfigurationProperties(prefix = "trading.public")
@Validated
public class TradingPublicProperties {

    /**
     * Number of days that must elapse before a trading run becomes visible on
     * the public API. {@code 0} disables the delay (everything is public).
     */
    @NotNull
    @PositiveOrZero
    private Integer displayDelayDays;

    public Integer getDisplayDelayDays() {
        return displayDelayDays;
    }

    public void setDisplayDelayDays(Integer displayDelayDays) {
        this.displayDelayDays = displayDelayDays;
    }
}
