package com.trading.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class TradeDetailResponse {
    private TradeInfo trade;
    private String fullReasoning;
    private String researchSources; // JSON string
    private String agentContext; // JSON string
    private List<RelatedTrade> relatedTrades;
    private Long runId; // ID of the agent run that created this trade (null if not part of a run)
    private String runSummary; // Summary of the run that created this trade
    private List<RunDetailDto.ReasoningStepInfo> reasoningSteps; // Agent reasoning timeline

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TradeInfo {
        private Long id;
        private String agentName;
        private String type;
        private String symbol;
        private Integer quantity;
        private Double price;
        private Double totalValue;
        private Instant timestamp;
        private String rationale;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RelatedTrade {
        private Long id;
        private String type;
        private Integer quantity;
        private Double price;
        private Instant timestamp;
    }
}
