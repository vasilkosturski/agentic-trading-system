package com.trading.dto.response;

import com.trading.dto.jsonb.ToolCallDto;
import com.trading.dto.jsonb.ReasoningDto;
import com.trading.dto.jsonb.SourceDto;
import com.trading.entity.DecisionPhase;
import com.trading.enums.TradeDecision;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

/**
 * DTO for decision phase data.
 * Per design.md: Decision phase includes decision, reasoning, sources, tool calls, and latency metrics.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class DecisionPhaseDto {
    private Long decisionId;
    private Long runId;
    private TradeDecision decision;
    private String symbol;
    private Integer quantity;
    private ReasoningDto reasoning;
    private List<SourceDto> sources;
    private List<ToolCallDto> toolCalls;
    private Long latencyMs;
    private Integer tokensUsed;
    private Integer inputTokens;
    private Integer outputTokens;
    private Integer numTurns;
    private Integer cachedTokens;
    private Integer reasoningTokens;
    private BigDecimal costUsd;
    private String modelName;
    private Instant createdAt;

    /**
     * Factory method to create DTO from DecisionPhase entity.
     */
    public static DecisionPhaseDto fromEntity(DecisionPhase decisionPhase) {
        DecisionPhaseDto dto = new DecisionPhaseDto();
        dto.setDecisionId(decisionPhase.getId());
        dto.setRunId(decisionPhase.getRun().getId());
        dto.setDecision(decisionPhase.getDecision());
        dto.setSymbol(decisionPhase.getSymbol());
        dto.setQuantity(decisionPhase.getQuantity());
        dto.setReasoning(decisionPhase.getReasoning());
        dto.setSources(decisionPhase.getSources());
        dto.setToolCalls(decisionPhase.getToolCalls());
        dto.setLatencyMs(decisionPhase.getLatencyMs());
        dto.setTokensUsed(decisionPhase.getTokensUsed());
        dto.setInputTokens(decisionPhase.getInputTokens());
        dto.setOutputTokens(decisionPhase.getOutputTokens());
        dto.setNumTurns(decisionPhase.getNumTurns());
        dto.setCachedTokens(decisionPhase.getCachedTokens());
        dto.setReasoningTokens(decisionPhase.getReasoningTokens());
        dto.setCostUsd(decisionPhase.getCostUsd());
        dto.setModelName(decisionPhase.getModelName());
        dto.setCreatedAt(decisionPhase.getCreatedAt());
        return dto;
    }
}
