package com.trading.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request DTO for logging a tool call during an agent run.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class LogToolCallRequest {
    @NotBlank(message = "Tool name is required")
    private String toolName;

    private String inputParams;

    private String outputResult;

    @NotBlank(message = "Timestamp is required")
    private String timestamp;

    @PositiveOrZero(message = "Duration must be zero or positive")
    private Long durationMs;

    private Boolean success;

    private String errorMessage;

    @NotNull(message = "Sequence number is required")
    @PositiveOrZero(message = "Sequence number must be zero or positive")
    private Integer sequenceNumber;
}
