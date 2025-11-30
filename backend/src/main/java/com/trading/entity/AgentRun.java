package com.trading.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.time.Instant;

@Entity
@Table(name = "agent_runs", schema = "analytics")
@Getter
@Setter
@NoArgsConstructor
public class AgentRun {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "agent_name", nullable = false)
    private String agentName;

    @Column(name = "run_type", nullable = false)
    private String runType; // TRADING, REBALANCE

    @Column(name = "start_time", nullable = false)
    private Instant startTime;

    @Column(name = "end_time")
    private Instant endTime;

    @Column(nullable = false)
    private String outcome; // TRADED, NO_TRADE, ERROR

    @Column(columnDefinition = "TEXT")
    private String summary; // Simple summary (brief explanation)

    @Column(name = "full_reasoning", columnDefinition = "TEXT")
    private String fullReasoning; // Full detailed reasoning

    @Column(name = "research_sources", columnDefinition = "TEXT")
    private String researchSources; // JSON string array of web sources

    @Column(name = "historical_context", columnDefinition = "TEXT")
    private String historicalContext; // JSON object with historical insights (past trades, agent context)

    @Column(name = "trade_count")
    private Integer tradeCount = 0;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "market_conditions", columnDefinition = "TEXT")
    private String marketConditions; // JSON string with market status

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    // Constructor for starting a run
    public AgentRun(String agentName, String runType, String marketConditions) {
        this.agentName = agentName;
        this.runType = runType;
        this.startTime = Instant.now();
        this.outcome = "IN_PROGRESS";
        this.marketConditions = marketConditions;
    }

    // Business methods
    public void markAsTraded(String summary, String fullReasoning, String researchSources, String historicalContext, Integer tradeCount) {
        this.endTime = Instant.now();
        this.outcome = "TRADED";
        this.summary = summary;
        this.fullReasoning = fullReasoning;
        this.researchSources = researchSources;
        this.historicalContext = historicalContext;
        this.tradeCount = tradeCount;
    }

    public void markAsNoTrade(String summary, String fullReasoning, String researchSources, String historicalContext) {
        this.endTime = Instant.now();
        this.outcome = "NO_TRADE";
        this.summary = summary;
        this.fullReasoning = fullReasoning;
        this.researchSources = researchSources;
        this.historicalContext = historicalContext;
        this.tradeCount = 0;
    }

    public void markAsError(String errorMessage) {
        this.endTime = Instant.now();
        this.outcome = "ERROR";
        this.errorMessage = errorMessage;
    }

    public boolean isCompleted() {
        return this.endTime != null;
    }

    public Long getDurationSeconds() {
        if (this.endTime == null) {
            return null;
        }
        return this.endTime.getEpochSecond() - this.startTime.getEpochSecond();
    }
}
