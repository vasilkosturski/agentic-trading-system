package com.trading.service;

import com.trading.entity.PriceCache;
import com.trading.repository.PriceCacheRepository;
import java.time.Duration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

@Service
public class PriceCacheService {

    private static final Logger logger = LoggerFactory.getLogger(PriceCacheService.class);

    private final PriceCacheRepository priceCacheRepository;
    private final RetryTemplate retryTemplate;
    private final RestTemplate restTemplate;

    // REQUIRES_NEW so the cache-fill upsert runs in its own writable transaction even when the
    // outer caller is `@Transactional(readOnly = true)` (e.g. TradingRunService, MemoryService).
    // Without this, getPrice() on a cache miss fails with PostgreSQL error 25006
    // "cannot execute INSERT in a read-only transaction" and the whole outer transaction aborts.
    private final TransactionTemplate cacheWriteTx;

    @Value("${market.cache.ttl-minutes:60}")
    private int ttlMinutes;

    @Value("${market.finnhub.api-key:}")
    private String finnhubApiKey;

    @Value("${market.finnhub.base-url:https://finnhub.io/api/v1}")
    private String finnhubBaseUrl;

    @Value("${market.finnhub.rate-limit-cooldown-seconds:60}")
    private int rateLimitCooldownSeconds;

    // Finnhub's free-tier limit is per-minute, so once we see a 429 the entire bucket is
    // exhausted until the next window. We trip a process-local cool-down so the rest of the
    // burst skips Finnhub and falls through to stale cache instead of independently
    // rediscovering the same 429.
    private volatile Instant rateLimitedUntil = Instant.EPOCH;
    private volatile Instant cooldownLoggedFor = Instant.EPOCH;

    public PriceCacheService(
            PriceCacheRepository priceCacheRepository,
            RetryTemplate retryTemplate,
            RestTemplate restTemplate,
            PlatformTransactionManager txManager) {
        this.priceCacheRepository = priceCacheRepository;
        this.retryTemplate = retryTemplate;
        this.restTemplate = restTemplate;
        this.cacheWriteTx = new TransactionTemplate(txManager);
        this.cacheWriteTx.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
        this.cacheWriteTx.setReadOnly(false);
    }

    /**
     * High-level entry point: return a cached price if fresh, otherwise fetch from Finnhub,
     * persist to cache, and return. Returns null if Finnhub has no data / fails after retries.
     */
    public MarketService.PriceData getPrice(String symbol) {
        Instant now = Instant.now();
        Optional<CachedPrice> hit = get(symbol, now);
        if (hit.isPresent()) {
            CachedPrice cached = hit.get();
            long ageMinutes = Duration.between(cached.cachedAt(), now).toMinutes();
            logger.debug("Returning DB-cached price for {}: ${} (age: {} min)", symbol, cached.price(), ageMinutes);
            return new MarketService.PriceData(
                    cached.price(), true, cached.cachedAt(), "DB Cache (age: " + ageMinutes + " min)");
        }

        Double fresh = now.isBefore(rateLimitedUntil) ? null : fetchFromFinnhub(symbol);
        if (fresh == null) {
            if (now.isBefore(rateLimitedUntil)) {
                Instant currentWindow = rateLimitedUntil;
                if (!currentWindow.equals(cooldownLoggedFor)) {
                    cooldownLoggedFor = currentWindow;
                    logger.info(
                            "Finnhub rate-limit cool-down active until {} - using cache fallback for all symbols",
                            currentWindow);
                }
            }
            // Finnhub failed (rate limit or error) - try to use stale cache as fallback
            Optional<PriceCache> staleCache = priceCacheRepository.findBySymbol(symbol);
            if (staleCache.isPresent()) {
                PriceCache cached = staleCache.get();
                long ageMinutes = Duration.between(cached.getCachedAt(), now).toMinutes();
                logger.info("Finnhub unavailable for {} - using stale cache (age: {} min)", symbol, ageMinutes);
                return new MarketService.PriceData(
                        cached.getPrice(),
                        true,
                        cached.getCachedAt(),
                        "Stale Cache (age: " + ageMinutes + " min, Finnhub unavailable)");
            }
            return null;
        }
        try {
            cacheWriteTx.executeWithoutResult(status -> priceCacheRepository.upsert(symbol, fresh, now, "Finnhub"));
            logger.debug("Saved price to DB cache: {} = ${}", symbol, fresh);
        } catch (org.springframework.dao.ConcurrencyFailureException e) {
            // Concurrent upsert lost the race (CannotAcquireLockException, DeadlockLoserDataAccessException,
            // PessimisticLockingFailureException etc. all extend ConcurrencyFailureException); the other
            // writer's value is now in the cache. Skipping is the correct behavior - price will be served
            // from cache on the next call. Logged at WARN with the exception class name so future
            // regressions (e.g. TransactionRequiredException) stay visible instead of being swallowed.
            logger.warn(
                    "Concurrent cache upsert for {}: {} - continuing without our value",
                    symbol,
                    e.getClass().getSimpleName());
        }
        return new MarketService.PriceData(fresh, false, now, "Real-time quote from Finnhub");
    }

    /**
     * Look up a cached price. Returns empty if missing or expired relative to {@code now}.
     * Package-private: callers go through {@link #getPrice(String)}; direct access is for same-package tests.
     * Not transactional on the read path to avoid deadlocks.
     */
    Optional<CachedPrice> get(String symbol, Instant now) {
        Optional<PriceCache> cachedOpt = priceCacheRepository.findBySymbol(symbol);
        if (cachedOpt.isEmpty()) {
            return Optional.empty();
        }

        PriceCache cached = cachedOpt.get();
        Instant expiryTime = cached.getCachedAt().plus(ttlMinutes, ChronoUnit.MINUTES);
        if (now.isBefore(expiryTime)) {
            return Optional.of(new CachedPrice(cached.getPrice(), cached.getCachedAt()));
        }
        return Optional.empty();
    }

    /**
     * Periodically evict stale entries older than the TTL.
     * Default interval: 1 hour (overridable via market.cache.cleanup-interval-ms).
     */
    @Scheduled(fixedRateString = "${market.cache.cleanup-interval-ms:3600000}")
    @Transactional
    public void cleanupStale() {
        Instant cutoff = Instant.now().minus(ttlMinutes, ChronoUnit.MINUTES);
        priceCacheRepository.deleteOlderThan(cutoff);
        logger.info("Evicted price cache entries older than {}", cutoff);
    }

    private Double fetchFromFinnhub(String symbol) {
        try {
            FinnhubQuoteResponse quote = retryTemplate.execute(ctx -> {
                if (ctx.getRetryCount() > 0) {
                    logger.warn("Finnhub retry {}/3 for {}", ctx.getRetryCount(), symbol);
                }
                String url = String.format("%s/quote?symbol=%s&token=%s", finnhubBaseUrl, symbol, finnhubApiKey);
                return restTemplate.getForObject(url, FinnhubQuoteResponse.class);
            });

            if (quote != null && quote.c() > 0) {
                logger.info("Finnhub price for {}: ${}", symbol, quote.c());
                return quote.c();
            }

            if (quote != null) {
                logger.warn("Finnhub returned zero price for {} - symbol may not be supported", symbol);
            }
            return null;

        } catch (RestClientException e) {
            // Log as INFO if it's a 429 rate limit (expected), ERROR for other failures
            if (e.getMessage() != null && e.getMessage().contains("429")) {
                rateLimitedUntil = Instant.now().plusSeconds(rateLimitCooldownSeconds);
                logger.info("Finnhub rate limit hit for {} - will use cache fallback", symbol);
            } else {
                logger.error("Finnhub failed after retries for {}: {}", symbol, e.getMessage());
            }
            return null;
        }
    }

    record FinnhubQuoteResponse(double c, double d, double dp, double h, double l, double o, double pc, long t) {}

    public record CachedPrice(double price, Instant cachedAt) {}
}
