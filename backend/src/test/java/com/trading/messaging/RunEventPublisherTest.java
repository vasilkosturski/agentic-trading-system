package com.trading.messaging;

import com.trading.dto.websocket.DecisionCompletedMessage;
import com.trading.dto.websocket.PhaseUpdateMessage;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.messaging.simp.SimpMessagingTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

@DisplayName("RunEventPublisher tests")
class RunEventPublisherTest {

    private SimpMessagingTemplate messagingTemplate;
    private RunEventPublisher publisher;

    @BeforeEach
    void setUp() {
        messagingTemplate = mock(SimpMessagingTemplate.class);
        publisher = new RunEventPublisher(messagingTemplate);
    }

    @Test
    @DisplayName("publishPhaseUpdate sends to /topic/runs/phases with the same payload")
    void publishPhaseUpdateSendsToPhasesTopic() {
        PhaseUpdateMessage message = new PhaseUpdateMessage(1L, 100L, "RESEARCHING");

        publisher.publishPhaseUpdate(message);

        ArgumentCaptor<String> topicCaptor = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<Object> payloadCaptor = ArgumentCaptor.forClass(Object.class);
        verify(messagingTemplate).convertAndSend(topicCaptor.capture(), payloadCaptor.capture());

        assertThat(topicCaptor.getValue()).isEqualTo("/topic/runs/phases");
        assertThat(payloadCaptor.getValue()).isSameAs(message);
    }

    @Test
    @DisplayName("publishDecisionCompleted sends to /topic/runs/decisions with the same payload")
    void publishDecisionCompletedSendsToDecisionsTopic() {
        DecisionCompletedMessage message = new DecisionCompletedMessage(1L, 100L, "BUY", 999L);

        publisher.publishDecisionCompleted(message);

        ArgumentCaptor<String> topicCaptor = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<Object> payloadCaptor = ArgumentCaptor.forClass(Object.class);
        verify(messagingTemplate).convertAndSend(topicCaptor.capture(), payloadCaptor.capture());

        assertThat(topicCaptor.getValue()).isEqualTo("/topic/runs/decisions");
        assertThat(payloadCaptor.getValue()).isSameAs(message);
    }
}
