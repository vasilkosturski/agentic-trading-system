package com.trading.config;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.trading.repository.TradingAgentRepository;
import com.trading.security.JwtAuthenticationFilter;
import com.trading.security.JwtTokenProvider;
import com.trading.service.AccountProvisioner;
import com.trading.service.AccountQueryService;
import com.trading.service.AgentIdentityService;
import com.trading.service.MarketService;
import com.trading.service.MemoryService;
import com.trading.service.PortfolioService;
import com.trading.service.PriceCacheService;
import com.trading.service.PromptLoader;
import com.trading.service.ScheduledSnapshotService;
import com.trading.service.TradingRunService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.FilterType;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.test.web.servlet.MockMvc;

/**
 * CORS preflight integration test for the consolidated {@link CorsConfig}.
 *
 * <p>Verifies that the authenticated-by-default security filter chain cooperates
 * with the single {@link org.springframework.web.cors.CorsConfigurationSource}
 * bean to:
 * <ul>
 *   <li>Authorize OPTIONS preflights from origins listed in
 *       {@link SecurityProperties#getAllowedOrigins()} — returns 200 and echoes
 *       the {@code Access-Control-Allow-Origin} header.</li>
 *   <li>Reject OPTIONS preflights from disallowed origins — returns 403 with no
 *       {@code Access-Control-Allow-Origin} header.</li>
 * </ul>
 *
 * <p>The wiring under test: {@code .cors(Customizer.withDefaults())} in
 * {@link SecurityConfig#securityFilterChain} causes Spring Security to install a
 * {@code CorsFilter} ahead of the JWT filter, sourced from the
 * {@code corsConfigurationSource} bean. Preflights are then short-circuited
 * inside the security chain — before the authenticated-by-default authorization
 * rule would otherwise reject the anonymous OPTIONS request.
 *
 * <p>Note: Spring Security 6.x's {@code HttpSecurityConfiguration.applyCorsIfAvailable}
 * already auto-wires CORS when a {@code CorsConfigurationSource} bean is present,
 * so these tests would also pass without the explicit {@code .cors(...)} call on
 * this Spring version. The explicit call is kept because it (a) documents intent
 * at the call site, (b) is the configuration pattern recommended by the Spring
 * Security reference, and (c) does not rely on the auto-apply convention being
 * preserved in future versions.
 *
 * <p>Same DB-free SQLite stand-in pattern as {@link SecurityChainIntegrationTest}
 * (see its class-level JavaDoc for the diagnosis around why
 * {@link JwtAuthenticationFilter} must NOT be {@code @MockBean}'d and why the
 * SQLite {@code DataSource} is harmless when no test touches a repository).
 */
@SpringBootTest(
        webEnvironment = WebEnvironment.MOCK,
        classes = CorsIntegrationTest.DbFreeContext.class,
        properties = {
            // Match SecurityChainIntegrationTest — in-memory SQLite stands in for
            // PostgreSQL so JPA can wire its repositories at refresh without needing
            // Testcontainers or a real DB. No CORS preflight touches the DB layer.
            "spring.datasource.url=jdbc:sqlite::memory:",
            "spring.datasource.driver-class-name=org.sqlite.JDBC",
            "spring.datasource.username=",
            "spring.datasource.password=",
            "spring.jpa.database-platform=org.hibernate.community.dialect.SQLiteDialect",
            "spring.jpa.hibernate.ddl-auto=none",
            "spring.jpa.properties.hibernate.hbm2ddl.create_namespaces=false",
            "spring.jpa.properties.hibernate.boot.allow_jdbc_metadata_access=false"
        })
@AutoConfigureMockMvc
@DisplayName("CORS Integration Tests")
class CorsIntegrationTest {

    /**
     * Same exclusion shape as {@link SecurityChainIntegrationTest.DbFreeContext}:
     * {@link ScheduledSnapshotService} is dropped because its {@code @Scheduled}
     * methods are noise here, and {@code TestSecurityConfig} is dropped because
     * its {@code @MockBean}s would clash with the ones declared below.
     */
    @Configuration
    @ComponentScan(
            basePackages = "com.trading",
            excludeFilters = {
                @ComponentScan.Filter(
                        type = FilterType.REGEX,
                        pattern = {
                            "com\\.trading\\.service\\.ScheduledSnapshotService",
                            "com\\.trading\\.config\\.TestSecurityConfig"
                        })
            })
    @org.springframework.boot.autoconfigure.EnableAutoConfiguration
    static class DbFreeContext {}

    @Autowired
    private MockMvc mockMvc;

    // ----- Security collaborators (same rationale as SecurityChainIntegrationTest) -----

    @MockBean
    private AuthenticationManager authenticationManager;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    // ----- Service-layer collaborators (all DB-touching) -----

    @MockBean
    private AccountQueryService accountQueryService;

    @MockBean
    private AccountProvisioner accountProvisioner;

    @MockBean
    private AgentIdentityService agentIdentityService;

    @MockBean
    private MemoryService memoryService;

    @MockBean
    private TradingRunService tradingRunService;

    @MockBean
    private PortfolioService portfolioService;

    @MockBean
    private MarketService marketService;

    @MockBean
    private PriceCacheService priceCacheService;

    @MockBean
    private PromptLoader promptLoader;

    @MockBean
    private TradingAgentRepository tradingAgentRepository;

    @Test
    @DisplayName("Preflight from allowed origin returns 200 and echoes Access-Control-Allow-Origin")
    void preflightFromAllowedOrigin_Returns200() throws Exception {
        mockMvc.perform(options("/api/accounts/1/trades")
                        .header("Origin", "http://localhost:3000")
                        .header("Access-Control-Request-Method", "POST")
                        .header("Access-Control-Request-Headers", "content-type"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "http://localhost:3000"))
                .andExpect(header().string("Access-Control-Allow-Credentials", "true"));
    }

    @Test
    @DisplayName("Preflight from disallowed origin returns 403 with no Access-Control-Allow-Origin header")
    void preflightFromDisallowedOrigin_Returns403() throws Exception {
        mockMvc.perform(options("/api/accounts/1/trades")
                        .header("Origin", "http://evil.example.com")
                        .header("Access-Control-Request-Method", "POST"))
                .andExpect(status().isForbidden())
                .andExpect(header().doesNotExist("Access-Control-Allow-Origin"));
    }
}
