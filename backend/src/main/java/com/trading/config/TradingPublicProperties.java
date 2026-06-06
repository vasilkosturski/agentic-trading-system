package com.trading.config;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@ConfigurationProperties(prefix = "trading.public")
@Validated
public class TradingPublicProperties {

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
