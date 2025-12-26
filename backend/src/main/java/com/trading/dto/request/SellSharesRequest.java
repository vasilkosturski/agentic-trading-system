package com.trading.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request DTO for selling shares.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class SellSharesRequest {
    @NotNull(message = "Agent ID is required")
    private Long agentId;

    @NotBlank(message = "Stock symbol is required")
    private String symbol;

    @NotNull(message = "Quantity is required")
    @Positive(message = "Quantity must be positive")
    private Integer quantity;

    @NotNull(message = "Run ID is required - every transaction must be linked to an agent run")
    private Long runId;
}
