package com.trading.dto.response;

import com.trading.dto.UsageMetricsDto;
import com.trading.dto.jsonb.ToolCallDto;
import com.trading.dto.jsonb.ReasoningDto;
import com.trading.dto.jsonb.SourceDto;
import com.trading.entity.DecisionPhase;
import com.trading.enums.TradeDecision;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

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
    private UsageMetricsDto metrics;
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
        dto.setMetrics(UsageMetricsDto.fromEntity(decisionPhase.getMetrics()));
        dto.setCreatedAt(decisionPhase.getCreatedAt());
        return dto;
    }
}
