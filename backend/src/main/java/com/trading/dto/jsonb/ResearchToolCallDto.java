package com.trading.dto.jsonb;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO for tool calls in research phase.
 * Per design doc Line 898: [{tool, duration_ms}] - simpler structure, no params.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ResearchToolCallDto {
    
    /**
     * Tool name (e.g., "query_holdings", "brave_search")
     */
    private String tool;
    
    /**
     * Duration in milliseconds
     */
    private Long durationMs;
}

