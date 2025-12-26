package com.trading.dto.request;

import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request DTO for getting agent account balance.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class GetBalanceRequest {
    @NotNull(message = "Agent ID is required")
    private Long agentId;
}
