package com.trading.dto.response;

import com.trading.entity.ExecutionPhase;
import com.trading.enums.PhaseStatus;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * DTO for execution phase data.
 * Per design.md: Execution phase tracks trade execution status.
 * May be null for HOLD decisions.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ExecutionPhaseDto {
    private Long executionId;
    private Long runId;
    private Long tradeId;  // may be null
    private PhaseStatus status;
    private String errorDetails;  // may be null
    private Instant createdAt;

    /**
     * Factory method to create DTO from ExecutionPhase entity.
     */
    public static ExecutionPhaseDto fromEntity(ExecutionPhase executionPhase) {
        return new ExecutionPhaseDto(
            executionPhase.getId(),
            executionPhase.getRun().getId(),
            executionPhase.getTrade() != null ? executionPhase.getTrade().getId() : null,
            executionPhase.getStatus(),
            executionPhase.getErrorDetails(),
            executionPhase.getCreatedAt()
        );
    }
}
