package com.trading.dto.response;

import com.trading.entity.AccountTransaction;
import com.trading.entity.ExecutionPhase;
import com.trading.enums.PhaseStatus;
import java.time.Instant;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

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
    private Long tradeId; // may be null
    private PhaseStatus status;
    private String errorDetails; // may be null
    private TradeDetailDto trade; // nested trade details, may be null
    private Instant createdAt;

    /**
     * Nested DTO for trade details from AccountTransaction.
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TradeDetailDto {
        private String symbol;
        private String transactionType;
        private Integer quantity;
        private Double price;
        private Double totalAmount;

        public static TradeDetailDto fromEntity(AccountTransaction tx) {
            TradeDetailDto dto = new TradeDetailDto();
            dto.setSymbol(tx.getSymbol());
            dto.setTransactionType(tx.getTransactionType().name());
            dto.setQuantity(tx.getQuantity());
            dto.setPrice(tx.getPrice());
            dto.setTotalAmount(tx.getTotalAmount());
            return dto;
        }
    }

    /**
     * Factory method to create DTO from ExecutionPhase entity.
     */
    public static ExecutionPhaseDto fromEntity(ExecutionPhase executionPhase) {
        ExecutionPhaseDto dto = new ExecutionPhaseDto();
        dto.setExecutionId(executionPhase.getId());
        dto.setRunId(executionPhase.getRun().getId());
        dto.setStatus(executionPhase.getStatus());
        dto.setErrorDetails(executionPhase.getErrorDetails());
        dto.setCreatedAt(executionPhase.getCreatedAt());

        AccountTransaction tx = executionPhase.getTrade();
        if (tx != null) {
            dto.setTradeId(tx.getId());
            dto.setTrade(TradeDetailDto.fromEntity(tx));
        }

        return dto;
    }
}
