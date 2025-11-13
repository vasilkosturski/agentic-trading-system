package com.trading.repository;

import com.trading.entity.AgentReasoningStep;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AgentReasoningStepRepository extends JpaRepository<AgentReasoningStep, Long> {

    /**
     * Find all reasoning steps for a specific run, ordered by sequence number
     */
    List<AgentReasoningStep> findByAgentRunIdOrderBySequenceNumberAsc(Long agentRunId);

    /**
     * Count reasoning steps for a specific run
     */
    Long countByAgentRunId(Long agentRunId);

    /**
     * Find reasoning steps by run and type (e.g., "research", "analysis", "decision")
     */
    @Query("SELECT rs FROM AgentReasoningStep rs WHERE rs.agentRunId = :runId AND rs.stepType = :stepType ORDER BY rs.sequenceNumber ASC")
    List<AgentReasoningStep> findByAgentRunIdAndStepType(@Param("runId") Long runId, @Param("stepType") String stepType);
}

