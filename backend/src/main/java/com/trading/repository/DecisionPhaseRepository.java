package com.trading.repository;

import com.trading.entity.DecisionPhase;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Repository for DecisionPhase entities.
 * Per design doc: trading.decision_phases table (1:1 with trading_runs).
 */
@Repository
public interface DecisionPhaseRepository extends JpaRepository<DecisionPhase, Long> {

    /**
     * Find decision phase by trading run ID.
     * One decision phase per run (1:1 relationship).
     */
    Optional<DecisionPhase> findByRunId(Long runId);

    /**
     * Check if decision phase exists for a run.
     */
    boolean existsByRunId(Long runId);
}
