package com.trading.repository;

import com.trading.entity.AgentRun;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AgentRunRepository extends JpaRepository<AgentRun, Long> {

    /**
     * Find all runs for a specific agent, ordered by start time descending
     */
    List<AgentRun> findByAgentNameOrderByStartTimeDesc(String agentName);

    /**
     * Find runs by agent and outcome
     */
    @Query("SELECT ar FROM AgentRun ar WHERE ar.agentName = :agentName AND ar.outcome = :outcome ORDER BY ar.startTime DESC")
    List<AgentRun> findByAgentNameAndOutcome(@Param("agentName") String agentName, @Param("outcome") String outcome);

    /**
     * Find runs by run type
     */
    List<AgentRun> findByRunTypeOrderByStartTimeDesc(String runType);

    /**
     * Find recent runs across all agents (last N runs)
     */
    @Query(value = "SELECT * FROM analytics.agent_runs ORDER BY start_time DESC LIMIT :limit", nativeQuery = true)
    List<AgentRun> findRecentRuns(@Param("limit") int limit);

    /**
     * Find recent runs for a specific agent
     */
    @Query(value = "SELECT * FROM analytics.agent_runs WHERE agent_name = :agentName ORDER BY start_time DESC LIMIT :limit", nativeQuery = true)
    List<AgentRun> findRecentRunsByAgent(@Param("agentName") String agentName, @Param("limit") int limit);

    /**
     * Count runs by agent and outcome
     */
    @Query("SELECT COUNT(ar) FROM AgentRun ar WHERE ar.agentName = :agentName AND ar.outcome = :outcome")
    Long countByAgentNameAndOutcome(@Param("agentName") String agentName, @Param("outcome") String outcome);

    /**
     * Get total trade count for an agent
     */
    @Query("SELECT COALESCE(SUM(ar.tradeCount), 0) FROM AgentRun ar WHERE ar.agentName = :agentName")
    Integer getTotalTradeCountByAgent(@Param("agentName") String agentName);

    /**
     * Find runs with errors
     */
    @Query("SELECT ar FROM AgentRun ar WHERE ar.outcome = 'ERROR' ORDER BY ar.startTime DESC")
    List<AgentRun> findRunsWithErrors();
}
