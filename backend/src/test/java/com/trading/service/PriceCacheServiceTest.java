package com.trading.service;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.trading.entity.PriceCache;
import com.trading.repository.PriceCacheRepository;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.retry.policy.NeverRetryPolicy;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

@ExtendWith(MockitoExtension.class)
@DisplayName("PriceCacheService Tests")
class PriceCacheServiceTest {

    private static final int TTL_MINUTES = 60;
    private static final int COOLDOWN_SECONDS = 60;
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
        ReflectionTestUtils.setField(priceCacheService, "rateLimitCooldownSeconds", COOLDOWN_SECONDS);
    }

    private ListAppender<ILoggingEvent> attachAppender() {
        Logger svcLogger = (Logger) LoggerFactory.getLogger(PriceCacheService.class);
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.start();
        svcLogger.addAppender(appender);
        return appender;
    }

    @Test
    @DisplayName("getPrice() sets the circuit breaker when Finnhub returns 429")
    @SuppressWarnings("unchecked")
    void getPrice_setsCircuitBreaker_whenFinnhubReturns429() {
        when(priceCacheRepository.findBySymbol("AAPL")).thenReturn(Optional.empty());
        doThrow(HttpClientErrorException.create(HttpStatus.TOO_MANY_REQUESTS, "Too Many Requests", null, null, null))
                .when(restTemplate)
                .getForObject(anyString(), any(Class.class));

        Instant before = Instant.now();
        MarketService.PriceData result = priceCacheService.getPrice("AAPL");
        Instant after = Instant.now();

        assertNull(result, "no stale cache exists - should return null per existing semantics");

        Instant rateLimitedUntil = (Instant) ReflectionTestUtils.getField(priceCacheService, "rateLimitedUntil");
        assertNotNull(rateLimitedUntil);
        Instant earliest = before.plusSeconds(COOLDOWN_SECONDS).minusSeconds(2);
        Instant latest = after.plusSeconds(COOLDOWN_SECONDS).plusSeconds(2);
        assertFalse(rateLimitedUntil.isBefore(earliest), "rateLimitedUntil should be ~60s in the future");
        assertFalse(rateLimitedUntil.isAfter(latest), "rateLimitedUntil should be ~60s in the future");
    }

    @Test
    @DisplayName("getPrice() skips Finnhub during cool-down and uses stale cache")
    @SuppressWarnings("unchecked")
    void getPrice_skipsFinnhubDuringCooldown_andUsesStaleCache() {
        ReflectionTestUtils.setField(
                priceCacheService, "rateLimitedUntil", Instant.now().plusSeconds(30));

        Instant staleCachedAt = Instant.now().minus(TTL_MINUTES + 10, ChronoUnit.MINUTES);
        PriceCache stale = new PriceCache("AAPL", 142.5, staleCachedAt, "Finnhub");
        when(priceCacheRepository.findBySymbol("AAPL")).thenReturn(Optional.of(stale));

        MarketService.PriceData result = priceCacheService.getPrice("AAPL");

        assertNotNull(result);
        assertEquals(142.5, result.getPrice());
        assertTrue(
                result.getSource().startsWith("Stale Cache"),
                "expected Stale Cache source but was: " + result.getSource());
        verify(restTemplate, never()).getForObject(anyString(), any(Class.class));
    }

    @Test
    @DisplayName("getPrice() resumes calling Finnhub after the cool-down expires")
    @SuppressWarnings("unchecked")
    void getPrice_resumesFinnhubAfterCooldownExpires() {
        ReflectionTestUtils.setField(
                priceCacheService, "rateLimitedUntil", Instant.now().minusSeconds(1));
        when(priceCacheRepository.findBySymbol("AAPL")).thenReturn(Optional.empty());

        var quote = new PriceCacheService.FinnhubQuoteResponse(200.0, 0, 0, 0, 0, 0, 0, 0L);
        doReturn(quote).when(restTemplate).getForObject(anyString(), any(Class.class));

        MarketService.PriceData result = priceCacheService.getPrice("AAPL");

        assertNotNull(result);
        assertEquals(200.0, result.getPrice());
        verify(restTemplate, times(1)).getForObject(anyString(), any(Class.class));
    }

    @Test
    @DisplayName("getPrice() logs the cool-down notice only once per window")
    void getPrice_singleCooldownLogPerWindow() {
        ReflectionTestUtils.setField(
                priceCacheService, "rateLimitedUntil", Instant.now().plusSeconds(30));
        when(priceCacheRepository.findBySymbol(anyString())).thenReturn(Optional.empty());

        ListAppender<ILoggingEvent> appender = attachAppender();

        for (String sym : List.of("AAPL", "MSFT", "GOOG", "TSLA", "NVDA")) {
            priceCacheService.getPrice(sym);
        }

        long cooldownLogs = appender.list.stream()
                .filter(e -> e.getLevel() == Level.INFO)
                .filter(e -> e.getFormattedMessage().contains("rate-limit cool-down active"))
                .count();
        assertEquals(1, cooldownLogs, "expected exactly ONE cool-down INFO log per window");
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
        assertTrue(
                result.getSource().startsWith("DB Cache"),
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
        verify(priceCacheRepository, times(1)).upsert(eq("AAPL"), eq(123.45), any(Instant.class), eq("Finnhub"));
    }

    @Test
    @DisplayName("getPrice() returns null when Finnhub fails after retries")
    @SuppressWarnings("unchecked")
    void getPrice_returnsNullWhenFinnhubFails() {
        when(priceCacheRepository.findBySymbol("AAPL")).thenReturn(Optional.empty());
        doThrow(new RestClientException("boom")).when(restTemplate).getForObject(anyString(), any(Class.class));

        MarketService.PriceData result = priceCacheService.getPrice("AAPL");

        assertNull(result);
        verify(priceCacheRepository, never()).upsert(any(), anyDouble(), any(Instant.class), any());
    }

    @Test
    @DisplayName("getPrice() swallows ConcurrencyFailureException on cache write (concurrent upsert)")
    @SuppressWarnings("unchecked")
    void getPrice_swallowsConcurrencyFailureOnWrite() {
        when(priceCacheRepository.findBySymbol("AAPL")).thenReturn(Optional.empty());

        var quote = new PriceCacheService.FinnhubQuoteResponse(123.45, 0, 0, 0, 0, 0, 0, 0L);
        doReturn(quote).when(restTemplate).getForObject(anyString(), any(Class.class));

        // CannotAcquireLockException extends ConcurrencyFailureException - exactly the kind
        // of concurrent-upsert race we still want to tolerate silently.
        doThrow(new org.springframework.dao.CannotAcquireLockException("lost the race"))
                .when(priceCacheRepository)
                .upsert(anyString(), anyDouble(), any(Instant.class), anyString());

        MarketService.PriceData result = priceCacheService.getPrice("AAPL");

        assertNotNull(result);
        assertEquals(123.45, result.getPrice());
        assertFalse(result.isCached());
        assertEquals("Real-time quote from Finnhub", result.getSource());
    }

    @Test
    @DisplayName("getPrice() does NOT swallow unexpected RuntimeException on cache write")
    @SuppressWarnings("unchecked")
    void getPrice_propagatesUnexpectedRuntimeExceptionOnWrite() {
        when(priceCacheRepository.findBySymbol("AAPL")).thenReturn(Optional.empty());

        var quote = new PriceCacheService.FinnhubQuoteResponse(123.45, 0, 0, 0, 0, 0, 0, 0L);
        doReturn(quote).when(restTemplate).getForObject(anyString(), any(Class.class));

        // After narrowing the catch, an arbitrary RuntimeException (e.g. TransactionRequiredException
        // wrapped as InvalidDataAccessApiUsageException) must propagate so regressions stay visible.
        doThrow(new RuntimeException("DB hiccup"))
                .when(priceCacheRepository)
                .upsert(anyString(), anyDouble(), any(Instant.class), anyString());

        assertThrows(RuntimeException.class, () -> priceCacheService.getPrice("AAPL"));
    }
}
