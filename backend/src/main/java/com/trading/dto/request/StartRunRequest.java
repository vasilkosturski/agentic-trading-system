package com.trading.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request DTO for starting a new agent run.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class StartRunRequest {
    @NotNull(message = "Agent ID is required")
    private Long agentId;

    @NotBlank(message = "Run type is required")
    private String runType;

    private String marketConditions;
}
