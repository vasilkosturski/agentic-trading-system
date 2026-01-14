package com.trading.dto.request;

import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request to create a new trading run.
 * Per design.md: POST /api/runs - Creates run with status=IN_PROGRESS, phase=INITIALIZING.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CreateRunRequest {

    @NotNull(message = "Agent ID is required")
    private Long agentId;
}
