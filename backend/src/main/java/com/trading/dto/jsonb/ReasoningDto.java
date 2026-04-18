package com.trading.dto.jsonb;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO for structured reasoning in decision phase.
 * 4-field structured reasoning: rationale narrative, portfolio context,
 * historical context, research summary.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ReasoningDto {

    /**
     * Brief 1-2 sentence narrative explaining the decision.
     * Example: "Buying JPM because strong earnings beat expectations and value metrics are compelling."
     */
    private String rationale;

    /**
     * Current portfolio state context.
     * Example: "I currently hold 8/10 positions with $5K available cash. Portfolio at $105K (+5% total)."
     */
    private String portfolioContext;

    /**
     * Historical trading context for this symbol.
     * Example: "Checked JPM trade history: bought at $145, sold at $155 last month for +$1K profit."
     */
    private String historicalContext;

    /**
     * Summary of Market Analyst research.
     * Example: "Market Analyst found 5 value stocks. Did additional research on JPM earnings."
     */
    private String researchContext;
}

