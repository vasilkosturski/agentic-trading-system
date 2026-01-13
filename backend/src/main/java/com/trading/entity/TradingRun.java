package com.trading.entity;

import com.trading.enums.RunPhase;
import com.trading.enums.RunStatus;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.time.Instant;

/**
 * Trading run entity - tracks each autonomous trading cycle.
 * Per design doc: Parent record with phase lifecycle (INITIALIZING → RESEARCHING → DECIDING → TRADING → COMPLETED).
 * 
 * Replaces: analytics.agent_runs
 * Schema: trading.trading_runs
 */
@Entity
@Table(name = "trading_runs", schema = "trading", indexes = {
    @Index(name = "idx_trading_runs_agent_id", columnList = "agent_id"),
    @Index(name = "idx_trading_runs_status", columnList = "status")
})
@Getter
@Setter
@NoArgsConstructor
public class TradingRun {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "agent_id", nullable = false)
    private TradingAgent agent;

    /**
     * Run status: IN_PROGRESS, COMPLETED, FAILED
     */
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private RunStatus status;

    /**
     * Current phase: INITIALIZING, RESEARCHING, DECIDING, TRADING, COMPLETED, ERROR
     */
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private RunPhase phase;

    @Column(name = "started_at", nullable = false)
    private Instant startedAt;

    @Column(name = "completed_at")
    private Instant completedAt;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    // Bidirectional relationships (Issue #7 fix)
    @OneToOne(mappedBy = "run", fetch = FetchType.LAZY)
    private DecisionPhase decision;

    @OneToOne(mappedBy = "run", fetch = FetchType.LAZY)
    private ExecutionPhase execution;

    // Constructor for creating a new run
    public TradingRun(TradingAgent agent) {
        this.agent = agent;
        this.status = RunStatus.IN_PROGRESS;
        this.phase = RunPhase.INITIALIZING;
        this.startedAt = Instant.now();
    }

    // Business methods
    public void updatePhase(RunPhase newPhase) {
        this.phase = newPhase;
        if (newPhase == RunPhase.COMPLETED || newPhase == RunPhase.ERROR) {
            this.completedAt = Instant.now();
            this.status = (newPhase == RunPhase.ERROR) ? RunStatus.FAILED : RunStatus.COMPLETED;
        }
    }

    public void markAsError(String errorMessage) {
        this.phase = RunPhase.ERROR;
        this.status = RunStatus.FAILED;
        this.errorMessage = errorMessage;
        this.completedAt = Instant.now();
    }

    public void markAsCompleted() {
        this.phase = RunPhase.COMPLETED;
        this.status = RunStatus.COMPLETED;
        this.completedAt = Instant.now();
    }

    // Bidirectional navigation convenience methods
    public boolean hasDecision() {
        return decision != null;
    }

    public boolean hasExecution() {
        return execution != null;
    }

    public boolean isCompleted() {
        return this.completedAt != null;
    }

    public Long getDurationMs() {
        if (this.completedAt == null) {
            return null;
        }
        return this.completedAt.toEpochMilli() - this.startedAt.toEpochMilli();
    }
}

