package com.trading.dto.response;

import com.trading.entity.AccountTransaction;
import com.trading.entity.AgentRun;
import com.trading.entity.AgentToolCall;
import com.trading.entity.AgentReasoningStep;
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
    private Long agentId;
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
    private List<ToolCallInfo> toolCalls; // List of tool calls during this run
    private List<ReasoningStepInfo> reasoningSteps; // List of reasoning steps during this run

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
                    transaction.getTransactionType().name(),  // Convert enum to string
                    transaction.getTotalAmount()
            );
        }
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ToolCallInfo {
        private Long id;
        private String toolName;
        private String inputParams; // JSON string
        private String outputResult; // JSON string or text
        private Instant timestamp;
        private Long durationMs;
        private Boolean success;
        private String errorMessage;
        private Integer sequenceNumber;

        public static ToolCallInfo fromEntity(AgentToolCall toolCall) {
            return new ToolCallInfo(
                    toolCall.getId(),
                    toolCall.getToolName(),
                    toolCall.getInputParams(),
                    toolCall.getOutputResult(),
                    toolCall.getTimestamp(),
                    toolCall.getDurationMs(),
                    toolCall.getSuccess(),
                    toolCall.getErrorMessage(),
                    toolCall.getSequenceNumber()
            );
        }
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ReasoningStepInfo {
        private Long id;
        private String stepType;
        private String stepDescription;
        private String reasoningText;
        private Instant timestamp;
        private Integer sequenceNumber;

        public static ReasoningStepInfo fromEntity(AgentReasoningStep step) {
            return new ReasoningStepInfo(
                    step.getId(),
                    step.getStepType(),
                    step.getStepDescription(),
                    step.getReasoningText(),
                    step.getTimestamp(),
                    step.getSequenceNumber()
            );
        }
    }

    // Factory method to create from AgentRun entity and transactions list
    public static RunDetailDto fromEntity(AgentRun run, List<AccountTransaction> transactions, Long agentId) {
        List<TradeInfo> trades = transactions.stream()
                .map(TradeInfo::fromEntity)
                .collect(Collectors.toList());

        return new RunDetailDto(
                run.getId(),
                agentId,
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
                trades,
                null, // toolCalls - will be populated by controller
                null  // reasoningSteps - will be populated by controller
        );
    }

    // Factory method with tool calls and reasoning steps
    public static RunDetailDto fromEntity(AgentRun run, List<AccountTransaction> transactions,
                                         List<AgentToolCall> toolCalls, List<AgentReasoningStep> reasoningSteps,
                                         Long agentId) {
        List<TradeInfo> trades = transactions.stream()
                .map(TradeInfo::fromEntity)
                .collect(Collectors.toList());

        List<ToolCallInfo> toolCallInfos = toolCalls.stream()
                .map(ToolCallInfo::fromEntity)
                .collect(Collectors.toList());

        List<ReasoningStepInfo> reasoningStepInfos = reasoningSteps.stream()
                .map(ReasoningStepInfo::fromEntity)
                .collect(Collectors.toList());

        return new RunDetailDto(
                run.getId(),
                agentId,
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
                trades,
                toolCallInfos,
                reasoningStepInfos
        );
    }
}
