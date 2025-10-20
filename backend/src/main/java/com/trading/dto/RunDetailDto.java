package com.trading.dto;

import com.trading.entity.AccountTransaction;
import com.trading.entity.AgentRun;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;
import java.util.stream.Collectors;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class RunDetailDto {
    private Long id;
    private String agentName;
    private String runType;
    private Instant startTime;
    private Instant endTime;
    private String outcome;
    private String fullReasoning;
    private String researchSources; // JSON string
    private String summary;
    private Integer tradeCount;
    private String errorMessage;
    private String agentContext; // JSON string
    private String marketConditions; // JSON string
    private Long durationSeconds;
    private List<TradeInfo> trades; // List of trades from this run

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TradeInfo {
        private Long id;
        private String symbol;
        private Integer quantity;
        private Double price;
        private Instant timestamp;
        private String rationale;
        private String transactionType; // BUY or SELL
        private Double totalAmount;

        public static TradeInfo fromEntity(AccountTransaction transaction) {
            return new TradeInfo(
                    transaction.getId(),
                    transaction.getSymbol(),
                    transaction.getQuantity(),
                    transaction.getPrice(),
                    transaction.getTimestamp(),
                    transaction.getRationale(),
                    transaction.getTransactionType(),
                    transaction.getTotalAmount()
            );
        }
    }

    // Factory method to create from AgentRun entity and transactions list
    public static RunDetailDto fromEntity(AgentRun run, List<AccountTransaction> transactions) {
        List<TradeInfo> trades = transactions.stream()
                .map(TradeInfo::fromEntity)
                .collect(Collectors.toList());

        return new RunDetailDto(
                run.getId(),
                run.getAgentName(),
                run.getRunType(),
                run.getStartTime(),
                run.getEndTime(),
                run.getOutcome(),
                run.getFullReasoning(),
                run.getResearchSources(),
                run.getSummary(),
                run.getTradeCount(),
                run.getErrorMessage(),
                run.getAgentContext(),
                run.getMarketConditions(),
                run.getDurationSeconds(),
                trades
        );
    }
}
