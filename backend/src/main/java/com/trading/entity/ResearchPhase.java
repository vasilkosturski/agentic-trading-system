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
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
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

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    // Constructor
    public ResearchPhase(TradingRun run) {
        this.run = run;
    }
}
