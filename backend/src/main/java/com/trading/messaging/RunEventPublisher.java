package com.trading.messaging;

import com.trading.dto.websocket.DecisionCompletedMessage;
import com.trading.dto.websocket.PhaseUpdateMessage;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;

/**
 * Wraps {@link SimpMessagingTemplate} for trading-run broadcast concerns
 * (phase updates and decision completions).
 */
@Component
public class RunEventPublisher {

    private final SimpMessagingTemplate messagingTemplate;

    public RunEventPublisher(SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
    }

    public void publishPhaseUpdate(PhaseUpdateMessage message) {
        messagingTemplate.convertAndSend(WebSocketTopics.TOPIC_PHASES, message);
    }

    public void publishDecisionCompleted(DecisionCompletedMessage message) {
        messagingTemplate.convertAndSend(WebSocketTopics.TOPIC_DECISIONS, message);
    }
}
