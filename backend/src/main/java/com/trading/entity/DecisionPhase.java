package com.trading.entity;

import com.trading.dto.jsonb.DecisionToolCallDto;
import com.trading.dto.jsonb.ReasoningDto;
import com.trading.dto.jsonb.SourceDto;
import io.hypersistence.utils.hibernate.type.json.JsonType;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.Type;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

/**
 * Decision phase entity - stores Trader LLM trading decisions.
 * Per design doc Lines 137-141: decision, symbol, quantity, reasoning, sources, tool_calls, metrics.
 * 
 * Schema: trading.decision_phases
 * Relationship: One per trading run (1:1)
 */
@Entity
@Table(name = "decision_phases", schema = "trading", uniqueConstraints = {
    @UniqueConstraint(columnNames = "run_id")
})
@Getter
@Setter
@NoArgsConstructor
public class DecisionPhase {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "run_id", nullable = false)
    private TradingRun run;

    /**
     * Trading decision: BUY, SELL, or HOLD
     */
    @Column(nullable = false, length = 10)
    private String decision;

    /**
     * Symbol for BUY/SELL decisions (null for HOLD)
     */
    @Column(length = 10)
    private String symbol;

    /**
     * Quantity for BUY/SELL decisions (null for HOLD)
     */
    private Integer quantity;

    /**
     * Structured reasoning - 5 fields per design doc.
     * JSONB: {portfolio_context, historical_context, research_summary, candidate_evaluation, final_rationale}
     */
    @Type(JsonType.class)
    @Column(columnDefinition = "jsonb")
    private ReasoningDto reasoning;

    /**
     * Sources used during decision (web + system_context).
     * JSONB: [{type, title, url, description}]
     */
    @Type(JsonType.class)
    @Column(columnDefinition = "jsonb")
    private List<SourceDto> sources;

    /**
     * Tool calls made during decision phase.
     * JSONB: [{tool, params, duration_ms}] - per design doc Line 934
     */
    @Type(JsonType.class)
    @Column(name = "tool_calls", columnDefinition = "jsonb")
    private List<DecisionToolCallDto> toolCalls;

    // Observability metrics
    @Column(name = "tokens_used")
    private Integer tokensUsed;

    @Column(name = "latency_ms")
    private Long latencyMs;

    @Column(name = "cost_usd", precision = 10, scale = 6)
    private BigDecimal costUsd;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    // Constructor
    public DecisionPhase(TradingRun run) {
        this.run = run;
    }

    // Business methods
    public boolean isBuy() {
        return "BUY".equals(decision);
    }

    public boolean isSell() {
        return "SELL".equals(decision);
    }

    public boolean isHold() {
        return "HOLD".equals(decision);
    }

    public boolean requiresExecution() {
        return isBuy() || isSell();
    }
}

