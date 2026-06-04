package com.trading.dto.response;

import java.time.Instant;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class HoldingDto {
    // Original fields (persisted from entity)
    private String symbol;
    private Integer quantity;
    private Double averagePrice; // Cost basis per share

    // New fields (calculated from live market prices)
    private Double currentPrice; // Live market price per share
    private Double marketValue; // quantity × currentPrice (current market value)
    private Double costBasis; // quantity × averagePrice (total cost at purchase)
    private Double unrealizedPnl; // marketValue - costBasis (profit/loss in dollars)
    private Double gainLossPercent; // (unrealizedPnl / costBasis) × 100 (percentage gain/loss)
    private Boolean cached; // Whether currentPrice came from cache vs real-time
    private Instant priceTimestamp; // When the currentPrice was fetched

    /**
     * Constructor for backward compatibility with original 3-field version.
     * Used when populating prices/P&L is not needed.
     */
    public HoldingDto(String symbol, Integer quantity, Double averagePrice) {
        this.symbol = symbol;
        this.quantity = quantity;
        this.averagePrice = averagePrice;
    }
}
