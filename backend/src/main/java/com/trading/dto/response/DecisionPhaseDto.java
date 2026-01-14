package com.trading.dto.response;

import com.trading.dto.jsonb.DecisionToolCallDto;
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
    private List<DecisionToolCallDto> toolCalls;
    private Long latencyMs;
    private Instant createdAt;

    /**
     * Factory method to create DTO from DecisionPhase entity.
     */
    public static DecisionPhaseDto fromEntity(DecisionPhase decisionPhase) {
        return new DecisionPhaseDto(
            decisionPhase.getId(),
            decisionPhase.getRun().getId(),
            decisionPhase.getDecision(),
            decisionPhase.getSymbol(),
            decisionPhase.getQuantity(),
            decisionPhase.getReasoning(),
            decisionPhase.getSources(),
            decisionPhase.getToolCalls(),
            decisionPhase.getLatencyMs(),
            decisionPhase.getCreatedAt()
        );
    }
}
