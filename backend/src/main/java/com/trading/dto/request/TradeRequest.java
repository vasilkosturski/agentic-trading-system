package com.trading.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Unified request DTO for trading operations (buy/sell).
 * Used with REST endpoint POST /api/accounts/{agentId}/trades
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TradeRequest {
    @NotBlank(message = "Stock symbol is required")
    private String symbol;

    @NotNull(message = "Quantity is required")
    @Positive(message = "Quantity must be positive")
    private Integer quantity;

    @NotNull(message = "Trade type is required (BUY or SELL)")
    private TradeType type;

    @NotNull(message = "Run ID is required - every transaction must be linked to an agent run")
    private Long runId;
}
