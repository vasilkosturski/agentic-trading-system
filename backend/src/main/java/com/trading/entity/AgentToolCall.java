package com.trading.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.time.Instant;

@Entity
@Table(name = "agent_tool_calls", schema = "analytics")
@Getter
@Setter
@NoArgsConstructor
public class AgentToolCall {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "agent_run_id", nullable = false)
    private Long agentRunId;

    @Column(name = "tool_name", nullable = false, length = 255)
    private String toolName;

    @Column(name = "input_params", columnDefinition = "TEXT")
    private String inputParams; // JSON string

    @Column(name = "output_result", columnDefinition = "TEXT")
    private String outputResult; // JSON string or plain text, truncated to 10KB

    @Column(nullable = false)
    private Instant timestamp;

    @Column(name = "duration_ms")
    private Long durationMs;

    @Column(nullable = false)
    private Boolean success = true;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "sequence_number", nullable = false)
    private Integer sequenceNumber;

    // Constructor for creating a tool call record
    public AgentToolCall(Long agentRunId, String toolName, String inputParams, 
                         String outputResult, Instant timestamp, Long durationMs, 
                         Boolean success, String errorMessage, Integer sequenceNumber) {
        this.agentRunId = agentRunId;
        this.toolName = toolName;
        this.inputParams = inputParams;
        this.outputResult = outputResult;
        this.timestamp = timestamp;
        this.durationMs = durationMs;
        this.success = success;
        this.errorMessage = errorMessage;
        this.sequenceNumber = sequenceNumber;
    }
}

