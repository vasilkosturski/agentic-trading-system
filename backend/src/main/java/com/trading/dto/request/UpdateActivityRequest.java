package com.trading.dto.request;

import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request DTO for updating agent activity timestamp.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UpdateActivityRequest {
    @NotNull(message = "Agent ID is required")
    private Long agentId;
}
