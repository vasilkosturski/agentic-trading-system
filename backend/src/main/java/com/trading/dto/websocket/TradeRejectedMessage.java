package com.trading.dto.websocket;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.trading.enums.TradeRejectionType;
import com.trading.enums.WebSocketMessageType;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * WebSocket message for rejected trade.
 * Broadcast to /topic/runs/trades when a trade is rejected.
 */
@Data
@NoArgsConstructor
public class TradeRejectedMessage {

    private final WebSocketMessageType type = WebSocketMessageType.TRADE_REJECTED;

    @JsonProperty("agent_id")
    private Long agentId;

    @JsonProperty("run_id")
    private Long runId;

    @JsonProperty("rejection_type")
    private TradeRejectionType rejectionType;

    @JsonProperty("rejection_message")
    private String rejectionMessage;

    public TradeRejectedMessage(Long agentId, Long runId, TradeRejectionType rejectionType, String rejectionMessage) {
        this.agentId = agentId;
        this.runId = runId;
        this.rejectionType = rejectionType;
        this.rejectionMessage = rejectionMessage;
    }
}
