package com.trading.config;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.boot.autoconfigure.context.ConfigurationPropertiesAutoConfiguration;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Context-load tests for {@link AgentProperties}.
 *
 * <p>Uses {@link ApplicationContextRunner} to spin up a minimal Spring context that
 * registers the {@code @ConfigurationProperties} bean and binds it from inline
 * properties. Mirrors {@link SecurityPropertiesTest}'s pattern — keeps the test
 * fast and self-contained while still exercising real Spring Boot binding.
 *
 * <p>The inline property values mirror application.yml's {@code trading.agents.profiles}
 * block, so a regression in either side surfaces here.
 */
@DisplayName("AgentProperties context-load tests")
class AgentPropertiesTest {

    private final ApplicationContextRunner contextRunner = new ApplicationContextRunner()
        .withConfiguration(AutoConfigurations.of(
            ConfigurationPropertiesAutoConfiguration.class))
        .withUserConfiguration(AgentPropertiesTestConfig.class)
        .withPropertyValues(
            "trading.agents.profiles.warren.initial-capital=100000",
            "trading.agents.profiles.warren.style=Value Investor",
            "trading.agents.profiles.george.initial-capital=100000",
            "trading.agents.profiles.george.style=Contrarian Macro",
            "trading.agents.profiles.ray.initial-capital=100000",
            "trading.agents.profiles.ray.style=Risk Parity",
            "trading.agents.profiles.cathie.initial-capital=100000",
            "trading.agents.profiles.cathie.style=Growth Innovation",
            "trading.agents.profiles.testagent.initial-capital=100000",
            "trading.agents.profiles.testagent.style=Test Style"
        );

    @Test
    @DisplayName("YAML binding populates style for all 4 production agents + testagent")
    void stylesBindForAllConfiguredAgents() {
        contextRunner.run(context -> {
            AgentProperties props = context.getBean(AgentProperties.class);

            assertThat(props.getProfiles().get("warren").getStyle()).isEqualTo("Value Investor");
            assertThat(props.getProfiles().get("george").getStyle()).isEqualTo("Contrarian Macro");
            assertThat(props.getProfiles().get("ray").getStyle()).isEqualTo("Risk Parity");
            assertThat(props.getProfiles().get("cathie").getStyle()).isEqualTo("Growth Innovation");
            assertThat(props.getProfiles().get("testagent").getStyle()).isEqualTo("Test Style");
        });
    }

    @Test
    @DisplayName("getStyle(\"Warren\") returns Optional.of(\"Value Investor\") — case-insensitive lookup")
    void getStyleIsCaseInsensitive() {
        contextRunner.run(context -> {
            AgentProperties props = context.getBean(AgentProperties.class);

            assertThat(props.getStyle("Warren")).isEqualTo(Optional.of("Value Investor"));
            assertThat(props.getStyle("warren")).isEqualTo(Optional.of("Value Investor"));
        });
    }

    @Test
    @DisplayName("getStyle(\"unknown\") returns Optional.empty() — lenient for display-only metadata")
    void getStyleReturnsEmptyForUnknownAgent() {
        contextRunner.run(context -> {
            AgentProperties props = context.getBean(AgentProperties.class);

            assertThat(props.getStyle("unknown")).isEmpty();
        });
    }

    @Test
    @DisplayName("getStyle(null) returns Optional.empty() — defensive null handling")
    void getStyleReturnsEmptyForNullAgentName() {
        contextRunner.run(context -> {
            AgentProperties props = context.getBean(AgentProperties.class);

            assertThat(props.getStyle(null)).isEmpty();
        });
    }

    /**
     * Minimal config class to enable {@link AgentProperties} in the test context
     * without dragging in unrelated trading-domain beans.
     */
    @org.springframework.context.annotation.Configuration
    @org.springframework.boot.context.properties.EnableConfigurationProperties(AgentProperties.class)
    static class AgentPropertiesTestConfig {
    }
}
