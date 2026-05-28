package com.trading.messaging;

import com.trading.dto.websocket.TradeExecutedMessage;
import com.trading.dto.websocket.TradeRejectedMessage;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;

/**
 * Wraps {@link SimpMessagingTemplate} for trade-broadcast concerns.
 */
@Component
public class TradeEventPublisher {

    private final SimpMessagingTemplate messagingTemplate;

    public TradeEventPublisher(SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
    }

    public void publishTradeExecuted(TradeExecutedMessage message) {
        messagingTemplate.convertAndSend(WebSocketTopics.TOPIC_TRADES, message);
    }

    public void publishTradeRejected(TradeRejectedMessage message) {
        messagingTemplate.convertAndSend(WebSocketTopics.TOPIC_TRADES, message);
    }
}
