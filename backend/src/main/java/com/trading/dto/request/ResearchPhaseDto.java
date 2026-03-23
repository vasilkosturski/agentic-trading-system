package com.trading.dto.request;

import com.trading.dto.jsonb.ToolCallDto;
import com.trading.dto.jsonb.SourceDto;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;

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

    // Token usage metrics from SDK
    private Integer tokensUsed;
    private Integer inputTokens;
    private Integer outputTokens;
    private Integer numTurns;
    private Integer cachedTokens;
    private Integer reasoningTokens;
    private BigDecimal costUsd;
    private String modelName;
}
