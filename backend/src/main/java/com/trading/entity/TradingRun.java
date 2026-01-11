package com.trading.entity;

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
     * Run status: pending, in_progress, completed, failed
     */
    @Column(nullable = false, length = 20)
    private String status;

    /**
     * Current phase: INITIALIZING, RESEARCHING, DECIDING, TRADING, COMPLETED, ERROR
     */
    @Column(nullable = false, length = 20)
    private String phase;

    @Column(name = "started_at", nullable = false)
    private Instant startedAt;

    @Column(name = "completed_at")
    private Instant completedAt;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    // Constructor for creating a new run
    public TradingRun(TradingAgent agent) {
        this.agent = agent;
        this.status = "in_progress";
        this.phase = "INITIALIZING";
        this.startedAt = Instant.now();
    }

    // Business methods
    public void updatePhase(String newPhase) {
        this.phase = newPhase;
        if ("COMPLETED".equals(newPhase) || "ERROR".equals(newPhase)) {
            this.completedAt = Instant.now();
            this.status = "ERROR".equals(newPhase) ? "failed" : "completed";
        }
    }

    public void markAsError(String errorMessage) {
        this.phase = "ERROR";
        this.status = "failed";
        this.errorMessage = errorMessage;
        this.completedAt = Instant.now();
    }

    public void markAsCompleted() {
        this.phase = "COMPLETED";
        this.status = "completed";
        this.completedAt = Instant.now();
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

