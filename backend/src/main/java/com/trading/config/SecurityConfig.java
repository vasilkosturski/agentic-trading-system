package com.trading.config;

import com.trading.security.JwtAuthenticationFilter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Security configuration for the trading system.
 *
 * <p>Implements JWT-based authentication for admin endpoints.
 *
 * <h3>Design Decisions:</h3>
 * <ul>
 *   <li>JWT Authentication - Stateless token-based auth, credentials stored in localStorage</li>
 *   <li>In-memory authentication - Single admin user, no database overhead</li>
 *   <li>CSRF disabled - Stateless REST API, no session cookies to protect</li>
 *   <li>Stateless sessions - No HTTP sessions, JWT tokens carry authentication</li>
 *   <li>Method-level security - Protection via @PreAuthorize on individual endpoints
 *       (the single admin path is {@code GET /api/runs/admin}, gated by
 *       {@code @PreAuthorize("hasRole('ADMIN')")})</li>
 *   <li>Public by default - the app is a public read-only trading-runs viewer; the
 *       7-day display delay enforced inside {@code TradingRunService} is the legal-
 *       protection guard, not the security chain. The only filter-chain admin gate
 *       restricts {@code /actuator/**} (less the {@code health}/{@code info} matchers
 *       declared in {@link SecurityProperties#getPublicMatchers()}) to
 *       {@code ROLE_ADMIN}</li>
 *   <li>JWT filter - Validates Bearer tokens on each request</li>
 * </ul>
 *
 * <h3>Required Configuration:</h3>
 * <ul>
 *   <li><strong>jwt.secret</strong> - REQUIRED. JWT signing secret, minimum 32 characters (256 bits).
 *       Must be set in application.properties or environment variables. No default for security reasons.</li>
 *   <li>jwt.expiration - Optional. Token expiration in milliseconds (default: 3600000 = 1 hour)</li>
 *   <li>ADMIN_USERNAME - Admin username (default: admin)</li>
 *   <li>ADMIN_PASSWORD - Admin password (default: changeme - CHANGE IN PRODUCTION)</li>
 * </ul>
 *
 * @see org.springframework.security.access.prepost.PreAuthorize
 * @see com.trading.security.JwtTokenProvider for JWT secret requirements
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
@EnableConfigurationProperties(SecurityProperties.class)
public class SecurityConfig {

    private final SecurityProperties securityProperties;

    @Value("${ADMIN_USERNAME:admin}")
    private String adminUsername;

    @Value("${ADMIN_PASSWORD:changeme}")
    private String adminPassword;

    public SecurityConfig(SecurityProperties securityProperties) {
        this.securityProperties = securityProperties;
    }

    /**
     * Configures HTTP security with JWT authentication and stateless sessions.
     *
     * <p>Matcher chain (first-match-wins):
     * <ol>
     *   <li>{@link SecurityProperties#getPublicMatchers()} → {@code permitAll}. Covers
     *       {@code /api/auth/**}, {@code /actuator/health}, {@code /actuator/info}.
     *       Listed first so the two public actuator endpoints win against the
     *       {@code /actuator/**} admin gate below.</li>
     *   <li>{@code /actuator/**} → {@code hasRole("ADMIN")}. Restricts the remaining
     *       actuator endpoints ({@code /actuator/env}, {@code /actuator/metrics}, etc.)
     *       to authenticated admins.</li>
     *   <li>Everything else → {@code permitAll}. The public read-only trading-runs UI
     *       reaches the controllers without authentication; the 7-day display delay
     *       is enforced inside {@code TradingRunService}. The single admin-only
     *       endpoint ({@code GET /api/runs/admin}) is gated by method-level
     *       {@code @PreAuthorize("hasRole('ADMIN')")}, not by the filter chain.</li>
     * </ol>
     *
     * <p>Other configuration:
     * <ul>
     *   <li>CORS - wired via {@code .cors(Customizer.withDefaults())} so the
     *       {@link org.springframework.web.cors.CorsConfigurationSource} bean
     *       defined in {@link CorsConfig} is installed ahead of the JWT filter;
     *       browser preflight {@code OPTIONS} from allowed origins is short-circuited
     *       before any matcher runs.</li>
     *   <li>CSRF disabled - REST API is stateless.</li>
     *   <li>Stateless session management - no HTTP sessions, JWT tokens only.</li>
     *   <li>{@link HttpStatusEntryPoint} returning {@code 401} - kept so the
     *       {@code /actuator/**} admin gate returns the idiomatic
     *       {@code 401 Unauthorized} for anonymous callers instead of Spring 6's
     *       default {@code 403 Forbidden}.</li>
     *   <li>JWT filter - validates Bearer tokens before
     *       {@link UsernamePasswordAuthenticationFilter}.</li>
     * </ul>
     *
     * @param http the HttpSecurity to configure
     * @param jwtAuthenticationFilter the JWT authentication filter
     * @return the configured SecurityFilterChain
     * @throws Exception if configuration fails
     */
    @Bean
    public SecurityFilterChain securityFilterChain(
            HttpSecurity http,
            JwtAuthenticationFilter jwtAuthenticationFilter) throws Exception {
        http
            .cors(Customizer.withDefaults())
            .csrf(csrf -> csrf.disable())
            .sessionManagement(session -> session
                .sessionCreationPolicy(SessionCreationPolicy.STATELESS)
            )
            .authorizeHttpRequests(auth -> auth
                .requestMatchers(securityProperties.getPublicMatchers().toArray(new String[0])).permitAll()
                .requestMatchers("/actuator/**").hasRole("ADMIN")
                .anyRequest().permitAll()
            )
            .exceptionHandling(ex -> ex
                .authenticationEntryPoint(new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED))
            )
            .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

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

    /**
     * Provides AuthenticationManager for authenticating users.
     * Required for login endpoint to authenticate credentials.
     *
     * @param authenticationConfiguration Spring's authentication configuration
     * @return AuthenticationManager instance
     * @throws Exception if configuration fails
     */
    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration authenticationConfiguration) throws Exception {
        return authenticationConfiguration.getAuthenticationManager();
    }
}
