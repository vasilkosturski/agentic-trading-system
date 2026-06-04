package com.trading.util;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("MoneyMath utility tests")
class MoneyMathTest {

    @Test
    @DisplayName("round2(0.1 + 0.2) returns 0.30 (IEEE-754 imprecision absorbed)")
    void round2HandlesFloatingPointImprecision() {
        assertThat(MoneyMath.round2(0.1 + 0.2)).isEqualTo(0.30);
    }

    @Test
    @DisplayName("round2(1.005) returns 1.01 (HALF_UP boundary — Math.round returns 1.00 here)")
    void round2RoundsHalfUp() {
        assertThat(MoneyMath.round2(1.005)).isEqualTo(1.01);
    }
}
