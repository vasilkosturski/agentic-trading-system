package com.trading.util;

import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * Money-rounding helper. Rounds to 2 decimal places using HALF_UP semantics
 * (rounds halves away from zero, matching typical monetary conventions and
 * avoiding the IEEE-754 surprises of {@code Math.round(x * 100.0) / 100.0}).
 */
public final class MoneyMath {

    private MoneyMath() {
        // utility class — no instances
    }

    public static double round2(double value) {
        return BigDecimal.valueOf(value).setScale(2, RoundingMode.HALF_UP).doubleValue();
    }
}
