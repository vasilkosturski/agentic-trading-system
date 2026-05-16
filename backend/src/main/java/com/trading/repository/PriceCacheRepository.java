package com.trading.repository;

import com.trading.entity.PriceCache;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.Optional;

@Repository
public interface PriceCacheRepository extends JpaRepository<PriceCache, String> {

    /**
     * Find cached price by symbol.
     */
    Optional<PriceCache> findBySymbol(String symbol);

    /**
     * Delete cache entries older than the given timestamp.
     * Useful for cleanup of stale data.
     */
    @Modifying
    @Query("DELETE FROM PriceCache p WHERE p.cachedAt < :cutoffTime")
    void deleteOlderThan(@Param("cutoffTime") Instant cutoffTime);

    /**
     * Upsert (INSERT ... ON CONFLICT UPDATE) to avoid deadlocks on concurrent cache updates.
     * Uses native SQL with ON CONFLICT to handle race conditions gracefully.
     *
     * Annotated {@code @Transactional} because Spring Data JPA requires a transactional
     * context for {@code @Modifying} queries; without it Spring throws
     * {@code TransactionRequiredException} and the write silently fails. Propagation is
     * the default ({@code REQUIRED}) so callers can wrap multiple operations in one
     * transaction if needed.
     *
     * The {@link com.trading.service.PriceCacheService#getPrice} catch block downstream
     * still absorbs a narrow set of {@link org.springframework.dao.DataAccessException}
     * subtypes (e.g. {@link org.springframework.dao.CannotAcquireLockException} on
     * concurrent upsert deadlocks) — see {@code PriceCacheService.getPrice()} for the
     * documented swallow semantics.
     */
    @Modifying
    @Transactional
    @Query(value = "INSERT INTO analytics.price_cache (symbol, price, cached_at, source) " +
                   "VALUES (:symbol, :price, :cachedAt, :source) " +
                   "ON CONFLICT (symbol) DO UPDATE SET " +
                   "price = EXCLUDED.price, cached_at = EXCLUDED.cached_at, source = EXCLUDED.source",
           nativeQuery = true)
    void upsert(@Param("symbol") String symbol,
                @Param("price") double price,
                @Param("cachedAt") Instant cachedAt,
                @Param("source") String source);
}
