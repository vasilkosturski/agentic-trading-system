package com.trading.entity;

import com.trading.dto.jsonb.ReasoningDto;
import com.trading.dto.jsonb.SourceDto;
import com.trading.dto.jsonb.ToolCallDto;
import com.trading.enums.TradeDecision;
import io.hypersistence.utils.hibernate.type.json.JsonType;
import jakarta.persistence.Column;
import jakarta.persistence.Embedded;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.ColumnDefault;
import org.hibernate.annotations.Type;

/**
 * Decision phase entity - stores Trader LLM trading decisions.
 * Per design doc Lines 137-141: decision, symbol, quantity, reasoning, sources, tool_calls, metrics.
 *
 * Schema: trading.decision_phases
 * Relationship: One per trading run (1:1)
 */
@Entity
@Table(
        name = "decision_phases",
        schema = "trading",
        uniqueConstraints = {@UniqueConstraint(columnNames = "run_id")})
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
     * Uses enum with EnumType.STRING for type safety and DB readability.
     */
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 10)
    private TradeDecision decision;

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
     * Structured reasoning - 3 fields.
     * JSONB: {portfolio_context, historical_context, research_summary}
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
    private List<ToolCallDto> toolCalls;

    @Column(name = "system_prompt", columnDefinition = "TEXT")
    private String systemPrompt;

    @Column(name = "task_prompt", columnDefinition = "TEXT")
    private String taskPrompt;

    // Observability metrics (embedded — maps to same flat columns)
    @Embedded
    private UsageMetrics metrics;

    @Column(name = "latency_ms")
    private Long latencyMs;

    /**
     * Number of attempts the guardrail-retry loop used for this phase.
     * Defaults to 1 (first-try success). Set to 2 or 3 when the LLM had to
     * self-correct after a guardrail rejection.
     */
    @Column(name = "guardrail_attempts", nullable = false)
    @ColumnDefault("1")
    private Integer guardrailAttempts = 1;

    /**
     * Issue strings from the LAST failed attempt; NULL on first-try success.
     * JSONB: ["fake_url", "empty_candidates"]
     */
    @Type(JsonType.class)
    @Column(name = "guardrail_issues", columnDefinition = "jsonb")
    private List<String> guardrailIssues;

    /**
     * Per-phase guardrail outcome label. Application-validated enum:
     * one of 'first_try', 'recovered', 'exhausted'.
     */
    @Column(name = "guardrail_outcome", nullable = false, columnDefinition = "TEXT")
    @ColumnDefault("'first_try'")
    private String guardrailOutcome = "first_try";

    /**
     * Last rejected LLM output as a JSON-safe object; NULL on first-try success.
     * Stores the FULL payload (typically a TradingDecision-shaped dict with
     * action, symbol, quantity, rationale) so the debug view can show what the
     * model actually produced before the guardrail caught it.
     */
    @Type(JsonType.class)
    @Column(name = "guardrail_failed_output", columnDefinition = "jsonb")
    private Map<String, Object> guardrailFailedOutput;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    // Constructor
    public DecisionPhase(TradingRun run) {
        this.run = run;
    }

    // Business methods - now use enum comparison (type-safe)
    public boolean isBuy() {
        return decision == TradeDecision.BUY;
    }

    public boolean isSell() {
        return decision == TradeDecision.SELL;
    }

    public boolean isHold() {
        return decision == TradeDecision.HOLD;
    }

    public boolean requiresExecution() {
        return isBuy() || isSell();
    }
}
