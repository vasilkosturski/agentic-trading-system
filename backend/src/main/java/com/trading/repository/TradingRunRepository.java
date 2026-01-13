package com.trading.repository;

import com.trading.entity.TradingRun;
import com.trading.enums.RunPhase;
import com.trading.enums.RunStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Repository for TradingRun entities.
 * Per design doc: trading.trading_runs table.
 */
@Repository
public interface TradingRunRepository extends JpaRepository<TradingRun, Long> {

    /**
     * Find all runs for a specific agent, ordered by start time descending.
     */
    List<TradingRun> findByAgentIdOrderByStartedAtDesc(Long agentId);

    /**
     * Find runs by agent ID and status.
     */
    List<TradingRun> findByAgentIdAndStatus(Long agentId, RunStatus status);

    /**
     * Find active run for an agent (any phase except COMPLETED/ERROR).
     */
    @Query("SELECT tr FROM TradingRun tr WHERE tr.agent.id = :agentId AND tr.phase NOT IN (com.trading.enums.RunPhase.COMPLETED, com.trading.enums.RunPhase.ERROR)")
    Optional<TradingRun> findActiveRunByAgentId(@Param("agentId") Long agentId);

    /**
     * Find recent runs across all agents (with limit).
     */
    @Query(value = "SELECT * FROM trading.trading_runs ORDER BY started_at DESC LIMIT :limit", nativeQuery = true)
    List<TradingRun> findRecentRuns(@Param("limit") int limit);

    /**
     * Find recent runs for a specific agent (with limit).
     */
    @Query(value = "SELECT * FROM trading.trading_runs WHERE agent_id = :agentId ORDER BY started_at DESC LIMIT :limit", nativeQuery = true)
    List<TradingRun> findRecentRunsByAgentId(@Param("agentId") Long agentId, @Param("limit") int limit);

    /**
     * Count runs by agent and status.
     */
    Long countByAgentIdAndStatus(Long agentId, RunStatus status);
}

