package com.trading.dto.response;

import java.time.LocalDateTime;
import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Account report DTO returned by MCP resource endpoint.
 * Used by Python agents to get account summary for AI prompts.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AccountReportDto {
    private String agentName;
    private Double balance;
    private Double holdingsValue;
    private Double totalPortfolioValue;
    private Double initialBalance;
    private Double totalProfitLoss;
    private Double profitLossPercent;
    private LocalDateTime lastUpdated;
    private Integer holdingsCount;
    private Long transactionCount;
    private List<HoldingDto> holdings;
}
