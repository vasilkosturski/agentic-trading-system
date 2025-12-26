package com.trading.dto.request;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request DTO for ending an agent run.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class EndRunRequest {
    @NotNull(message = "Run ID is required")
    private Long runId;

    private String summary;

    private String fullReasoning;

    private String researchSources;

    private String historicalContext;

    @PositiveOrZero(message = "Trade count must be zero or positive")
    private Integer tradeCount;
}
