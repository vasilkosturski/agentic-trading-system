package com.trading.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

/**
 * DTO for recent trade display in the frontend
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RecentTradeDto {
    private String agentName;
    private String transactionType; // BUY or SELL
    private String symbol;
    private Integer quantity;
    private Double price;
    private Double totalAmount;
    private LocalDateTime timestamp;
    private String rationale;
}