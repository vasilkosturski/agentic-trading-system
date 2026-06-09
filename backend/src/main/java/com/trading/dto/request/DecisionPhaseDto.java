package com.trading.dto.request;

import com.trading.dto.UsageMetricsDto;
import com.trading.dto.jsonb.ReasoningDto;
import com.trading.dto.jsonb.SourceDto;
import com.trading.dto.jsonb.ToolCallDto;
import com.trading.entity.DecisionPhase;
import com.trading.entity.TradingRun;
import com.trading.enums.TradeDecision;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.Map;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

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
     * Token usage metrics from SDK (nested object).
     */
    private UsageMetricsDto metrics;

    private String systemPrompt;

    private String taskPrompt;

    /**
     * Number of attempts the guardrail-retry loop used for this phase.
     * Defaults to 1 (first-try success).
     */
    private Integer guardrailAttempts;

    /**
     * Issue strings from the LAST failed attempt; NULL on first-try success.
     */
    private List<String> guardrailIssues;

    /**
     * Per-phase guardrail outcome label: 'first_try', 'recovered', or 'exhausted'.
     */
    private String guardrailOutcome;

    /**
     * Last rejected LLM output as a JSON-safe object; NULL on first-try success.
     */
    private Map<String, Object> guardrailFailedOutput;

    /**
     * Validate decision consistency.
     * BUY/SELL decisions must have symbol and quantity.
     */
    public void validate() {
        if (decision == TradeDecision.BUY || decision == TradeDecision.SELL) {
            if (symbol == null || symbol.trim().isEmpty()) {
                throw new IllegalArgumentException(decision + " decision requires symbol");
            }
            if (quantity == null || quantity <= 0) {
                throw new IllegalArgumentException(decision + " decision requires positive quantity");
            }
        }
    }

    /**
     * Convert this request DTO into a {@link DecisionPhase} entity attached to
     * the given run. Mirrors the per-DTO mapping convention already used by
     * {@link UsageMetricsDto#toEntity()}.
     */
    public DecisionPhase toEntity(TradingRun run) {
        DecisionPhase phase = new DecisionPhase(run);
        phase.setDecision(decision);
        phase.setSymbol(symbol);
        phase.setQuantity(quantity);
        phase.setReasoning(reasoning);
        phase.setSources(sources);
        phase.setToolCalls(toolCalls);
        phase.setLatencyMs(latencyMs);
        if (metrics != null) {
            phase.setMetrics(metrics.toEntity());
        }
        phase.setSystemPrompt(systemPrompt);
        phase.setTaskPrompt(taskPrompt);
        if (guardrailAttempts != null) {
            phase.setGuardrailAttempts(guardrailAttempts);
        }
        phase.setGuardrailIssues(guardrailIssues);
        if (guardrailOutcome != null) {
            phase.setGuardrailOutcome(guardrailOutcome);
        }
        phase.setGuardrailFailedOutput(guardrailFailedOutput);
        return phase;
    }
}
