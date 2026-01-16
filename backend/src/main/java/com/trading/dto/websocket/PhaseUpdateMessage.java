package com.trading.dto.websocket;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * WebSocket message for phase updates.
 * Broadcast to /topic/runs/phases when a run's phase changes.
 */
@Data
@NoArgsConstructor
public class PhaseUpdateMessage {

    private final String type = "phase_update";

    @JsonProperty("agent_id")
    private Long agentId;

    @JsonProperty("run_id")
    private Long runId;

    private String phase;

    public PhaseUpdateMessage(Long agentId, Long runId, String phase) {
        this.agentId = agentId;
        this.runId = runId;
        this.phase = phase;
    }
}
