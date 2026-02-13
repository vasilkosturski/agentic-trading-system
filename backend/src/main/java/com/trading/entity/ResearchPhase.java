package com.trading.entity;

import com.trading.dto.jsonb.ToolCallDto;
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
 * Research phase entity - stores Market Analyst research outputs.
 * Per design doc Lines 131-135: candidates, sources, research_notes, tool_calls, metrics.
 * 
 * Schema: trading.research_phases
 * Relationship: One per trading run (1:1)
 */
@Entity
@Table(name = "research_phases", schema = "trading", uniqueConstraints = {
    @UniqueConstraint(columnNames = "run_id")
})
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
    public ResearchPhase(TradingRun run) {
        this.run = run;
    }
}

