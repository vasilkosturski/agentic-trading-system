package com.trading.dto.jsonb;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.Map;

/**
 * DTO for tool calls in decision phase.
 * Per design doc Line 934: [{tool, params, duration_ms}] - includes params for detailed tracking.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class DecisionToolCallDto {
    
    /**
     * Tool name (e.g., "get_symbol_trade_history", "brave_search")
     */
    private String tool;
    
    /**
     * Tool parameters (e.g., {"symbol": "JPM"})
     */
    private Map<String, Object> params;
    
    /**
     * Duration in milliseconds
     */
    private Long durationMs;
}

