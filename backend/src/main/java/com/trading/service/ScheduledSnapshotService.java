package com.trading.service;

import com.trading.entity.TradingAgent;
import com.trading.repository.TradingAgentRepository;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

/**
 * Service responsible for creating scheduled portfolio snapshots
 * Runs daily at market close to ensure consistent data points across all agents
 */
@Service
public class ScheduledSnapshotService {

    private static final Logger logger = LoggerFactory.getLogger(ScheduledSnapshotService.class);

    @Autowired
    private TradingAgentRepository agentRepository;

    @Autowired
    private PortfolioSnapshotService portfolioSnapshotService;

    /**
     * Create daily portfolio snapshots for all agents at market close (4 PM EST)
     * Cron: "0 0 16 * * ?" = At 16:00 (4pm) every day
     * Running in America/New_York timezone to align with US market hours
     */
    @Scheduled(cron = "0 0 16 * * ?", zone = "America/New_York")
    public void createDailySnapshots() {
        logger.info("Starting daily portfolio snapshot creation at market close");
        createSnapshotsForAllAgents("daily");
    }

    /**
     * Create intraday portfolio snapshots for dashboard performance.
     * Runs every 4 hours (00:00, 04:00, ... UTC) to keep portfolio values fresh
     * without live API calls on each request. The dashboard chart collapses to
     * one point per agent per day, so hourly granularity was ~6x redundant — every
     * 4 hours keeps intraday detail while cutting snapshot writes (and the growth
     * of account_portfolio_snapshots) accordingly.
     * Cron: at minute 0 of every 4th hour (00:00, 04:00, 08:00, ... ).
     */
    @Scheduled(cron = "0 0 */4 * * ?")
    public void createIntradaySnapshots() {
        logger.info("Starting intraday (every-4h) portfolio snapshot creation for dashboard");
        createSnapshotsForAllAgents("intraday");
    }

    /**
     * Common method to create snapshots for all agents
     */
    @SuppressWarnings(
            "checkstyle:IllegalCatch") // scheduled task isolates per-agent and per-batch failures so the cron keeps
    // running
    private void createSnapshotsForAllAgents(String snapshotType) {
        try {
            List<TradingAgent> agents = agentRepository.findAll();
            int successCount = 0;
            int failCount = 0;

            for (TradingAgent agent : agents) {
                try {
                    portfolioSnapshotService.createSnapshot(agent.getName());
                    successCount++;
                    logger.debug("Created {} snapshot for agent: {}", snapshotType, agent.getName());
                } catch (Exception e) {
                    failCount++;
                    logger.error(
                            "Failed to create {} snapshot for agent {}: {}",
                            snapshotType,
                            agent.getName(),
                            e.getMessage());
                }
            }

            logger.info(
                    "{} snapshot creation completed. Success: {}, Failed: {}", snapshotType, successCount, failCount);
        } catch (Exception e) {
            logger.error("Error during {} snapshot creation: {}", snapshotType, e.getMessage(), e);
        }
    }
}
