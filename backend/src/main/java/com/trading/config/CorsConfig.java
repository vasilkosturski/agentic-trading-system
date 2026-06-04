package com.trading.config;

import java.util.Arrays;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

/**
 * CORS configuration.
 *
 * <p>Exposes a single {@link CorsConfigurationSource} bean that is wired into the
 * security filter chain via {@code .cors(Customizer.withDefaults())} in
 * {@link SecurityConfig#securityFilterChain}. Spring Security auto-detects the
 * bean by its conventional name ({@code corsConfigurationSource}) and installs
 * a {@code CorsFilter} ahead of the JWT filter, so preflight {@code OPTIONS}
 * requests from allowed origins are short-circuited inside the security chain
 * before the authenticated-by-default authorization rule sees them.
 *
 * <p>Origins are sourced from {@link SecurityProperties#getAllowedOrigins()} —
 * the typed {@link org.springframework.boot.context.properties.ConfigurationProperties}
 * binding — rather than a stringly-typed {@code @Value} field, so the list is
 * parsed once at startup with validation rather than re-split on each access.
 */
@Configuration
public class CorsConfig {

    private final SecurityProperties securityProperties;

    public CorsConfig(SecurityProperties securityProperties) {
        this.securityProperties = securityProperties;
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOriginPatterns(securityProperties.getAllowedOrigins());
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(Arrays.asList("*"));
        configuration.setAllowCredentials(true);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", configuration);
        return source;
    }
}
