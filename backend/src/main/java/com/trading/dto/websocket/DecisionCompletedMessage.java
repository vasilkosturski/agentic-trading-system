package com.trading.dto.websocket;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.trading.enums.WebSocketMessageType;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * WebSocket message for decision completion.
 * Broadcast to /topic/runs/decisions when a trading decision is made.
 */
@Data
@NoArgsConstructor
public class DecisionCompletedMessage {

    private final WebSocketMessageType type = WebSocketMessageType.DECISION_COMPLETED;

    @JsonProperty("agent_id")
    private Long agentId;

    @JsonProperty("run_id")
    private Long runId;

    private String decision;

    @JsonProperty("trade_id")
    private Long tradeId;

    public DecisionCompletedMessage(Long agentId, Long runId, String decision, Long tradeId) {
        this.agentId = agentId;
        this.runId = runId;
        this.decision = decision;
        this.tradeId = tradeId;
    }
}
