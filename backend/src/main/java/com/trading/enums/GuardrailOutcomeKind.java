package com.trading.enums;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

/**
 * Per-phase guardrail-retry outcome label.
 *
 * <p>JSON wire form is the lowercase value ({@code first_try}, {@code recovered},
 * {@code exhausted}) — matches the Python {@code Literal["first_try","recovered","exhausted"]}
 * declared in {@code models/run_tracking.py} so both sides agree on a single
 * canonical spelling. Jackson uses {@link #fromJson(String)} as the
 * {@link JsonCreator} so unknown values surface as a 400 Bad Request via the
 * standard {@code HttpMessageNotReadableException} path rather than persisting
 * a silent typo.
 */
public enum GuardrailOutcomeKind {
    FIRST_TRY("first_try"),
    RECOVERED("recovered"),
    EXHAUSTED("exhausted");

    private final String wireValue;

    GuardrailOutcomeKind(String wireValue) {
        this.wireValue = wireValue;
    }

    @JsonValue
    public String getWireValue() {
        return wireValue;
    }

    @JsonCreator
    public static GuardrailOutcomeKind fromJson(String value) {
        if (value == null) {
            return null;
        }
        for (GuardrailOutcomeKind kind : values()) {
            if (kind.wireValue.equals(value)) {
                return kind;
            }
        }
        throw new IllegalArgumentException(
                "Unknown guardrailOutcome: '" + value + "' (expected one of: first_try, recovered, exhausted)");
    }
}
