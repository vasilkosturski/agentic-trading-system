package com.trading.dto.response;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class AgentDetailDto {
    private Long id;
    private String name;
    private String strategy;
    private Double initialCapital;
    private PortfolioInfo portfolio;
    private List<RunSummary> recentRuns;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PortfolioInfo {
        private Double cashBalance;
        private Map<String, Integer> holdings;
        private Double totalValue;
        private Double totalReturn;
        private Double totalReturnPercent;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RunSummary {
        private Long id;
        private String runType;
        private String outcome;
        private String timestamp;
        private Integer tradeCount;
        private String summary;
    }
}
