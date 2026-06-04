package com.trading.config;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * Verifies that Spring Security dependency is correctly added to build.gradle.kts.
 * This test ensures that Spring Security classes are available on the classpath.
 */
class SpringSecurityDependencyTest {

    /**
     * RED phase: This test will fail initially because spring-boot-starter-security
     * is not yet added to build.gradle.kts, so Spring Security classes won't be
     * available on the classpath.
     */
    @Test
    void shouldHaveSpringSecurityOnClasspath() {
        // Attempt to instantiate a core Spring Security class
        // If the dependency is missing, this will fail with NoClassDefFoundError
        PasswordEncoder encoder = new BCryptPasswordEncoder();

        assertNotNull(encoder, "BCryptPasswordEncoder should be instantiable");

        // Verify it works as expected
        String rawPassword = "test123";
        String encodedPassword = encoder.encode(rawPassword);

        assertNotNull(encodedPassword, "Encoded password should not be null");
        assertNotEquals(rawPassword, encodedPassword, "Encoded password should be different from raw");
        assertTrue(encoder.matches(rawPassword, encodedPassword), "Encoder should match raw with encoded");
    }

    @Test
    void shouldHaveSpringSecurityConfigAnnotationsAvailable() {
        // Verify that Spring Security configuration annotations are available
        try {
            Class<?> enableWebSecurityClass =
                    Class.forName("org.springframework.security.config.annotation.web.configuration.EnableWebSecurity");
            Class<?> enableMethodSecurityClass = Class.forName(
                    "org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity");

            assertNotNull(enableWebSecurityClass, "@EnableWebSecurity annotation should be available");
            assertNotNull(enableMethodSecurityClass, "@EnableMethodSecurity annotation should be available");
        } catch (ClassNotFoundException e) {
            fail("Spring Security annotations not found on classpath: " + e.getMessage());
        }
    }

    @Test
    void shouldHaveUserDetailsServiceAvailable() {
        // Verify that UserDetailsService interface is available (needed for in-memory auth)
        try {
            Class<?> userDetailsServiceClass =
                    Class.forName("org.springframework.security.core.userdetails.UserDetailsService");
            Class<?> inMemoryManagerClass =
                    Class.forName("org.springframework.security.provisioning.InMemoryUserDetailsManager");

            assertNotNull(userDetailsServiceClass, "UserDetailsService interface should be available");
            assertNotNull(inMemoryManagerClass, "InMemoryUserDetailsManager class should be available");
        } catch (ClassNotFoundException e) {
            fail("Spring Security UserDetailsService classes not found: " + e.getMessage());
        }
    }
}
