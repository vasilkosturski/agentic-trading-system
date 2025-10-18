package com.trading.service;

import com.trading.entity.AgentRun;
import com.trading.repository.AgentRunRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
@Transactional
public class RunService {

    private static final Logger logger = LoggerFactory.getLogger(RunService.class);

    @Autowired
    private AgentRunRepository agentRunRepository;

    /**
     * Start a new agent run
     */
    public AgentRun startRun(String agentName, String runType, String agentContext, String marketConditions) {
        logger.info("Starting {} run for agent: {}", runType, agentName);

        AgentRun run = new AgentRun(agentName, runType, agentContext, marketConditions);
        run = agentRunRepository.save(run);

        logger.info("Created run ID: {} for agent: {}", run.getId(), agentName);
        return run;
    }

    /**
     * End a run that resulted in trades
     */
    public AgentRun endRunWithTrades(Long runId, String fullReasoning, String researchSources,
                                     String summary, Integer tradeCount) {
        logger.info("Ending run {} with {} trades", runId, tradeCount);

        AgentRun run = getRun(runId);
        run.markAsTraded(fullReasoning, researchSources, summary, tradeCount);
        run = agentRunRepository.save(run);

        logger.info("Run {} completed with outcome: {}", runId, run.getOutcome());
        return run;
    }

    /**
     * End a run that resulted in no trades
     */
    public AgentRun endRunWithNoTrade(Long runId, String fullReasoning, String researchSources, String summary) {
        logger.info("Ending run {} with no trades", runId);

        AgentRun run = getRun(runId);
        run.markAsNoTrade(fullReasoning, researchSources, summary);
        run = agentRunRepository.save(run);

        logger.info("Run {} completed with outcome: {}", runId, run.getOutcome());
        return run;
    }

    /**
     * Mark a run as error
     */
    public AgentRun markRunAsError(Long runId, String errorMessage) {
        logger.error("Marking run {} as error: {}", runId, errorMessage);

        AgentRun run = getRun(runId);
        run.markAsError(errorMessage);
        run = agentRunRepository.save(run);

        logger.info("Run {} marked as error", runId);
        return run;
    }

    /**
     * Get a run by ID
     */
    public AgentRun getRun(Long runId) {
        Optional<AgentRun> runOpt = agentRunRepository.findById(runId);
        if (runOpt.isEmpty()) {
            throw new RuntimeException("Agent run not found with ID: " + runId);
        }
        return runOpt.get();
    }

    /**
     * Get recent runs (default 50)
     */
    public List<AgentRun> getRecentRuns() {
        return agentRunRepository.findRecentRuns(50);
    }

    /**
     * Get recent runs with limit
     */
    public List<AgentRun> getRecentRuns(int limit) {
        return agentRunRepository.findRecentRuns(limit);
    }

    /**
     * Get recent runs for a specific agent
     */
    public List<AgentRun> getRecentRunsByAgent(String agentName, int limit) {
        return agentRunRepository.findRecentRunsByAgent(agentName, limit);
    }

    /**
     * Get all runs for an agent
     */
    public List<AgentRun> getRunsByAgent(String agentName) {
        return agentRunRepository.findByAgentNameOrderByStartTimeDesc(agentName);
    }

    /**
     * Get run statistics for an agent
     */
    public RunStatistics getRunStatistics(String agentName) {
        Long totalRuns = agentRunRepository.countByAgentNameAndOutcome(agentName, "TRADED") +
                        agentRunRepository.countByAgentNameAndOutcome(agentName, "NO_TRADE") +
                        agentRunRepository.countByAgentNameAndOutcome(agentName, "ERROR");
        Long tradedRuns = agentRunRepository.countByAgentNameAndOutcome(agentName, "TRADED");
        Long noTradeRuns = agentRunRepository.countByAgentNameAndOutcome(agentName, "NO_TRADE");
        Long errorRuns = agentRunRepository.countByAgentNameAndOutcome(agentName, "ERROR");
        Integer totalTrades = agentRunRepository.getTotalTradeCountByAgent(agentName);

        return new RunStatistics(totalRuns, tradedRuns, noTradeRuns, errorRuns, totalTrades);
    }

    /**
     * Inner class for run statistics
     */
    public static class RunStatistics {
        public final Long totalRuns;
        public final Long tradedRuns;
        public final Long noTradeRuns;
        public final Long errorRuns;
        public final Integer totalTrades;

        public RunStatistics(Long totalRuns, Long tradedRuns, Long noTradeRuns, Long errorRuns, Integer totalTrades) {
            this.totalRuns = totalRuns;
            this.tradedRuns = tradedRuns;
            this.noTradeRuns = noTradeRuns;
            this.errorRuns = errorRuns;
            this.totalTrades = totalTrades;
        }
    }
}
