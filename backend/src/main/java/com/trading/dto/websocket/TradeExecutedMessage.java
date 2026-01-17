package com.trading.dto.websocket;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.trading.enums.WebSocketMessageType;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * WebSocket message for successful trade execution.
 * Broadcast to /topic/runs/trades when a trade is executed.
 */
@Data
@NoArgsConstructor
public class TradeExecutedMessage {

    private final WebSocketMessageType type = WebSocketMessageType.TRADE_EXECUTED;

    @JsonProperty("agent_id")
    private Long agentId;

    @JsonProperty("run_id")
    private Long runId;

    private TradeDetails trade;

    public TradeExecutedMessage(Long agentId, Long runId, TradeDetails trade) {
        this.agentId = agentId;
        this.runId = runId;
        this.trade = trade;
    }

    @Data
    @NoArgsConstructor
    public static class TradeDetails {
        private String side;
        private String symbol;
        private Integer quantity;
        private Double price;

        @JsonProperty("total_cost")
        private Double totalCost;

        public TradeDetails(String side, String symbol, Integer quantity, Double price) {
            this.side = side;
            this.symbol = symbol;
            this.quantity = quantity;
            this.price = price;
            this.totalCost = price * quantity;
        }
    }
}
