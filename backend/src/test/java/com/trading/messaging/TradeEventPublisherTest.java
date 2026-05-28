package com.trading.messaging;

import com.trading.dto.websocket.TradeExecutedMessage;
import com.trading.dto.websocket.TradeRejectedMessage;
import com.trading.enums.TradeRejectionType;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.messaging.simp.SimpMessagingTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

@DisplayName("TradeEventPublisher tests")
class TradeEventPublisherTest {

    private SimpMessagingTemplate messagingTemplate;
    private TradeEventPublisher publisher;

    @BeforeEach
    void setUp() {
        messagingTemplate = mock(SimpMessagingTemplate.class);
        publisher = new TradeEventPublisher(messagingTemplate);
    }

    @Test
    @DisplayName("publishTradeExecuted sends to /topic/runs/trades with the same payload")
    void publishTradeExecutedSendsToTradesTopic() {
        TradeExecutedMessage.TradeDetails details = new TradeExecutedMessage.TradeDetails("BUY", "NVDA", 42, 178.70);
        TradeExecutedMessage message = new TradeExecutedMessage(1L, 100L, details);

        publisher.publishTradeExecuted(message);

        ArgumentCaptor<String> topicCaptor = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<Object> payloadCaptor = ArgumentCaptor.forClass(Object.class);
        verify(messagingTemplate).convertAndSend(topicCaptor.capture(), payloadCaptor.capture());

        assertThat(topicCaptor.getValue()).isEqualTo("/topic/runs/trades");
        assertThat(payloadCaptor.getValue()).isSameAs(message);
    }

    @Test
    @DisplayName("publishTradeRejected sends to /topic/runs/trades with the same payload")
    void publishTradeRejectedSendsToTradesTopic() {
        TradeRejectedMessage message = new TradeRejectedMessage(
            1L,
            100L,
            TradeRejectionType.INSUFFICIENT_FUNDS,
            "Not enough cash"
        );

        publisher.publishTradeRejected(message);

        ArgumentCaptor<String> topicCaptor = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<Object> payloadCaptor = ArgumentCaptor.forClass(Object.class);
        verify(messagingTemplate).convertAndSend(topicCaptor.capture(), payloadCaptor.capture());

        assertThat(topicCaptor.getValue()).isEqualTo("/topic/runs/trades");
        assertThat(payloadCaptor.getValue()).isSameAs(message);
    }
}
