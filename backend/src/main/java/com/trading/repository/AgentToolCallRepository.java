package com.trading.repository;

import com.trading.entity.AgentToolCall;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AgentToolCallRepository extends JpaRepository<AgentToolCall, Long> {

    /**
     * Find all tool calls for a specific run, ordered by sequence number
     */
    List<AgentToolCall> findByAgentRunIdOrderBySequenceNumberAsc(Long agentRunId);

    /**
     * Count tool calls for a specific run
     */
    Long countByAgentRunId(Long agentRunId);

    /**
     * Find tool calls by run and tool name (useful for debugging specific tools)
     */
    @Query("SELECT tc FROM AgentToolCall tc WHERE tc.agentRunId = :runId AND tc.toolName = :toolName ORDER BY tc.sequenceNumber ASC")
    List<AgentToolCall> findByAgentRunIdAndToolName(@Param("runId") Long runId, @Param("toolName") String toolName);

    /**
     * Find failed tool calls for a run
     */
    @Query("SELECT tc FROM AgentToolCall tc WHERE tc.agentRunId = :runId AND tc.success = false ORDER BY tc.sequenceNumber ASC")
    List<AgentToolCall> findFailedToolCallsByRunId(@Param("runId") Long runId);
}

