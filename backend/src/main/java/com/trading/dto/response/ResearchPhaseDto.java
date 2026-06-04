package com.trading.dto.response;

import com.trading.dto.UsageMetricsDto;
import com.trading.dto.jsonb.SourceDto;
import com.trading.dto.jsonb.ToolCallDto;
import com.trading.entity.ResearchPhase;
import java.time.Instant;
import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

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
    private UsageMetricsDto metrics;
    private String systemPrompt;
    private String taskPrompt;
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
        dto.setMetrics(UsageMetricsDto.fromEntity(researchPhase.getMetrics()));
        dto.setSystemPrompt(researchPhase.getSystemPrompt());
        dto.setTaskPrompt(researchPhase.getTaskPrompt());
        dto.setCreatedAt(researchPhase.getCreatedAt());
        return dto;
    }
}
