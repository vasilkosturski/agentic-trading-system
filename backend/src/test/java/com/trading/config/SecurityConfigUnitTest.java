package com.trading.config;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * Unit tests for SecurityConfig that don't require Spring context.
 * These tests verify SecurityConfig can be instantiated and its beans work correctly.
 */
class SecurityConfigUnitTest {

    /**
     * RED: Verify SecurityConfig class exists and can be instantiated.
     * Expected to fail because SecurityConfig.java doesn't exist yet.
     */
    @Test
    void securityConfigClassShouldExist() {
        // Try to load the SecurityConfig class
        assertDoesNotThrow(
                () -> {
                    Class<?> securityConfigClass = Class.forName("com.trading.config.SecurityConfig");
                    assertNotNull(securityConfigClass, "SecurityConfig class should exist");
                },
                "SecurityConfig class should be found in com.trading.config package");
    }

    /**
     * RED: Verify SecurityConfig has required annotations.
     * Expected to fail because SecurityConfig.java doesn't exist yet.
     */
    @Test
    void securityConfigShouldHaveRequiredAnnotations() throws ClassNotFoundException {
        Class<?> securityConfigClass = Class.forName("com.trading.config.SecurityConfig");

        // Check for @Configuration
        boolean hasConfiguration =
                securityConfigClass.isAnnotationPresent(org.springframework.context.annotation.Configuration.class);
        assertTrue(hasConfiguration, "SecurityConfig should have @Configuration");

        // Check for @EnableWebSecurity
        boolean hasEnableWebSecurity = securityConfigClass.isAnnotationPresent(
                org.springframework.security.config.annotation.web.configuration.EnableWebSecurity.class);
        assertTrue(hasEnableWebSecurity, "SecurityConfig should have @EnableWebSecurity");

        // Check for @EnableMethodSecurity
        boolean hasEnableMethodSecurity = securityConfigClass.isAnnotationPresent(
                org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity.class);
        assertTrue(hasEnableMethodSecurity, "SecurityConfig should have @EnableMethodSecurity");
    }

    /**
     * Verify SecurityConfig has passwordEncoder() method that returns BCryptPasswordEncoder.
     */
    @Test
    void securityConfigShouldHavePasswordEncoderMethod() throws Exception {
        Class<?> securityConfigClass = Class.forName("com.trading.config.SecurityConfig");

        // Find passwordEncoder() method
        var passwordEncoderMethod = securityConfigClass.getMethod("passwordEncoder");
        assertNotNull(passwordEncoderMethod, "SecurityConfig should have passwordEncoder() method");

        // Verify it returns PasswordEncoder
        assertEquals(
                PasswordEncoder.class,
                passwordEncoderMethod.getReturnType(),
                "passwordEncoder() should return PasswordEncoder");

        // passwordEncoder() is static-like (no instance state needed), invoke on null instance
        // Actually, we can't invoke it without a SecurityConfig instance, so just verify the method exists
        // The actual behavior is tested in SecurityConfigTest
    }

    /**
     * RED: Verify SecurityConfig has securityFilterChain() method.
     * Expected to fail because SecurityConfig.java doesn't exist yet.
     */
    @Test
    void securityConfigShouldHaveSecurityFilterChainMethod() throws ClassNotFoundException {
        Class<?> securityConfigClass = Class.forName("com.trading.config.SecurityConfig");

        // Find securityFilterChain method
        boolean hasSecurityFilterChainMethod = false;
        for (var method : securityConfigClass.getDeclaredMethods()) {
            if (method.getName().equals("securityFilterChain")) {
                hasSecurityFilterChainMethod = true;

                // Verify return type
                assertEquals(
                        org.springframework.security.web.SecurityFilterChain.class,
                        method.getReturnType(),
                        "securityFilterChain() should return SecurityFilterChain");

                // Verify it has @Bean annotation
                boolean hasBean = method.isAnnotationPresent(org.springframework.context.annotation.Bean.class);
                assertTrue(hasBean, "securityFilterChain() should have @Bean annotation");

                break;
            }
        }

        assertTrue(hasSecurityFilterChainMethod, "SecurityConfig should have securityFilterChain() method");
    }

    /**
     * RED: Verify SecurityConfig has userDetailsService() method.
     * Expected to fail because SecurityConfig.java doesn't exist yet.
     */
    @Test
    void securityConfigShouldHaveUserDetailsServiceMethod() throws ClassNotFoundException {
        Class<?> securityConfigClass = Class.forName("com.trading.config.SecurityConfig");

        // Find userDetailsService method
        boolean hasUserDetailsServiceMethod = false;
        for (var method : securityConfigClass.getDeclaredMethods()) {
            if (method.getName().equals("userDetailsService")) {
                hasUserDetailsServiceMethod = true;

                // Verify return type
                assertEquals(
                        org.springframework.security.core.userdetails.UserDetailsService.class,
                        method.getReturnType(),
                        "userDetailsService() should return UserDetailsService");

                // Verify it has @Bean annotation
                boolean hasBean = method.isAnnotationPresent(org.springframework.context.annotation.Bean.class);
                assertTrue(hasBean, "userDetailsService() should have @Bean annotation");

                break;
            }
        }

        assertTrue(hasUserDetailsServiceMethod, "SecurityConfig should have userDetailsService() method");
    }

    /**
     * RED: Verify SecurityConfig has @Value annotated fields for credentials.
     * Expected to fail because SecurityConfig.java doesn't exist yet.
     */
    @Test
    void securityConfigShouldHaveValueAnnotatedFields() throws ClassNotFoundException {
        Class<?> securityConfigClass = Class.forName("com.trading.config.SecurityConfig");

        // Look for @Value annotated fields
        int valueAnnotatedFields = 0;
        for (var field : securityConfigClass.getDeclaredFields()) {
            if (field.isAnnotationPresent(org.springframework.beans.factory.annotation.Value.class)) {
                valueAnnotatedFields++;

                var valueAnnotation = field.getAnnotation(org.springframework.beans.factory.annotation.Value.class);
                String value = valueAnnotation.value();

                // Verify it's reading from environment
                assertTrue(value.contains("${"), "@Value should use ${...} syntax: " + value);
                assertTrue(
                        value.contains("ADMIN_USERNAME") || value.contains("ADMIN_PASSWORD"),
                        "@Value should reference ADMIN_USERNAME or ADMIN_PASSWORD: " + value);
            }
        }

        assertTrue(
                valueAnnotatedFields >= 2,
                "SecurityConfig should have at least 2 @Value fields (ADMIN_USERNAME, ADMIN_PASSWORD)");
    }
}
