package com.trading.dto.response;

import com.trading.dto.jsonb.ToolCallDto;
import com.trading.dto.jsonb.SourceDto;
import com.trading.entity.ResearchPhase;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

/**
 * DTO for research phase data.
 * Per design.md: Research phase includes candidates, sources, tool calls, and latency metrics.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ResearchPhaseDto {
    private Long researchId;
    private Long runId;
    private List<String> candidates;
    private List<SourceDto> sources;
    private String researchNotes;
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
     * Factory method to create DTO from ResearchPhase entity.
     */
    public static ResearchPhaseDto fromEntity(ResearchPhase researchPhase) {
        ResearchPhaseDto dto = new ResearchPhaseDto();
        dto.setResearchId(researchPhase.getId());
        dto.setRunId(researchPhase.getRun().getId());
        dto.setCandidates(researchPhase.getCandidates());
        dto.setSources(researchPhase.getSources());
        dto.setResearchNotes(researchPhase.getResearchNotes());
        dto.setToolCalls(researchPhase.getToolCalls());
        dto.setLatencyMs(researchPhase.getLatencyMs());
        dto.setTokensUsed(researchPhase.getTokensUsed());
        dto.setInputTokens(researchPhase.getInputTokens());
        dto.setOutputTokens(researchPhase.getOutputTokens());
        dto.setNumTurns(researchPhase.getNumTurns());
        dto.setCachedTokens(researchPhase.getCachedTokens());
        dto.setReasoningTokens(researchPhase.getReasoningTokens());
        dto.setCostUsd(researchPhase.getCostUsd());
        dto.setModelName(researchPhase.getModelName());
        dto.setCreatedAt(researchPhase.getCreatedAt());
        return dto;
    }
}
