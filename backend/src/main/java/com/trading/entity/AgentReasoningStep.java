package com.trading.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.time.Instant;

@Entity
@Table(name = "agent_reasoning_steps", schema = "analytics")
@Getter
@Setter
@NoArgsConstructor
public class AgentReasoningStep {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "agent_run_id", nullable = false)
    private Long agentRunId;

    @Column(name = "step_type", nullable = false, length = 50)
    private String stepType; // "research", "analysis", "decision", "execution"

    @Column(name = "step_description", length = 500)
    private String stepDescription; // Brief description of what agent is doing

    @Column(name = "reasoning_text", columnDefinition = "TEXT")
    private String reasoningText; // Detailed agent thoughts

    @Column(nullable = false)
    private Instant timestamp;

    @Column(name = "sequence_number", nullable = false)
    private Integer sequenceNumber;

    // Constructor for creating a reasoning step record
    public AgentReasoningStep(Long agentRunId, String stepType, String stepDescription,
                              String reasoningText, Instant timestamp, Integer sequenceNumber) {
        this.agentRunId = agentRunId;
        this.stepType = stepType;
        this.stepDescription = stepDescription;
        this.reasoningText = reasoningText;
        this.timestamp = timestamp;
        this.sequenceNumber = sequenceNumber;
    }
}

