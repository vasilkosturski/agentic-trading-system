package com.trading.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties({AgentProperties.class, TradingPublicProperties.class})
public class TradingConfig {}
