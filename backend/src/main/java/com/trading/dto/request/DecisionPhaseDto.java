package com.trading.dto.request;

import com.trading.dto.jsonb.ToolCallDto;
import com.trading.dto.jsonb.ReasoningDto;
import com.trading.dto.jsonb.SourceDto;
import com.trading.enums.TradeDecision;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * Decision phase data for CompleteRunRequest.
 * Contains all data collected during the DECIDING phase.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class DecisionPhaseDto {

    @NotNull(message = "Decision is required (BUY, SELL, or HOLD)")
    private TradeDecision decision;

    /**
     * Symbol to trade (null for HOLD)
     */
    private String symbol;

    /**
     * Quantity to trade (null for HOLD)
     */
    private Integer quantity;

    /**
     * Structured reasoning for the decision.
     */
    @Valid
    private ReasoningDto reasoning;

    /**
     * Sources used in decision phase.
     */
    private List<SourceDto> sources;

    /**
     * Tool calls made during decision phase.
     */
    private List<ToolCallDto> toolCalls;

    /**
     * Decision phase execution time in milliseconds.
     */
    private Long latencyMs;

    /**
     * Validate decision consistency.
     * BUY/SELL decisions must have symbol and quantity.
     */
    public void validate() {
        if (decision == TradeDecision.BUY || decision == TradeDecision.SELL) {
            if (symbol == null || symbol.trim().isEmpty()) {
                throw new IllegalArgumentException(
                    decision + " decision requires symbol");
            }
            if (quantity == null || quantity <= 0) {
                throw new IllegalArgumentException(
                    decision + " decision requires positive quantity");
            }
        }
    }
}
