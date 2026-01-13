package com.trading.enums;

/**
 * Status for decision and execution phases.
 * Tracks the lifecycle of individual phase execution.
 */
public enum PhaseStatus {
    /**
     * Phase not yet started
     */
    PENDING("pending"),

    /**
     * Phase is currently executing
     */
    IN_PROGRESS("in_progress"),

    /**
     * Phase completed successfully
     */
    COMPLETED("completed"),

    /**
     * Phase encountered error and failed
     */
    FAILED("failed"),

    /**
     * Phase was skipped (e.g., HOLD decision means no execution phase)
     */
    SKIPPED("skipped");

    private final String value;

    PhaseStatus(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    /**
     * Get enum from database value.
     * Used for compatibility with existing string-based code.
     */
    public static PhaseStatus fromValue(String value) {
        for (PhaseStatus status : values()) {
            if (status.value.equals(value)) {
                return status;
            }
        }
        throw new IllegalArgumentException("Unknown PhaseStatus value: " + value);
    }
}
