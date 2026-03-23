package com.trading.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.math.BigDecimal;

/**
 * Embeddable usage metrics for LLM token tracking.
 * Maps to existing flat columns in research_phases and decision_phases tables.
 * No schema migration needed — column names match exactly.
 */
@Embeddable
@Getter
@Setter
@NoArgsConstructor
public class UsageMetrics {

    @Column(name = "tokens_used")
    private Integer tokensUsed;

    @Column(name = "input_tokens")
    private Integer inputTokens;

    @Column(name = "output_tokens")
    private Integer outputTokens;

    @Column(name = "num_turns")
    private Integer numTurns;

    @Column(name = "cached_tokens")
    private Integer cachedTokens;

    @Column(name = "reasoning_tokens")
    private Integer reasoningTokens;

    @Column(name = "model_name", length = 50)
    private String modelName;

    @Column(name = "cost_usd", precision = 10, scale = 6)
    private BigDecimal costUsd;
}
