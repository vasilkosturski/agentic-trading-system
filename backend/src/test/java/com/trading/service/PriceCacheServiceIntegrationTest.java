package com.trading.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

import com.trading.entity.PriceCache;
import com.trading.repository.PriceCacheRepository;
import com.trading.testsupport.TestcontainersConfiguration;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.context.annotation.Import;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

/**
 * Integration tests for {@link PriceCacheService} that boot a real Spring context
 * with a real PostgreSQL (Testcontainers) and a real {@link PriceCacheRepository}.
 *
 * Purpose: prove the bug-then-fix invariant that two consecutive {@code getPrice}
 * calls actually persist to {@code analytics.price_cache} and that the second call
 * is served from cache (without re-hitting Finnhub).
 *
 * Before the @Transactional fix on {@code PriceCacheRepository.upsert}, the first
 * call's write silently fails (Spring throws TransactionRequiredException which
 * the service's overly-broad catch absorbs at DEBUG level), so the second call
 * misses the cache and re-fetches Finnhub. This test catches that regression.
 */
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Import(TestcontainersConfiguration.class)
@DisplayName("PriceCacheService Integration Tests")
class PriceCacheServiceIntegrationTest {

    private static final int TTL_MINUTES = 60;
    private static final String FINNHUB_BASE_URL = "https://finnhub.io/api/v1";
    private static final String FINNHUB_API_KEY = "test-key";

    @Autowired
    private PriceCacheRepository priceCacheRepository;

    @Autowired
    private PlatformTransactionManager txManager;

    // Service under test - manually instantiated so we can mock RestTemplate.
    private PriceCacheService priceCacheService;
    private RestTemplate mockRestTemplate;

    @BeforeEach
    void setUp() {
        // Clean cache table before each test.
        priceCacheRepository.deleteAll();

        // Real RetryTemplate with a single attempt to keep tests fast.
        RetryTemplate retryTemplate = RetryTemplate.builder().maxAttempts(1).build();

        // Mock Finnhub HTTP layer so we never make real network calls.
        mockRestTemplate = mock(RestTemplate.class);

        priceCacheService = new PriceCacheService(priceCacheRepository, retryTemplate, mockRestTemplate, txManager);
        ReflectionTestUtils.setField(priceCacheService, "ttlMinutes", TTL_MINUTES);
        ReflectionTestUtils.setField(priceCacheService, "finnhubApiKey", FINNHUB_API_KEY);
        ReflectionTestUtils.setField(priceCacheService, "finnhubBaseUrl", FINNHUB_BASE_URL);
    }

    /**
     * NOTE: {@code @Transactional(propagation = Propagation.NEVER)} is deliberate.
     *
     * {@code @DataJpaTest} defaults to wrapping each test method in a single transaction
     * that rolls back at the end. That outer transaction would silently satisfy the
     * {@code @Modifying} query's transaction requirement on {@code upsert} — masking the
     * exact bug we're trying to catch. Disabling the wrapping transaction means
     * {@code getPrice()} runs without an ambient tx (just like the real /api/market path),
     * which is what triggers {@code TransactionRequiredException} on the broken code path.
     */
    @Test
    @DisplayName("getPrice() persists to DB on first call and serves from cache on second call")
    @Transactional(propagation = Propagation.NEVER)
    @SuppressWarnings("unchecked")
    void getPrice_persistsBetweenCalls_andSecondCallIsCached() {
        // Arrange: stub Finnhub to return a fixed quote.
        var quote = new PriceCacheService.FinnhubQuoteResponse(123.45, 0, 0, 0, 0, 0, 0, 0L);
        doReturn(quote).when(mockRestTemplate).getForObject(anyString(), any(Class.class));

        // Act 1: first call should miss cache, fetch from Finnhub, persist.
        MarketService.PriceData first = priceCacheService.getPrice("AAPL");

        // Assert 1: response indicates fresh fetch.
        assertThat(first).isNotNull();
        assertThat(first.getPrice()).isEqualTo(123.45);
        assertThat(first.isCached()).isFalse();
        assertThat(first.getSource()).contains("Finnhub");

        // Assert 1b: the price_cache row was actually persisted.
        // This is the proof the bug is fixed: before @Transactional, the upsert silently fails.
        Optional<PriceCache> persisted = priceCacheRepository.findBySymbol("AAPL");
        assertThat(persisted)
                .as("After getPrice(), price_cache should contain a row for AAPL")
                .isPresent();
        assertThat(persisted.get().getPrice()).isEqualTo(123.45);
        assertThat(persisted.get().getSource()).isEqualTo("Finnhub");

        // Assert 1c: Finnhub was called exactly once so far.
        verify(mockRestTemplate, times(1)).getForObject(anyString(), any(Class.class));

        // Act 2: second call should hit the cache.
        MarketService.PriceData second = priceCacheService.getPrice("AAPL");

        // Assert 2: response is served from DB cache.
        assertThat(second).isNotNull();
        assertThat(second.getPrice()).isEqualTo(123.45);
        assertThat(second.isCached())
                .as("Second getPrice() should return cached=true (cache was persisted by first call)")
                .isTrue();
        assertThat(second.getSource()).startsWith("DB Cache");

        // Assert 2b: Finnhub was NOT called a second time.
        verify(mockRestTemplate, times(1)).getForObject(anyString(), any(Class.class));
    }
}
