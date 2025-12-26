package com.trading.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request DTO for marking a run as error.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class MarkRunAsErrorRequest {
    @NotNull(message = "Run ID is required")
    private Long runId;

    @NotBlank(message = "Error message is required")
    private String errorMessage;
}
