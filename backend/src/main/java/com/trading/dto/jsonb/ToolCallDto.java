package com.trading.dto.jsonb;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.Map;

/**
 * Unified DTO for tool calls in all phases (research, decision).
 *
 * Fields:
 * - tool: Tool name (e.g., "query_holdings", "brave_search", "get_symbol_trade_history")
 * - params: Optional tool parameters (e.g., {"symbol": "JPM"})
 * - durationMs: Duration in milliseconds
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ToolCallDto {

    /**
     * Tool name (e.g., "query_holdings", "brave_search")
     */
    private String tool;

    /**
     * Tool parameters - optional, may be null for simple tool calls
     */
    private Map<String, Object> params;

    /**
     * Duration in milliseconds
     */
    private Long durationMs;

    /**
     * Convenience constructor without params (for simple tool calls).
     */
    public ToolCallDto(String tool, Long durationMs) {
        this.tool = tool;
        this.params = null;
        this.durationMs = durationMs;
    }
}
