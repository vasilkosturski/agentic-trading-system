package com.trading.dto.response;

/**
 * Result of a trade execution (buy/sell).
 * Contains essential data for trade confirmation and audit trail:
 * - tradeId: Links trade to transaction record for audit trail
 * - What was traded (symbol, quantity, price) for confirmation
 * - Updated balance for next trade calculation
 *
 * Removed fields:
 * - totalAmount: Redundant (price * quantity)
 * - transactionType: LLM knows which function it called
 * - timestamp: Not needed for trade decisions
 * - message: Redundant formatted string of structured data
 */
public record TradeResult(
    Long tradeId,
    String symbol,
    Integer quantity,
    Double price,
    Double newBalance
) {}
