package com.trading.dto.jsonb;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO for structured reasoning in decision phase.
 * Per design doc Lines 618-637: 5-field structured reasoning.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ReasoningDto {
    
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
    private String researchSummary;
    
    /**
     * Evaluation of candidates against each other.
     * Example: "Evaluated JPM vs BAC. JPM has better P/E (12 vs 15) and recent earnings momentum."
     */
    private String candidateEvaluation;
    
    /**
     * Final decision rationale.
     * Example: "Choosing JPM because strong fundamentals + proven winner in my portfolio + fits value strategy."
     */
    private String finalRationale;
}

