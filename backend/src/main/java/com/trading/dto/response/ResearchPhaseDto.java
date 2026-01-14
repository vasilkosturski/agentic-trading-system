package com.trading.dto.response;

import com.trading.dto.jsonb.ResearchToolCallDto;
import com.trading.dto.jsonb.SourceDto;
import com.trading.entity.ResearchPhase;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

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
    private List<ResearchToolCallDto> toolCalls;
    private Long latencyMs;
    private Instant createdAt;

    /**
     * Factory method to create DTO from ResearchPhase entity.
     */
    public static ResearchPhaseDto fromEntity(ResearchPhase researchPhase) {
        return new ResearchPhaseDto(
            researchPhase.getId(),
            researchPhase.getRun().getId(),
            researchPhase.getCandidates(),
            researchPhase.getSources(),
            researchPhase.getResearchNotes(),
            researchPhase.getToolCalls(),
            researchPhase.getLatencyMs(),
            researchPhase.getCreatedAt()
        );
    }
}
