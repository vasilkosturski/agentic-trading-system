package com.trading.service;

import com.trading.entity.PriceCache;
import com.trading.repository.PriceCacheRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.retry.policy.NeverRetryPolicy;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("PriceCacheService Tests")
class PriceCacheServiceTest {

    private static final int TTL_MINUTES = 60;
    private static final String FINNHUB_BASE_URL = "https://finnhub.io/api/v1";
    private static final String FINNHUB_API_KEY = "test-key";

    @Mock
    private PriceCacheRepository priceCacheRepository;

    @Mock
    private RestTemplate restTemplate;

    private RetryTemplate retryTemplate;

    private PriceCacheService priceCacheService;

    @BeforeEach
    void setUp() {
        retryTemplate = new RetryTemplate();
        retryTemplate.setRetryPolicy(new NeverRetryPolicy());

        priceCacheService = new PriceCacheService(priceCacheRepository, retryTemplate, restTemplate);
        ReflectionTestUtils.setField(priceCacheService, "ttlMinutes", TTL_MINUTES);
        ReflectionTestUtils.setField(priceCacheService, "finnhubApiKey", FINNHUB_API_KEY);
        ReflectionTestUtils.setField(priceCacheService, "finnhubBaseUrl", FINNHUB_BASE_URL);
    }

    @Test
    @DisplayName("get() returns empty when symbol is not cached")
    void getReturnsEmptyWhenMissing() {
        when(priceCacheRepository.findBySymbol("AAPL")).thenReturn(Optional.empty());

        Optional<PriceCacheService.CachedPrice> result = priceCacheService.get("AAPL", Instant.now());

        assertTrue(result.isEmpty());
    }

    @Test
    @DisplayName("get() returns empty when cached entry has expired")
    void getReturnsEmptyWhenExpired() {
        Instant now = Instant.now();
        Instant staleCachedAt = now.minus(TTL_MINUTES + 5, ChronoUnit.MINUTES);
        PriceCache stale = new PriceCache("AAPL", 150.0, staleCachedAt, "Finnhub");
        when(priceCacheRepository.findBySymbol("AAPL")).thenReturn(Optional.of(stale));

        Optional<PriceCacheService.CachedPrice> result = priceCacheService.get("AAPL", now);

        assertTrue(result.isEmpty());
    }

    @Test
    @DisplayName("get() returns cached price when entry is fresh")
    void getReturnsCachedWhenFresh() {
        Instant now = Instant.now();
        Instant freshCachedAt = now.minus(5, ChronoUnit.MINUTES);
        PriceCache fresh = new PriceCache("AAPL", 150.0, freshCachedAt, "Finnhub");
        when(priceCacheRepository.findBySymbol("AAPL")).thenReturn(Optional.of(fresh));

        Optional<PriceCacheService.CachedPrice> result = priceCacheService.get("AAPL", now);

        assertTrue(result.isPresent());
        assertEquals(150.0, result.get().price());
        assertEquals(freshCachedAt, result.get().cachedAt());
    }

    @Test
    @DisplayName("cleanupStale() deletes entries older than now minus TTL")
    void cleanupStaleCallsRepoWithCutoff() {
        Instant before = Instant.now();

        priceCacheService.cleanupStale();

        Instant after = Instant.now();

        ArgumentCaptor<Instant> cutoffCaptor = ArgumentCaptor.forClass(Instant.class);
        verify(priceCacheRepository).deleteOlderThan(cutoffCaptor.capture());

        Instant cutoff = cutoffCaptor.getValue();
        Instant earliestExpected = before.minus(TTL_MINUTES, ChronoUnit.MINUTES);
        Instant latestExpected = after.minus(TTL_MINUTES, ChronoUnit.MINUTES);

        assertFalse(cutoff.isBefore(earliestExpected), "cutoff should be >= now(before) - TTL");
        assertFalse(cutoff.isAfter(latestExpected), "cutoff should be <= now(after) - TTL");
    }

    @Test
    @DisplayName("getPrice() returns cached PriceData when cache hit")
    void getPrice_returnsCachedWhenHit() {
        Instant freshCachedAt = Instant.now().minus(5, ChronoUnit.MINUTES);
        PriceCache fresh = new PriceCache("AAPL", 150.0, freshCachedAt, "Finnhub");
        when(priceCacheRepository.findBySymbol("AAPL")).thenReturn(Optional.of(fresh));

        MarketService.PriceData result = priceCacheService.getPrice("AAPL");

        assertNotNull(result);
        assertEquals(150.0, result.getPrice());
        assertTrue(result.isCached());
        assertEquals(freshCachedAt, result.getTimestamp());
        assertTrue(result.getSource().startsWith("DB Cache"),
            "expected source to start with 'DB Cache' but was: " + result.getSource());
        verify(priceCacheRepository, never()).upsert(any(), anyDouble(), any(Instant.class), any());
    }

    @Test
    @DisplayName("getPrice() fetches from Finnhub on miss and persists via repository upsert")
    @SuppressWarnings("unchecked")
    void getPrice_fetchesFromFinnhubOnMiss_andPersists() {
        when(priceCacheRepository.findBySymbol("AAPL")).thenReturn(Optional.empty());

        var quote = new PriceCacheService.FinnhubQuoteResponse(123.45, 0, 0, 0, 0, 0, 0, 0L);
        doReturn(quote).when(restTemplate).getForObject(anyString(), any(Class.class));

        MarketService.PriceData result = priceCacheService.getPrice("AAPL");

        assertNotNull(result);
        assertEquals(123.45, result.getPrice());
        assertFalse(result.isCached());
        assertEquals("Real-time quote from Finnhub", result.getSource());
        verify(priceCacheRepository, times(1))
            .upsert(eq("AAPL"), eq(123.45), any(Instant.class), eq("Finnhub"));
    }

    @Test
    @DisplayName("getPrice() returns null when Finnhub fails after retries")
    @SuppressWarnings("unchecked")
    void getPrice_returnsNullWhenFinnhubFails() {
        when(priceCacheRepository.findBySymbol("AAPL")).thenReturn(Optional.empty());
        doThrow(new RestClientException("boom"))
            .when(restTemplate).getForObject(anyString(), any(Class.class));

        MarketService.PriceData result = priceCacheService.getPrice("AAPL");

        assertNull(result);
        verify(priceCacheRepository, never()).upsert(any(), anyDouble(), any(Instant.class), any());
    }

    @Test
    @DisplayName("getPrice() swallows repository exceptions on cache write (best-effort)")
    @SuppressWarnings("unchecked")
    void getPrice_swallowsRepositoryExceptionOnWrite() {
        when(priceCacheRepository.findBySymbol("AAPL")).thenReturn(Optional.empty());

        var quote = new PriceCacheService.FinnhubQuoteResponse(123.45, 0, 0, 0, 0, 0, 0, 0L);
        doReturn(quote).when(restTemplate).getForObject(anyString(), any(Class.class));

        doThrow(new RuntimeException("DB hiccup"))
            .when(priceCacheRepository).upsert(anyString(), anyDouble(), any(Instant.class), anyString());

        MarketService.PriceData result = priceCacheService.getPrice("AAPL");

        assertNotNull(result);
        assertEquals(123.45, result.getPrice());
        assertFalse(result.isCached());
        assertEquals("Real-time quote from Finnhub", result.getSource());
    }
}
