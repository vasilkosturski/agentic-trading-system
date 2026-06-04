package com.trading.service;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.trading.enums.RunPhase;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.EnumSource;

@DisplayName("RunStateMachine tests")
class RunStateMachineTest {

    // ========== Valid transitions ==========

    @ParameterizedTest(name = "{0} -> {1} is allowed")
    @CsvSource({
        "INITIALIZING, RESEARCHING",
        "INITIALIZING, FAILED",
        "RESEARCHING,  DECIDING",
        "RESEARCHING,  FAILED",
        "DECIDING,     TRADING",
        "DECIDING,     COMPLETED",
        "DECIDING,     FAILED",
        "TRADING,      COMPLETED",
        "TRADING,      FAILED",
        "FAILED,       FAILED"
    })
    @DisplayName("Valid transitions do not throw")
    void validTransitions_DoNotThrow(RunPhase from, RunPhase to) {
        assertThatCode(() -> RunStateMachine.requireValidTransition(from, to)).doesNotThrowAnyException();
    }

    // ========== Invalid transitions ==========

    @ParameterizedTest(name = "{0} -> {1} throws IllegalArgumentException")
    @CsvSource({
        // Skips forward
        "INITIALIZING, DECIDING",
        "INITIALIZING, TRADING",
        "INITIALIZING, COMPLETED",
        "RESEARCHING,  TRADING",
        "RESEARCHING,  COMPLETED",
        // Self-loop on non-terminal
        "INITIALIZING, INITIALIZING",
        "RESEARCHING,  RESEARCHING",
        "DECIDING,     DECIDING",
        "TRADING,      TRADING",
        // Backwards
        "RESEARCHING,  INITIALIZING",
        "DECIDING,     INITIALIZING",
        "DECIDING,     RESEARCHING",
        "TRADING,      INITIALIZING",
        "TRADING,      RESEARCHING",
        "TRADING,      DECIDING",
        // COMPLETED is terminal — nothing allowed
        "COMPLETED,    INITIALIZING",
        "COMPLETED,    RESEARCHING",
        "COMPLETED,    DECIDING",
        "COMPLETED,    TRADING",
        "COMPLETED,    COMPLETED",
        "COMPLETED,    FAILED",
        // FAILED is terminal — only FAILED -> FAILED allowed (covered above)
        "FAILED,       INITIALIZING",
        "FAILED,       RESEARCHING",
        "FAILED,       DECIDING",
        "FAILED,       TRADING",
        "FAILED,       COMPLETED"
    })
    @DisplayName("Invalid transitions throw IllegalArgumentException")
    void invalidTransitions_ThrowIllegalArgumentException(RunPhase from, RunPhase to) {
        assertThatThrownBy(() -> RunStateMachine.requireValidTransition(from, to))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("Invalid phase transition: " + from + " -> " + to);
    }

    // ========== Message format pinning ==========

    @Test
    @DisplayName("Exception message format matches 'Invalid phase transition: X -> Y'")
    void invalidTransition_MessageFormatIsPinned() {
        assertThatThrownBy(() -> RunStateMachine.requireValidTransition(RunPhase.DECIDING, RunPhase.INITIALIZING))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("Invalid phase transition: DECIDING -> INITIALIZING");
    }

    // ========== Edge cases ==========

    @ParameterizedTest(name = "null from -> {0} throws NullPointerException")
    @EnumSource(RunPhase.class)
    @DisplayName("null from phase throws NullPointerException (pins current behavior)")
    void nullFromPhase_ThrowsNullPointerException(RunPhase to) {
        assertThatThrownBy(() -> RunStateMachine.requireValidTransition(null, to))
                .isInstanceOf(NullPointerException.class);
    }

    @ParameterizedTest(name = "{0} -> null throws NullPointerException")
    @EnumSource(value = RunPhase.class)
    @DisplayName(
            "null to phase throws NullPointerException (pins current behavior — Set.contains(null) on immutable Set)")
    void nullToPhase_ThrowsNullPointerException(RunPhase from) {
        assertThatThrownBy(() -> RunStateMachine.requireValidTransition(from, null))
                .isInstanceOf(NullPointerException.class);
    }
}
