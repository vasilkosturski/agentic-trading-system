package com.trading.dto.response;

import com.trading.dto.UsageMetricsDto;
import com.trading.dto.jsonb.ReasoningDto;
import com.trading.dto.jsonb.SourceDto;
import com.trading.dto.jsonb.ToolCallDto;
import com.trading.entity.DecisionPhase;
import com.trading.enums.TradeDecision;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

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
    private String systemPrompt;
    private String taskPrompt;
    private Integer guardrailAttempts;
    private List<String> guardrailIssues;
    private String guardrailOutcome;
    private Map<String, Object> guardrailFailedOutput;
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
        dto.setSystemPrompt(decisionPhase.getSystemPrompt());
        dto.setTaskPrompt(decisionPhase.getTaskPrompt());
        dto.setGuardrailAttempts(decisionPhase.getGuardrailAttempts());
        dto.setGuardrailIssues(decisionPhase.getGuardrailIssues());
        dto.setGuardrailOutcome(decisionPhase.getGuardrailOutcome());
        dto.setGuardrailFailedOutput(decisionPhase.getGuardrailFailedOutput());
        dto.setCreatedAt(decisionPhase.getCreatedAt());
        return dto;
    }
}
