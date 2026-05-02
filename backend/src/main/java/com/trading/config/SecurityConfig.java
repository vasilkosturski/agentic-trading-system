package com.trading.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Security configuration for the trading system.
 *
 * <p>Implements HTTP Basic Auth for admin endpoints using in-memory authentication.
 *
 * <h3>Design Decisions:</h3>
 * <ul>
 *   <li>HTTP Basic Auth - Browser-native authentication popup, no custom login pages</li>
 *   <li>In-memory authentication - Single admin user, no database overhead</li>
 *   <li>CSRF disabled - Stateless REST API, no session cookies to protect</li>
 *   <li>Method-level security - Protection via @PreAuthorize on individual endpoints</li>
 *   <li>Default permit all - Public endpoints remain open, admin endpoints require auth</li>
 * </ul>
 *
 * @see org.springframework.security.access.prepost.PreAuthorize
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    @Value("${ADMIN_USERNAME:admin}")
    private String adminUsername;

    @Value("${ADMIN_PASSWORD:changeme}")
    private String adminPassword;

    /**
     * Configures HTTP security with Basic Auth and permissive defaults.
     *
     * <p>Configuration:
     * <ul>
     *   <li>CSRF disabled - REST API is stateless</li>
     *   <li>All requests permitted by default - protection via @PreAuthorize</li>
     *   <li>HTTP Basic Auth enabled - browser native login popup</li>
     * </ul>
     *
     * @param http the HttpSecurity to configure
     * @return the configured SecurityFilterChain
     * @throws Exception if configuration fails
     */
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .authorizeHttpRequests(auth -> auth
                .anyRequest().permitAll()
            )
            .httpBasic(Customizer.withDefaults());

        return http.build();
    }

    /**
     * Provides in-memory user details service with admin user.
     *
     * <p>Creates a single admin user with credentials from environment variables:
     * <ul>
     *   <li>Username from ADMIN_USERNAME (default: admin)</li>
     *   <li>Password from ADMIN_PASSWORD (default: changeme)</li>
     *   <li>Role: ADMIN (grants ROLE_ADMIN authority)</li>
     * </ul>
     *
     * <p>Password is BCrypt-encoded at runtime from plaintext environment variable.
     *
     * @param passwordEncoder the password encoder to use
     * @return UserDetailsService with admin user configured
     */
    @Bean
    public UserDetailsService userDetailsService(PasswordEncoder passwordEncoder) {
        UserDetails admin = User.builder()
            .username(adminUsername)
            .password(passwordEncoder.encode(adminPassword))
            .roles("ADMIN")
            .build();

        return new InMemoryUserDetailsManager(admin);
    }

    /**
     * Provides BCrypt password encoder for secure password hashing.
     *
     * <p>BCrypt is the Spring Security recommended algorithm (2026).
     * Default strength: 10 rounds.
     *
     * @return BCryptPasswordEncoder instance
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
