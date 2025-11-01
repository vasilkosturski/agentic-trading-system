package com.trading.dto;

import com.trading.entity.AgentRun;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class AgentRunDto {
    private Long id;
    private Long agentId;
    private String agentName;
    private String runType;
    private Instant startTime;
    private Instant endTime;
    private String outcome;
    private String fullReasoning;
    private String researchSources; // JSON string
    private String summary;
    private Integer tradeCount;
    private String errorMessage;
    private String agentContext; // JSON string
    private String marketConditions; // JSON string
    private Long durationSeconds;

    // Constructor from entity
    public AgentRunDto(AgentRun run) {
        this.id = run.getId();
        this.agentName = run.getAgentName();
        this.agentId = null;
        this.runType = run.getRunType();
        this.startTime = run.getStartTime();
        this.endTime = run.getEndTime();
        this.outcome = run.getOutcome();
        this.fullReasoning = run.getFullReasoning();
        this.researchSources = run.getResearchSources();
        this.summary = run.getSummary();
        this.tradeCount = run.getTradeCount();
        this.errorMessage = run.getErrorMessage();
        this.agentContext = run.getAgentContext();
        this.marketConditions = run.getMarketConditions();
        this.durationSeconds = run.getDurationSeconds();
    }

    // Static factory method
    public static AgentRunDto fromEntity(AgentRun run) {
        return new AgentRunDto(run);
    }

    public static AgentRunDto fromEntity(AgentRun run, Long agentId) {
        AgentRunDto dto = new AgentRunDto(run);
        dto.setAgentId(agentId);
        return dto;
    }
}
