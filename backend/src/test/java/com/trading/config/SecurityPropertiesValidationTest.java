package com.trading.config;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.boot.autoconfigure.context.ConfigurationPropertiesAutoConfiguration;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.NestedExceptionUtils;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Validation tests for {@link SecurityProperties}.
 *
 * <p>Asserts that blank values for the two security-critical properties
 * ({@code security.jwt.secret} and {@code security.admin.password}) cause
 * context-load failure with the property name surfacing in the exception chain.
 *
 * <p>Uses {@link ApplicationContextRunner} so each test controls its own property
 * values inline — bypassing {@code application.yml} entirely. This isolates the
 * {@code @NotBlank} contract on {@link SecurityProperties} from any YAML defaults.
 */
@DisplayName("SecurityProperties validation tests")
class SecurityPropertiesValidationTest {

    private final ApplicationContextRunner contextRunner = new ApplicationContextRunner()
        .withConfiguration(AutoConfigurations.of(ConfigurationPropertiesAutoConfiguration.class))
        .withUserConfiguration(TestConfig.class);

    @Test
    @DisplayName("Empty security.jwt.secret fails context startup with property name in exception")
    void emptyJwtSecret_FailsContextStartup() {
        contextRunner
            .withPropertyValues(
                "security.allowed-origins=http://localhost:3000",
                "security.public-matchers[0]=/api/auth/**",
                "security.jwt.secret=",
                "security.jwt.expiration=3600000",
                "security.admin.username=admin",
                "security.admin.password=test-only-admin-password"
            )
            .run(context -> {
                assertThat(context).hasFailed();
                Throwable rootCause = NestedExceptionUtils.getRootCause(context.getStartupFailure());
                assertThat(rootCause).isNotNull();
                assertThat(rootCause.getMessage()).contains("secret");
            });
    }

    @Test
    @DisplayName("Empty security.admin.password fails context startup with property name in exception")
    void emptyAdminPassword_FailsContextStartup() {
        contextRunner
            .withPropertyValues(
                "security.allowed-origins=http://localhost:3000",
                "security.public-matchers[0]=/api/auth/**",
                "security.jwt.secret=test-only-jwt-secret-must-be-at-least-256-bits-long-for-hmac-sha256-algorithm",
                "security.jwt.expiration=3600000",
                "security.admin.username=admin",
                "security.admin.password="
            )
            .run(context -> {
                assertThat(context).hasFailed();
                Throwable rootCause = NestedExceptionUtils.getRootCause(context.getStartupFailure());
                assertThat(rootCause).isNotNull();
                assertThat(rootCause.getMessage()).contains("password");
            });
    }

    @EnableConfigurationProperties(SecurityProperties.class)
    @Configuration
    static class TestConfig {
    }
}
