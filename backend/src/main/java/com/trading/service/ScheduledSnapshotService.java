package com.trading.service;

import com.trading.entity.TradingAgent;
import com.trading.repository.TradingAgentRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.util.List;

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
    private AccountService accountService;

    /**
     * Create daily portfolio snapshots for all agents at market close (4 PM EST)
     * Cron: "0 0 16 * * ?" = At 16:00 (4pm) every day
     * Running in America/New_York timezone to align with US market hours
     */
    @Scheduled(cron = "0 0 16 * * ?", zone = "America/New_York")
    public void createDailySnapshots() {
        logger.info("Starting daily portfolio snapshot creation at market close");

        try {
            List<TradingAgent> agents = agentRepository.findAll();
            int successCount = 0;
            int failCount = 0;

            for (TradingAgent agent : agents) {
                try {
                    accountService.createPortfolioSnapshot(agent.getName());
                    successCount++;
                    logger.debug("Created snapshot for agent: {}", agent.getName());
                } catch (Exception e) {
                    failCount++;
                    logger.error("Failed to create snapshot for agent {}: {}",
                        agent.getName(), e.getMessage());
                }
            }

            logger.info("Daily snapshot creation completed. Success: {}, Failed: {}",
                successCount, failCount);
        } catch (Exception e) {
            logger.error("Error during daily snapshot creation: {}", e.getMessage(), e);
        }
    }
}
