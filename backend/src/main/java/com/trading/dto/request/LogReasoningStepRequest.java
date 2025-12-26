package com.trading.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request DTO for logging a reasoning step during an agent run.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class LogReasoningStepRequest {
    @NotBlank(message = "Step type is required")
    private String stepType;

    @NotBlank(message = "Step description is required")
    private String stepDescription;

    private String reasoningText;

    @NotBlank(message = "Timestamp is required")
    private String timestamp;

    @NotNull(message = "Sequence number is required")
    @PositiveOrZero(message = "Sequence number must be zero or positive")
    private Integer sequenceNumber;
}
