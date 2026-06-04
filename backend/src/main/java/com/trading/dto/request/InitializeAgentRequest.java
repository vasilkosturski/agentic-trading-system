package com.trading.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class InitializeAgentRequest {

    /**
     * Agent name (required) - e.g., "Warren", "George", "Ray", "Cathie"
     */
    @NotBlank(message = "name is required")
    private String name;

    /**
     * Initial cash balance (required)
     */
    @NotNull(message = "initialBalance is required")
    @Positive(message = "initialBalance must be positive")
    private Double initialBalance;
}
