package com.trading.config;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

/**
 * Type-safe configuration properties for the security cluster.
 *
 * Binds properties from application.yml with prefix "security" to this class.
 * Provides validation, IDE autocomplete, and centralized configuration for CORS,
 * public matchers, JWT, and the admin account.
 *
 * All default values are defined in application.yml, not here.
 * This keeps configuration in one place where it's visible and easy to change.
 *
 * Configuration in application.yml:
 * <pre>
 * security:
 *   allowed-origins: ${CORS_ALLOWED_ORIGINS:http://localhost:3000,http://localhost:5173,https://agentic-trading.vkontech.com}
 *   public-matchers:
 *     - /api/auth/**
 *     - /actuator/health
 *     - /actuator/info
 *   jwt:
 *     secret: ${JWT_SECRET}
 *     expiration: ${JWT_EXPIRATION:3600000}
 *   admin:
 *     username: ${ADMIN_USERNAME:admin}
 *     password: ${ADMIN_PASSWORD:}
 * </pre>
 */
@ConfigurationProperties(prefix = "security")
@Validated
public class SecurityProperties {

    /**
     * CORS allowed origins. Default defined in application.yml.
     */
    private List<String> allowedOrigins;

    /**
     * Request path matchers that should bypass authentication.
     * Default defined in application.yml.
     */
    private List<String> publicMatchers;

    /**
     * JWT signing and expiration settings.
     */
    @Valid
    private Jwt jwt = new Jwt();

    /**
     * Bootstrap admin account credentials.
     */
    @Valid
    private Admin admin = new Admin();

    // Getters and setters required for @ConfigurationProperties

    public List<String> getAllowedOrigins() {
        return allowedOrigins;
    }

    public void setAllowedOrigins(List<String> allowedOrigins) {
        this.allowedOrigins = allowedOrigins;
    }

    public List<String> getPublicMatchers() {
        return publicMatchers;
    }

    public void setPublicMatchers(List<String> publicMatchers) {
        this.publicMatchers = publicMatchers;
    }

    public Jwt getJwt() {
        return jwt;
    }

    public void setJwt(Jwt jwt) {
        this.jwt = jwt;
    }

    public Admin getAdmin() {
        return admin;
    }

    public void setAdmin(Admin admin) {
        this.admin = admin;
    }

    /**
     * JWT signing and expiration settings.
     */
    public static class Jwt {

        /**
         * JWT signing secret. Must be at least 32 characters (256 bits) for HS256.
         * No default — must be provided via environment variable JWT_SECRET.
         */
        @NotBlank
        private String secret;

        /**
         * JWT token expiration in milliseconds. Default defined in application.yml.
         */
        private long expiration;

        public String getSecret() {
            return secret;
        }

        public void setSecret(String secret) {
            this.secret = secret;
        }

        public long getExpiration() {
            return expiration;
        }

        public void setExpiration(long expiration) {
            this.expiration = expiration;
        }
    }

    /**
     * Bootstrap admin account credentials.
     */
    public static class Admin {

        /**
         * Admin username. Default defined in application.yml.
         */
        @NotBlank
        private String username;

        /**
         * Admin password. No default for security reasons — must be provided
         * via environment variable ADMIN_PASSWORD.
         */
        @NotBlank
        private String password;

        public String getUsername() {
            return username;
        }

        public void setUsername(String username) {
            this.username = username;
        }

        public String getPassword() {
            return password;
        }

        public void setPassword(String password) {
            this.password = password;
        }
    }
}
