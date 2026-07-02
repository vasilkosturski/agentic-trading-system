package com.trading.config;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
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
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Full-context security test for the Spring Boot Actuator gating contract.
 *
 * <p>Pins down the four corners of the Actuator security model after R8:
 * <ul>
 *   <li>Unauthenticated {@code /actuator/health} → 200 with no component details
 *       (because {@code management.endpoint.health.show-details: when-authorized}).</li>
 *   <li>Unauthenticated {@code /actuator/env} → 401 (matches the new
 *       {@code /actuator/**} admin gate; lacking authentication ≠ having ADMIN role,
 *       and the {@code HttpStatusEntryPoint(UNAUTHORIZED)} returns 401 not 403).</li>
 *   <li>Admin-authenticated {@code /actuator/env} → 200 (admin role satisfies the gate).</li>
 *   <li>Admin-authenticated {@code /actuator/health} → 200 with component details
 *       (the {@code when-authorized} flag reveals them to authenticated principals).</li>
 * </ul>
 *
 * <p>Reuses the DB-free {@code @SpringBootTest} fixture pattern documented on
 * {@link SecurityChainIntegrationTest}: in-memory SQLite stand-in for PostgreSQL so the
 * JPA infrastructure can wire without Testcontainers, and {@code @MockBean}s for every
 * DB-touching service so controllers are reachable by the dispatcher and the filter chain
 * (not an NPE) decides the status code.
 *
 * <p>Test exposure: the matching {@code src/test/resources/application.yml} overrides
 * {@code management.endpoints.web.exposure.include: "*"} so {@code /actuator/env} is
 * reachable in tests. Production exposes only {@code health,info} — defense in depth #1
 * is the exposure list, defense in depth #2 is the security gate. This test verifies
 * the gate, which only matters if the endpoints are reachable.
 */
@SpringBootTest(
        webEnvironment = WebEnvironment.MOCK,
        classes = ActuatorSecurityTest.DbFreeContext.class,
        properties = {
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
@DisplayName("Actuator Security Tests")
class ActuatorSecurityTest {

    /**
     * Application context mirroring {@link SecurityChainIntegrationTest.DbFreeContext}:
     * full {@code com.trading} component scan minus the noisy {@code ScheduledSnapshotService}
     * and the test-only {@code TestSecurityConfig} (which double-mocks
     * {@code JwtTokenProvider} and would clash with our own mock).
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

    // ----- Security collaborators -----

    @MockBean
    private AuthenticationManager authenticationManager;

    /**
     * Mocked because the real {@link JwtAuthenticationFilter} (wired by
     * {@code @Component} scanning) calls into the provider. Unauth requests never invoke
     * it; admin requests use {@code @WithMockUser} which bypasses JWT entirely.
     */
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

    // =====================================================================
    // /actuator/health — public matcher (already permitAll from R1).
    // show-details: when-authorized governs body content.
    // =====================================================================

    @Test
    @DisplayName("Unauth GET /actuator/health returns 200 without component details")
    void unauthGetActuatorHealth_Returns200WithoutDetails() throws Exception {
        mockMvc.perform(get("/actuator/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.components").doesNotExist())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("Admin GET /actuator/health returns 200 with component details")
    void adminGetActuatorHealth_Returns200WithDetails() throws Exception {
        mockMvc.perform(get("/actuator/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.components").exists());
    }

    // =====================================================================
    // /actuator/env — non-public; gated by the new /actuator/** admin matcher.
    // =====================================================================

    @Test
    @DisplayName("Unauth GET /actuator/env returns 401")
    void unauthGetActuatorEnv_Returns401() throws Exception {
        mockMvc.perform(get("/actuator/env")).andExpect(status().isUnauthorized());
    }

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("Admin GET /actuator/env returns 200")
    void adminGetActuatorEnv_Returns200() throws Exception {
        mockMvc.perform(get("/actuator/env")).andExpect(status().isOk());
    }
}
