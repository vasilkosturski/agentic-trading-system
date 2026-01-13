package com.trading.repository;

import com.trading.entity.ResearchPhase;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

/**
 * Repository for ResearchPhase entities.
 * Per design doc: trading.research_phases table (1:1 with trading_runs).
 */
@Repository
public interface ResearchPhaseRepository extends JpaRepository<ResearchPhase, Long> {

    /**
     * Find research phase by trading run ID.
     * One research phase per run (1:1 relationship).
     */
    Optional<ResearchPhase> findByRunId(Long runId);

    /**
     * Check if research phase exists for a run.
     */
    boolean existsByRunId(Long runId);
}

