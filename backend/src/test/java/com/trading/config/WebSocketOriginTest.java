package com.trading.config;

import com.trading.repository.TradingAgentRepository;
import com.trading.security.JwtAuthenticationFilter;
import com.trading.security.JwtTokenProvider;
import com.trading.service.AccountService;
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

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * SockJS origin enforcement integration test for {@link WebSocketConfig}.
 *
 * <p>Pins down the HTTP-boundary contract for the SockJS info endpoint at
 * {@code /api/ws/info}: allowed origins receive the JSON handshake metadata;
 * disallowed origins receive 403 with no info body. SockJS clients begin every
 * handshake with a GET to {@code <endpoint>/info?t=<timestamp>}, so this is the
 * cheap surface for asserting that broadcast trade events cannot leak to
 * arbitrary cross-origin pages.
 *
 * <p><strong>Layered defense.</strong> Two independent barriers cooperate to
 * enforce the contract:
 * <ol>
 *   <li>The global {@code CorsFilter} sourced from {@link CorsConfig} —
 *       registered for {@code /api/**}, which includes {@code /api/ws/**} —
 *       rejects disallowed origins inside the security chain with a 403 "Invalid
 *       CORS request" body.</li>
 *   <li>The SockJS handshake handler's own {@code setAllowedOriginPatterns}
 *       check (wired in {@link WebSocketConfig#registerStompEndpoints} from
 *       {@link SecurityProperties#getAllowedOrigins()}) is the defense-in-depth
 *       backstop for any code path that might bypass the CORS filter (e.g., a
 *       future relaxation of the {@code /api/**} registration, or non-browser
 *       SockJS clients that omit the {@code Origin} header check at the HTTP
 *       layer).</li>
 * </ol>
 * In this test the CORS filter is the visible barrier — both assertions hold
 * regardless of the SockJS pattern — but the SockJS layer is what keeps
 * trade-event broadcasts off arbitrary cross-origin pages when the CORS filter
 * is bypassed, and the test serves as the regression guard at the boundary
 * either layer would have to break for trade data to leak.
 *
 * <p>Requests are authenticated via {@code .with(user(...))} because the
 * security chain is authenticated-by-default and {@code /api/ws/**} is not in
 * {@link SecurityProperties#getPublicMatchers()}. Without that, anonymous calls
 * are short-circuited with 401 ahead of either origin barrier and neither layer
 * actually runs.
 *
 * <p>Reuses the DB-free SQLite stand-in pattern from
 * {@link SecurityChainIntegrationTest} and {@link CorsIntegrationTest} so the
 * full application context boots without Testcontainers or PostgreSQL. No test
 * here touches a repository method, so the SQL dialect mismatch is irrelevant.
 */
@SpringBootTest(
    webEnvironment = WebEnvironment.MOCK,
    classes = WebSocketOriginTest.DbFreeContext.class,
    properties = {
        "spring.datasource.url=jdbc:sqlite::memory:",
        "spring.datasource.driver-class-name=org.sqlite.JDBC",
        "spring.datasource.username=",
        "spring.datasource.password=",
        "spring.jpa.database-platform=org.hibernate.community.dialect.SQLiteDialect",
        "spring.jpa.hibernate.ddl-auto=none",
        "spring.jpa.properties.hibernate.hbm2ddl.create_namespaces=false",
        "spring.jpa.properties.hibernate.boot.allow_jdbc_metadata_access=false"
    }
)
@AutoConfigureMockMvc
@DisplayName("WebSocket Origin Restriction Tests")
class WebSocketOriginTest {

    /**
     * Same exclusion shape as {@link CorsIntegrationTest.DbFreeContext}:
     * {@link ScheduledSnapshotService} is dropped because its {@code @Scheduled}
     * methods are noise, and {@code TestSecurityConfig} is dropped because its
     * {@code @MockBean}s would clash with those declared below.
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
                }
            )
        }
    )
    @org.springframework.boot.autoconfigure.EnableAutoConfiguration
    static class DbFreeContext {
    }

    @Autowired
    private MockMvc mockMvc;

    // ----- Security collaborators (real JwtAuthenticationFilter; see SecurityChainIntegrationTest JavaDoc) -----

    @MockBean
    private AuthenticationManager authenticationManager;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    // ----- Service-layer collaborators (all DB-touching) -----

    @MockBean
    private AccountService accountService;

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
    @DisplayName("SockJS info request from allowed origin returns 200 with JSON body")
    void sockJsInfo_FromAllowedOrigin_Returns200() throws Exception {
        mockMvc.perform(get("/api/ws/info")
                .with(user("admin").roles("ADMIN"))
                .header("Origin", "http://localhost:3000"))
            .andExpect(status().isOk())
            .andExpect(content().contentTypeCompatibleWith("application/json"));
    }

    @Test
    @DisplayName("SockJS info request from disallowed origin returns 403")
    void sockJsInfo_FromDisallowedOrigin_Returns403() throws Exception {
        mockMvc.perform(get("/api/ws/info")
                .with(user("admin").roles("ADMIN"))
                .header("Origin", "http://evil.example.com"))
            .andExpect(status().isForbidden());
    }
}
