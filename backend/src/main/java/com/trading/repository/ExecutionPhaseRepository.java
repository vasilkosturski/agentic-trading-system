package com.trading.repository;

import com.trading.entity.ExecutionPhase;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

/**
 * Repository for ExecutionPhase entities.
 * Per design doc: trading.execution_phases table (1:1 with trading_runs).
 */
@Repository
public interface ExecutionPhaseRepository extends JpaRepository<ExecutionPhase, Long> {

    /**
     * Find execution phase by trading run ID.
     * One execution phase per run (1:1 relationship).
     */
    Optional<ExecutionPhase> findByRunId(Long runId);

    /**
     * Check if execution phase exists for a run.
     */
    boolean existsByRunId(Long runId);

    /**
     * Find execution phase by decision phase ID.
     */
    Optional<ExecutionPhase> findByDecisionId(Long decisionId);
}

