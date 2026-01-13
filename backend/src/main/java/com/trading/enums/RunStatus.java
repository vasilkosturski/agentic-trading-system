package com.trading.enums;

/**
 * Trading run completion status.
 * Indicates the final outcome of a trading cycle.
 */
public enum RunStatus {
    /**
     * Cycle is currently running
     */
    IN_PROGRESS("in_progress"),

    /**
     * Cycle finished successfully
     */
    COMPLETED("completed"),

    /**
     * Cycle encountered error and failed
     */
    FAILED("failed");

    private final String value;

    RunStatus(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    /**
     * Get enum from database value.
     * Used for compatibility with existing string-based code.
     */
    public static RunStatus fromValue(String value) {
        for (RunStatus status : values()) {
            if (status.value.equals(value)) {
                return status;
            }
        }
        throw new IllegalArgumentException("Unknown RunStatus value: " + value);
    }
}
