package com.trading.repository;

import com.trading.entity.TradingRun;
import com.trading.enums.RunStatus;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

/**
 * Repository for TradingRun entities.
 * Per design doc: trading.trading_runs table.
 */
@Repository
public interface TradingRunRepository extends JpaRepository<TradingRun, Long>, JpaSpecificationExecutor<TradingRun> {

    /**
     * Find all runs for a specific agent, ordered by start time descending.
     */
    List<TradingRun> findByAgentIdOrderByStartedAtDesc(Long agentId);

    /**
     * Find runs by agent ID and status.
     */
    List<TradingRun> findByAgentIdAndStatus(Long agentId, RunStatus status);

    /**
     * Find active run for an agent (any phase except COMPLETED/FAILED).
     */
    @Query(
            "SELECT tr FROM TradingRun tr WHERE tr.agent.id = :agentId AND tr.phase NOT IN (com.trading.enums.RunPhase.COMPLETED, com.trading.enums.RunPhase.FAILED)")
    Optional<TradingRun> findActiveRunByAgentId(@Param("agentId") Long agentId);

    /**
     * Find recent runs across all agents (with limit).
     */
    @Query(value = "SELECT * FROM trading.trading_runs ORDER BY started_at DESC LIMIT :limit", nativeQuery = true)
    List<TradingRun> findRecentRuns(@Param("limit") int limit);

    /**
     * Find recent runs for a specific agent (with limit).
     */
    @Query(
            value =
                    "SELECT * FROM trading.trading_runs WHERE agent_id = :agentId ORDER BY started_at DESC LIMIT :limit",
            nativeQuery = true)
    List<TradingRun> findRecentRunsByAgentId(@Param("agentId") Long agentId, @Param("limit") int limit);

    /**
     * Count runs by agent and status.
     */
    Long countByAgentIdAndStatus(Long agentId, RunStatus status);

    /**
     * Find all runs where startedAt is before the specified cutoff date.
     * Used to filter runs by publicDisplayDelayDays at database level.
     */
    Page<TradingRun> findByStartedAtBefore(Instant cutoffDate, Pageable pageable);

    /**
     * Find runs for an agent within an exclusive startedAt date range.
     * Boundaries are EXCLUSIVE on both ends to match Instant.isAfter(since) / isBefore(cutoffDate) semantics.
     * Pageable lets callers push the row limit (e.g. 20) to the database.
     */
    @Query("SELECT tr FROM TradingRun tr " + "WHERE tr.agent.id = :agentId "
            + "AND tr.startedAt > :since "
            + "AND tr.startedAt < :cutoffDate "
            + "ORDER BY tr.startedAt DESC")
    List<TradingRun> findByAgentIdAndStartedAtBetween(
            @Param("agentId") Long agentId,
            @Param("since") Instant since,
            @Param("cutoffDate") Instant cutoffDate,
            Pageable pageable);
}
