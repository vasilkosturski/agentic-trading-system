package com.trading.dto.jsonb;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Map;

/**
 * Unified DTO for tool calls in all phases (research, decision).
 *
 * Fields:
 * - tool: Tool name (e.g., "query_holdings", "brave_search", "get_symbol_trade_history")
 * - params: Optional tool parameters (e.g., {"symbol": "JPM"})
 * - error: Whether the tool call returned an error (null for legacy records)
 * - errorMessage: Truncated error output (null for successful calls)
 *
 * Implements {@link Serializable} because Hibernate 6.6 (Spring Boot 3.5) requires
 * JSONB-mapped entity attributes to be Serializable for the default JsonSerializer
 * dirty-checking path.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class ToolCallDto implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * Tool name (e.g., "query_holdings", "brave_search")
     */
    private String tool;

    /**
     * Tool parameters - optional, may be null for simple tool calls
     */
    private Map<String, Object> params;

    /**
     * Whether the tool call returned an error.
     * Null for tool calls from before this field was added (backward-compatible).
     */
    private Boolean error;

    /**
     * Truncated error message (max 500 chars) when error is true.
     * Null for successful tool calls.
     */
    private String errorMessage;

    /**
     * Convenience constructor for simple tool calls.
     */
    public ToolCallDto(String tool) {
        this.tool = tool;
        this.params = null;
        this.error = null;
        this.errorMessage = null;
    }
}
