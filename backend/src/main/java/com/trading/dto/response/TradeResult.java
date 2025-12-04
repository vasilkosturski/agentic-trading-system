package com.trading.dto.response;

import com.trading.entity.TransactionType;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * Result of a trade execution (buy/sell).
 * Provides structured data about the completed trade including transaction details,
 * updated account balance, and a formatted message for display.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TradeResult {
    /**
     * ID of the created transaction (for tracking/audit)
     */
    private Long transactionId;

    /**
     * Stock symbol that was traded
     */
    private String symbol;

    /**
     * Number of shares traded
     */
    private Integer quantity;

    /**
     * Price per share at execution
     */
    private Double price;

    /**
     * Total cost/proceeds (price * quantity)
     */
    private Double totalAmount;

    /**
     * Account balance after trade execution
     */
    private Double newBalance;

    /**
     * Type of transaction (BUY or SELL)
     */
    private TransactionType transactionType;

    /**
     * When the trade was executed
     */
    private Instant timestamp;

    /**
     * Human-readable message describing the trade
     * (for backward compatibility and display)
     */
    private String message;

    /**
     * Helper method to create a formatted message
     */
    public static String formatMessage(TransactionType type, Integer quantity, String symbol, Double price) {
        return String.format("Successfully %s %d shares of %s at $%.2f each",
            type.name().toLowerCase(),
            quantity,
            symbol,
            price);
    }
}
