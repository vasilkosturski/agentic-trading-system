package com.trading.messaging;

import com.trading.dto.websocket.TradeExecutedMessage;
import com.trading.dto.websocket.TradeRejectedMessage;
import com.trading.enums.TradeRejectionType;
import com.trading.messaging.event.TradeExecutedEvent;
import com.trading.messaging.event.TradeRejectedEvent;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.transaction.support.TransactionTemplate;
import com.trading.testsupport.SharedPostgresContainer;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

/**
 * Integration tests for {@link TradeEventListener} — verifies that broadcasts
 * fire only after the surrounding transaction commits (when one is active),
 * yet still fire immediately when no transaction is active (fallback execution).
 *
 * <p>The listener is exercised end-to-end through Spring's
 * {@link ApplicationEventPublisher}. {@link SimpMessagingTemplate} is mocked
 * at the leaf so we can assert on the broadcast call without spinning up a
 * STOMP broker.</p>
 *
 * <p>A {@link TransactionTemplate} is used to drive transaction boundaries
 * programmatically — the caller methods on {@code AccountService} are not
 * yet {@code @Transactional}, so we synthesize the transactional context the
 * listener needs to observe.</p>
 *
 * <p>The rollback tests gate Phase D's R14 (transactional {@code buyShares}/{@code sellShares}).
 * Two rollback variants are tested: programmatic (via {@code status.setRollbackOnly()}) and
 * exception-driven (via {@code throw new RuntimeException(...)} inside the transaction body).
 * R14 will use exception-driven rollback in production; both variants must demonstrate that
 * the AFTER_COMMIT listener does NOT fire on rollback, regardless of trigger mechanism.</p>
 */
@SpringBootTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@DisplayName("TradeEventListener integration tests")
class TradeEventListenerIntegrationTest {

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        SharedPostgresContainer.register(registry);
    }

    @Autowired
    private ApplicationEventPublisher applicationEventPublisher;

    @Autowired
    private TransactionTemplate transactionTemplate;

    @MockitoBean
    private SimpMessagingTemplate messagingTemplate;

    @BeforeEach
    void resetMocks() {
        reset(messagingTemplate);
    }

    @Test
    @DisplayName("HAPPY PATH: TradeExecutedEvent inside a committing transaction fires broadcast")
    void executedInsideCommittingTransactionBroadcasts() {
        TradeExecutedMessage message = sampleExecutedMessage();

        transactionTemplate.execute(status -> {
            applicationEventPublisher.publishEvent(new TradeExecutedEvent(message));
            return null;
        });

        verify(messagingTemplate).convertAndSend("/topic/runs/trades", (Object) message);
    }

    @Test
    @DisplayName("ROLLBACK PATH: TradeExecutedEvent inside a rolled-back transaction produces NO broadcast")
    void executedInsideRolledBackTransactionDoesNotBroadcast() {
        TradeExecutedMessage message = sampleExecutedMessage();

        transactionTemplate.execute(status -> {
            applicationEventPublisher.publishEvent(new TradeExecutedEvent(message));
            status.setRollbackOnly();
            return null;
        });

        verifyNoInteractions(messagingTemplate);
    }

    @Test
    @DisplayName("FALLBACK PATH: TradeExecutedEvent published OUTSIDE a transaction still fires broadcast (fallbackExecution=true)")
    void executedOutsideTransactionStillBroadcasts() {
        TradeExecutedMessage message = sampleExecutedMessage();

        applicationEventPublisher.publishEvent(new TradeExecutedEvent(message));

        verify(messagingTemplate).convertAndSend("/topic/runs/trades", (Object) message);
    }

    @Test
    @DisplayName("ROLLBACK PATH: TradeRejectedEvent inside a rolled-back transaction produces NO broadcast")
    void rejectedInsideRolledBackTransactionDoesNotBroadcast() {
        TradeRejectedMessage message = sampleRejectedMessage();

        transactionTemplate.execute(status -> {
            applicationEventPublisher.publishEvent(new TradeRejectedEvent(message));
            status.setRollbackOnly();
            return null;
        });

        verifyNoInteractions(messagingTemplate);
    }

    @Test
    @DisplayName("ROLLBACK PATH (exception-driven): TradeExecutedEvent inside a transaction that throws → NO broadcast")
    void executedInsideTransactionThatThrowsExceptionDoesNotBroadcast() {
        TradeExecutedMessage message = sampleExecutedMessage();

        assertThatThrownBy(() -> transactionTemplate.execute(status -> {
            applicationEventPublisher.publishEvent(new TradeExecutedEvent(message));
            throw new RuntimeException("forced rollback");
        })).isInstanceOf(RuntimeException.class)
           .hasMessage("forced rollback");

        verifyNoInteractions(messagingTemplate);
    }

    private TradeExecutedMessage sampleExecutedMessage() {
        TradeExecutedMessage.TradeDetails details =
            new TradeExecutedMessage.TradeDetails("buy", "NVDA", 42, 178.70);
        return new TradeExecutedMessage(1L, 100L, details);
    }

    private TradeRejectedMessage sampleRejectedMessage() {
        return new TradeRejectedMessage(1L, 100L, TradeRejectionType.INSUFFICIENT_FUNDS, "Not enough cash");
    }
}
