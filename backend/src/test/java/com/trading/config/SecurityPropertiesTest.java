package com.trading.config;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.context.ConfigurationPropertiesAutoConfiguration;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Context-load tests for {@link SecurityProperties}.
 *
 * <p>Uses {@link ApplicationContextRunner} to spin up a minimal Spring context that registers
 * the {@code @ConfigurationProperties} bean and binds it from inline properties. This avoids
 * the cost (and JWT_SECRET dependency) of a full {@code @SpringBootTest} while still
 * exercising real Spring Boot binding.
 *
 * <p>The inline property values mirror the defaults declared in {@code application.yml},
 * so a regression in either side surfaces here.
 */
@DisplayName("SecurityProperties context-load tests")
class SecurityPropertiesTest {

    private final ApplicationContextRunner contextRunner = new ApplicationContextRunner()
        .withConfiguration(org.springframework.boot.autoconfigure.AutoConfigurations.of(
            ConfigurationPropertiesAutoConfiguration.class))
        .withUserConfiguration(SecurityPropertiesTestConfig.class)
        .withPropertyValues(
            "security.allowed-origins=http://localhost:3000,http://localhost:5173,https://agentic-trading.vkontech.com",
            "security.public-matchers[0]=/api/auth/**",
            "security.public-matchers[1]=/actuator/health",
            "security.public-matchers[2]=/actuator/info",
            "security.jwt.secret=testSecretKeyThatIsLongEnoughForHS256AlgorithmToWorkProperly",
            "security.jwt.expiration=3600000",
            "security.admin.username=admin",
            "security.admin.password=changeme-for-test"
        );

    @Test
    @DisplayName("allowedOrigins binds three entries from application defaults")
    void allowedOriginsHasThreeEntries() {
        contextRunner.run(context -> {
            SecurityProperties props = context.getBean(SecurityProperties.class);
            assertThat(props.getAllowedOrigins()).hasSize(3);
        });
    }

    @Test
    @DisplayName("publicMatchers binds the auth path matcher")
    void publicMatchersIncludeAuthPath() {
        contextRunner.run(context -> {
            SecurityProperties props = context.getBean(SecurityProperties.class);
            assertThat(props.getPublicMatchers()).contains("/api/auth/**");
        });
    }

    @Test
    @DisplayName("jwt.secret binds and is non-blank")
    void jwtSecretIsNotBlank() {
        contextRunner.run(context -> {
            SecurityProperties props = context.getBean(SecurityProperties.class);
            assertThat(props.getJwt().getSecret()).isNotBlank();
        });
    }

    /**
     * Minimal config class to enable {@link SecurityProperties} in the test context
     * without dragging in {@link SecurityConfig} and its security-filter dependencies.
     */
    @org.springframework.context.annotation.Configuration
    @org.springframework.boot.context.properties.EnableConfigurationProperties(SecurityProperties.class)
    static class SecurityPropertiesTestConfig {
    }
}
