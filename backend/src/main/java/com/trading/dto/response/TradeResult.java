package com.trading.dto.response;

/**
 * Result of a trade execution (buy/sell).
 * Contains only the essential data the LLM needs for decision-making:
 * - What was traded (symbol, quantity, price) for confirmation
 * - Updated balance for next trade calculation
 *
 * Removed fields:
 * - transactionId: Internal DB detail, not useful for LLM
 * - totalAmount: Redundant (price * quantity)
 * - transactionType: LLM knows which function it called
 * - timestamp: Not needed for trade decisions
 * - message: Redundant formatted string of structured data
 */
public record TradeResult(
    String symbol,
    Integer quantity,
    Double price,
    Double newBalance
) {}
