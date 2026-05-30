package com.trading.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.trading.dto.request.LoginRequest;
import com.trading.dto.response.RunListResponseDto;
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
import org.springframework.http.MediaType;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Collections;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Full-context security filter chain integration test.
 *
 * <p>This is the <strong>first</strong> {@code @SpringBootTest} security test in this
 * codebase. Existing security tests ({@link com.trading.controller.AuthControllerTest},
 * {@link com.trading.controller.TradingRunControllerAdminSecurityTest}) are
 * {@code @WebMvcTest} slice tests scoped to a single controller. This test instead
 * boots the full application context with the real {@link SecurityConfig} and the
 * real {@link JwtAuthenticationFilter}, so the security filter chain itself is the
 * unit under test across multiple controllers.
 *
 * <p><strong>Critical gotcha — DO NOT {@code @MockBean} {@link JwtAuthenticationFilter}.</strong>
 * A Mockito mock of a Servlet {@code Filter} returns {@code void} from
 * {@code doFilter(...)} without invoking {@code chain.doFilter()}, which silently
 * short-circuits the chain and produces phantom 200 responses with
 * {@code Handler=null}. See the JavaDoc on
 * {@code TradingRunControllerAdminSecurityTest:42-50} for the full diagnosis. We
 * mock {@link JwtTokenProvider} instead; the real {@code JwtAuthenticationFilter}
 * from {@code @Component} scanning runs as part of the chain.
 *
 * <p><strong>DB-free boot without Testcontainers.</strong> The context is pointed at
 * an in-memory SQLite {@code DataSource} via test properties so JPA can wire its
 * repository proxies at refresh without needing PostgreSQL, Testcontainers, or Docker.
 * No test exercises a repository method, so the SQL dialect mismatch with the real
 * PostgreSQL schema is harmless. Spring Boot's main {@code DatabaseConfig} and
 * {@code @EnableJpaRepositories} stay in play; the SQLite DataSource cheaply satisfies
 * the JPA infrastructure's demand for an {@code EntityManagerFactory}.
 * {@link DbFreeContext} excludes only {@code ScheduledSnapshotService} (whose
 * {@code @Scheduled} machinery is noisy here) and the test-only
 * {@code TestSecurityConfig} (which would re-{@code MockBean} {@code JwtTokenProvider}
 * and clash with ours). All controller-facing services are provided as
 * {@code @MockBean}s so controllers are reachable by the dispatcher and the filter
 * chain (not a {@code NullPointerException}) decides the status code.
 *
 * <p><strong>What this test pins down.</strong> Two assertions cover the login
 * endpoint's success and failure paths. One assertion documents the public-by-default
 * design intent: an anonymous {@code GET /api/runs} must return 200 (the public web
 * UI fetches this without a login; the legal-protection guard is the 7-day filter
 * baked into the service call, not the security chain). One assertion covers the
 * single remaining filter-chain admin gate: anonymous {@code GET /actuator/env}
 * must return 401 because {@code /actuator/**} (less the public {@code health}/
 * {@code info} matchers) is restricted to {@code ROLE_ADMIN}. The other admin gate
 * in the system — {@code @PreAuthorize("hasRole('ADMIN')")} on
 * {@code TradingRunController#listAllRuns} — is exercised by
 * {@link com.trading.controller.TradingRunControllerAdminSecurityTest}.
 *
 * @see SecurityConfig
 * @see JwtAuthenticationFilter
 */
@SpringBootTest(
    webEnvironment = WebEnvironment.MOCK,
    classes = SecurityChainIntegrationTest.DbFreeContext.class,
    properties = {
        // In-memory SQLite stands in for PostgreSQL so the JPA repositories can be
        // proxied at context refresh without needing Testcontainers / a real DB.
        // No test exercises a repository method, so the actual SQL never runs and
        // the SQLDialect mismatch with the real schema is irrelevant.
        "spring.datasource.url=jdbc:sqlite::memory:",
        "spring.datasource.driver-class-name=org.sqlite.JDBC",
        "spring.datasource.username=",
        "spring.datasource.password=",
        "spring.jpa.database-platform=org.hibernate.community.dialect.SQLiteDialect",
        "spring.jpa.hibernate.ddl-auto=none",
        "spring.jpa.properties.hibernate.hbm2ddl.create_namespaces=false",
        // Disable JPA metadata processing of entities since we never query — keeps
        // boot fast and avoids dialect quirks with our PostgreSQL-specific schema.
        "spring.jpa.properties.hibernate.boot.allow_jdbc_metadata_access=false"
    }
)
@AutoConfigureMockMvc
@DisplayName("SecurityChain Integration Tests")
class SecurityChainIntegrationTest {

    /**
     * Application context for this test: scans the whole {@code com.trading} package
     * as the real app does, but excludes {@code ScheduledSnapshotService} (whose
     * {@code @Scheduled} methods would activate during refresh) and the test-only
     * {@code TestSecurityConfig} (which already {@code @MockBean}s
     * {@code JwtTokenProvider} and would conflict with our own mock). Spring Boot's
     * default auto-configurations are left active so the real {@code SecurityConfig},
     * {@code JwtAuthenticationFilter}, and MVC dispatcher all wire normally. The
     * {@code DataSource} is overridden to in-memory SQLite via the enclosing
     * {@code @SpringBootTest(properties = ...)} so the JPA infrastructure can boot
     * without PostgreSQL.
     */
    @Configuration
    @ComponentScan(
        basePackages = "com.trading",
        excludeFilters = {
            @ComponentScan.Filter(
                type = FilterType.REGEX,
                pattern = {
                    // ScheduledSnapshotService has @Scheduled methods and reaches
                    // through services we do not exercise here. Excluding keeps
                    // the @EnableScheduling refresh phase quiet.
                    "com\\.trading\\.service\\.ScheduledSnapshotService",
                    // Test-only @TestConfiguration that lives in the same package
                    // and ALSO @MockBeans JwtTokenProvider — would clash with our
                    // own @MockBean on the same type.
                    "com\\.trading\\.config\\.TestSecurityConfig"
                }
            )
        }
    )
    @org.springframework.boot.autoconfigure.EnableAutoConfiguration
    static class DbFreeContext {
    }

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    // ----- Security collaborators -----

    /**
     * Mocked so login can return a stub JWT and {@code BadCredentialsException} can be
     * raised. The real {@code AuthenticationManager} bean would need the in-memory
     * {@code UserDetailsService} and {@code BCryptPasswordEncoder} to round-trip
     * credentials; mocking it isolates this test from password-hashing details.
     */
    @MockBean
    private AuthenticationManager authenticationManager;

    /**
     * Mocked because the real {@link JwtAuthenticationFilter} (still wired by
     * {@code @Component} scanning) calls into it on every request. With no
     * {@code Authorization} header on these test requests the filter never invokes
     * the provider, but mocking it removes the need for a real JWT secret to be
     * resolvable at bean-creation time and makes the success path of the login
     * assertion return a deterministic stub token.
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

    /**
     * {@link com.trading.controller.AgentController} injects this repository directly
     * (no service in between), so it must be mocked even though every other DB-facing
     * collaborator is a service.
     */
    @MockBean
    private TradingAgentRepository tradingAgentRepository;

    // =====================================================================
    // Login endpoint — public matcher (success + failure paths).
    // =====================================================================

    @Test
    @DisplayName("POST /api/auth/login with valid credentials returns 200 (login endpoint stays open across R3)")
    void login_WithValidCredentials_Returns200() throws Exception {
        LoginRequest loginRequest = new LoginRequest();
        loginRequest.setUsername("admin");
        loginRequest.setPassword("changeme");

        UserDetails adminUser = User.builder()
            .username("admin")
            .password("password")
            .authorities(Collections.singletonList(new SimpleGrantedAuthority("ROLE_ADMIN")))
            .build();
        Authentication authentication = new UsernamePasswordAuthenticationToken(
            adminUser, null, adminUser.getAuthorities()
        );

        when(authenticationManager.authenticate(any(UsernamePasswordAuthenticationToken.class)))
            .thenReturn(authentication);
        when(jwtTokenProvider.generateToken(any(UserDetails.class)))
            .thenReturn("stub.jwt.token");

        mockMvc.perform(post("/api/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(loginRequest)))
            .andExpect(status().isOk());
    }

    @Test
    @DisplayName("POST /api/auth/login with invalid credentials returns 401")
    void login_WithInvalidCredentials_Returns401() throws Exception {
        LoginRequest loginRequest = new LoginRequest();
        loginRequest.setUsername("admin");
        loginRequest.setPassword("wrongpassword");

        when(authenticationManager.authenticate(any(UsernamePasswordAuthenticationToken.class)))
            .thenThrow(new BadCredentialsException("Invalid credentials"));

        mockMvc.perform(post("/api/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(loginRequest)))
            .andExpect(status().isUnauthorized());
    }

    // =====================================================================
    // Public-by-default — anonymous browser visitors must reach the public
    // read endpoints without authentication. The 7-day display delay enforced
    // by TradingRunService is the legal-protection guard, NOT the security
    // chain. The single admin path (/api/runs/admin) is gated by
    // @PreAuthorize("hasRole('ADMIN')") at the method level and is covered
    // by TradingRunControllerAdminSecurityTest.
    // =====================================================================

    @Test
    @DisplayName("Unauthenticated GET /api/runs returns 200 (public-by-default contract)")
    void unauthenticatedListRuns_Returns200() throws Exception {
        RunListResponseDto emptyResponse = new RunListResponseDto(
            Collections.emptyList(), 0L, 0, 20
        );
        when(tradingRunService.listRuns(any(), any(), any())).thenReturn(emptyResponse);

        mockMvc.perform(get("/api/runs"))
            .andExpect(status().isOk());
    }

    // =====================================================================
    // /actuator/** is admin-gated (defense in depth alongside the production
    // exposure list that hides everything but health/info). /actuator/health
    // and /actuator/info are in publicMatchers and win first-match against
    // the /actuator/** admin matcher; /actuator/env falls through to the
    // admin gate and returns 401 for anonymous callers.
    // =====================================================================

    @Test
    @DisplayName("Unauthenticated GET /actuator/env returns 401")
    void unauthenticatedGetActuatorEnv_Returns401() throws Exception {
        mockMvc.perform(get("/actuator/env"))
            .andExpect(status().isUnauthorized());
    }
}
