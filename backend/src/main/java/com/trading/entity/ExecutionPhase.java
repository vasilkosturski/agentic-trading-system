package com.trading.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.time.Instant;

/**
 * Execution phase entity - stores trade execution results.
 * Per design doc Lines 143-146: trade_id, status (executed/failed/skipped), error_details.
 * 
 * Schema: trading.execution_phases
 * Relationship: Optional - only exists for BUY/SELL decisions (0..1 per run)
 */
@Entity
@Table(name = "execution_phases", schema = "trading", uniqueConstraints = {
    @UniqueConstraint(columnNames = "run_id")
})
@Getter
@Setter
@NoArgsConstructor
public class ExecutionPhase {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "run_id", nullable = false)
    private TradingRun run;

    /**
     * Reference to the decision that led to this execution.
     */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "decision_id")
    private DecisionPhase decision;

    /**
     * Reference to the executed trade (if successful).
     * Null if execution failed or was skipped.
     */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "trade_id")
    private AccountTransaction trade;

    /**
     * Execution status: executed, failed, skipped
     * - executed: Trade completed successfully
     * - failed: Trade validation failed (insufficient funds, etc.)
     * - skipped: HOLD decision, no trade needed
     */
    @Column(nullable = false, length = 20)
    private String status;

    /**
     * Error details for failed executions.
     * Example: "Insufficient funds: need $4500.00, have $2000.00"
     */
    @Column(name = "error_details", columnDefinition = "TEXT")
    private String errorDetails;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    // Constructor for successful execution
    public ExecutionPhase(TradingRun run, DecisionPhase decision, AccountTransaction trade) {
        this.run = run;
        this.decision = decision;
        this.trade = trade;
        this.status = "executed";
    }

    // Constructor for failed execution
    public ExecutionPhase(TradingRun run, DecisionPhase decision, String errorDetails) {
        this.run = run;
        this.decision = decision;
        this.status = "failed";
        this.errorDetails = errorDetails;
    }

    // Constructor for skipped execution (HOLD decision)
    public ExecutionPhase(TradingRun run) {
        this.run = run;
        this.status = "skipped";
        this.errorDetails = "HOLD decision";
    }

    // Business methods
    public boolean isExecuted() {
        return "executed".equals(status);
    }

    public boolean isFailed() {
        return "failed".equals(status);
    }

    public boolean isSkipped() {
        return "skipped".equals(status);
    }
}

