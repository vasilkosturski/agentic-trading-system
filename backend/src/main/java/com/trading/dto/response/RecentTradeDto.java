package com.trading.dto.response;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.Instant;

/**
 * DTO for recent trade display in the frontend
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RecentTradeDto {
    private Long id;
    private String agentName;
    private String transactionType; // BUY or SELL
    private String symbol;
    private Integer quantity;
    private Double price;
    private Double totalAmount;
    private Instant timestamp;
    private String rationale;
}