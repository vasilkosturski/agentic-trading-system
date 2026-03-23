package com.trading.dto;

import com.trading.entity.UsageMetrics;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

/**
 * Shared DTO for LLM usage metrics.
 * Used by both request and response phase DTOs.
 * Maps to/from the @Embeddable UsageMetrics entity.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UsageMetricsDto {
    private Integer tokensUsed;
    private Integer inputTokens;
    private Integer outputTokens;
    private Integer numTurns;
    private Integer cachedTokens;
    private Integer reasoningTokens;
    private BigDecimal costUsd;
    private String modelName;

    /**
     * Factory method to create DTO from @Embeddable entity.
     */
    public static UsageMetricsDto fromEntity(UsageMetrics metrics) {
        if (metrics == null) {
            return null;
        }
        UsageMetricsDto dto = new UsageMetricsDto();
        dto.setTokensUsed(metrics.getTokensUsed());
        dto.setInputTokens(metrics.getInputTokens());
        dto.setOutputTokens(metrics.getOutputTokens());
        dto.setNumTurns(metrics.getNumTurns());
        dto.setCachedTokens(metrics.getCachedTokens());
        dto.setReasoningTokens(metrics.getReasoningTokens());
        dto.setCostUsd(metrics.getCostUsd());
        dto.setModelName(metrics.getModelName());
        return dto;
    }

    /**
     * Convert DTO to @Embeddable entity for persistence.
     */
    public UsageMetrics toEntity() {
        UsageMetrics metrics = new UsageMetrics();
        metrics.setTokensUsed(this.tokensUsed);
        metrics.setInputTokens(this.inputTokens);
        metrics.setOutputTokens(this.outputTokens);
        metrics.setNumTurns(this.numTurns);
        metrics.setCachedTokens(this.cachedTokens);
        metrics.setReasoningTokens(this.reasoningTokens);
        metrics.setCostUsd(this.costUsd);
        metrics.setModelName(this.modelName);
        return metrics;
    }
}
