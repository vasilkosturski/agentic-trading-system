package com.trading.model;

import java.time.Instant;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Real-time status update for agent trading cycles
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AgentStatusUpdate {
    private Long agentId;
    private String agentName;
    private String phase; // INITIALIZING, FETCHING_DATA, RESEARCHING, ANALYZING, DECIDING, TRADING, COMPLETED, ERROR
    private String message; // Human-readable description
    private Integer progress; // 0-100
    private String outcome; // For COMPLETED phase: trade details or no-trade reason
    private Instant timestamp;
}
