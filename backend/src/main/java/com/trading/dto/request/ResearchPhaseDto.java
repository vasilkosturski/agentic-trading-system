package com.trading.dto.request;

import com.trading.dto.UsageMetricsDto;
import com.trading.dto.jsonb.SourceDto;
import com.trading.dto.jsonb.ToolCallDto;
import com.trading.entity.ResearchPhase;
import com.trading.entity.TradingRun;
import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Research phase data for CompleteRunRequest.
 * Contains all data collected during the RESEARCHING phase.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ResearchPhaseDto {

    /**
     * Stock symbols researched (e.g., ["JPM", "BAC", "WFC"])
     */
    private List<String> candidates;

    /**
     * Web sources and system context used in research.
     */
    private List<SourceDto> sources;

    /**
     * Agent's research notes (markdown format)
     */
    private String notes;

    /**
     * Tool calls made during research phase (Brave Search, Memory, etc.)
     */
    private List<ToolCallDto> toolCalls;

    /**
     * Research phase execution time in milliseconds.
     */
    private Long latencyMs;

    /**
     * Token usage metrics from SDK (nested object).
     */
    private UsageMetricsDto metrics;

    private String systemPrompt;

    private String taskPrompt;

    /**
     * Convert this request DTO into a {@link ResearchPhase} entity attached to
     * the given run. Mirrors the per-DTO mapping convention already used by
     * {@link UsageMetricsDto#toEntity()}.
     */
    public ResearchPhase toEntity(TradingRun run) {
        ResearchPhase phase = new ResearchPhase(run);
        phase.setCandidates(candidates);
        phase.setSources(sources);
        phase.setResearchNotes(notes);
        phase.setToolCalls(toolCalls);
        phase.setLatencyMs(latencyMs);
        if (metrics != null) {
            phase.setMetrics(metrics.toEntity());
        }
        phase.setSystemPrompt(systemPrompt);
        phase.setTaskPrompt(taskPrompt);
        return phase;
    }
}
