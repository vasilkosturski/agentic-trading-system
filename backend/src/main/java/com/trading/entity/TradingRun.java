package com.trading.entity;

import com.trading.enums.RunPhase;
import com.trading.enums.RunStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(
        name = "trading_runs",
        schema = "trading",
        indexes = {
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

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private RunStatus status;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private RunPhase phase;

    @Column(name = "started_at", nullable = false)
    private Instant startedAt;

    @Column(name = "completed_at")
    private Instant completedAt;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @OneToOne(mappedBy = "run", fetch = FetchType.LAZY)
    private DecisionPhase decision;

    @OneToOne(mappedBy = "run", fetch = FetchType.LAZY)
    private ExecutionPhase execution;

    public TradingRun(TradingAgent agent) {
        this.agent = agent;
        this.status = RunStatus.IN_PROGRESS;
        this.phase = RunPhase.INITIALIZING;
        this.startedAt = Instant.now();
    }

    public void updatePhase(RunPhase newPhase) {
        this.phase = newPhase;
        if (newPhase == RunPhase.COMPLETED || newPhase == RunPhase.FAILED) {
            this.completedAt = Instant.now();
            this.status = (newPhase == RunPhase.FAILED) ? RunStatus.FAILED : RunStatus.COMPLETED;
        }
    }

    @SuppressWarnings("checkstyle:HiddenField") // parameter intentionally mirrors the field it assigns
    public void markAsError(String errorMessage) {
        this.phase = RunPhase.FAILED;
        this.status = RunStatus.FAILED;
        this.errorMessage = errorMessage;
        this.completedAt = Instant.now();
    }

    public void markAsCompleted() {
        this.phase = RunPhase.COMPLETED;
        this.status = RunStatus.COMPLETED;
        this.completedAt = Instant.now();
    }

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
