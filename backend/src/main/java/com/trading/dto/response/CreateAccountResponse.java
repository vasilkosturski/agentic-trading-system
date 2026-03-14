package com.trading.dto.response;

/**
 * Response for account creation (POST /api/accounts).
 * Fields match the JSON contract consumed by Python agents.
 */
public record CreateAccountResponse(
    Long id,
    Long accountId,
    String name,
    Double balance
) {}
