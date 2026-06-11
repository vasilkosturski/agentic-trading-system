package com.trading.entity;

import com.trading.dto.jsonb.SourceDto;
import com.trading.dto.jsonb.ToolCallDto;
import io.hypersistence.utils.hibernate.type.json.JsonType;
import jakarta.persistence.Column;
import jakarta.persistence.Embedded;
import jakarta.persistence.Entity;
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
 * Research phase entity - stores Market Analyst research outputs.
 * Per design doc Lines 131-135: candidates, sources, research_notes, tool_calls, metrics.
 *
 * Schema: trading.research_phases
 * Relationship: One per trading run (1:1)
 */
@Entity
@Table(
        name = "research_phases",
        schema = "trading",
        uniqueConstraints = {@UniqueConstraint(columnNames = "run_id")})
@Getter
@Setter
@NoArgsConstructor
public class ResearchPhase {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "run_id", nullable = false)
    private TradingRun run;

    /**
     * Stock candidates identified by Market Analyst.
     * JSONB: ["JPM", "BAC", "WFC"]
     */
    @Type(JsonType.class)
    @Column(columnDefinition = "jsonb")
    private List<String> candidates;

    /**
     * Sources used during research (web + system_context).
     * JSONB: [{type, title, url, description}]
     */
    @Type(JsonType.class)
    @Column(columnDefinition = "jsonb")
    private List<SourceDto> sources;

    /**
     * Research notes/summary from Market Analyst.
     */
    @Column(name = "research_notes", columnDefinition = "TEXT")
    private String researchNotes;

    /**
     * Tool calls made during research phase.
     * JSONB: [{tool, duration_ms}] - per design doc Line 898
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
     * Stores the FULL payload (typically a ResearchResponse-shaped dict with
     * summary, candidates, webSources) so the debug view can show what the
     * model actually produced before the guardrail caught it.
     */
    @Type(JsonType.class)
    @Column(name = "guardrail_failed_output", columnDefinition = "jsonb")
    private Map<String, Object> guardrailFailedOutput;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    // Constructor
    public ResearchPhase(TradingRun run) {
        this.run = run;
    }
}
