package com.trading.dto.response;

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
    private String summary; // Simple summary (brief explanation)
    private String fullReasoning; // Full detailed reasoning
    private String researchSources; // JSON string array of web sources
    private String historicalContext; // JSON object with historical insights (past trades, agent context)
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
