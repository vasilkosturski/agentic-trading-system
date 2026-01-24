package com.trading.config;

import com.trading.entity.TradingAgent;
import com.trading.repository.TradingAgentRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.Map;

/**
 * Initializes agent styles on startup if not already set.
 * 
 * This ensures existing agents get their style field populated
 * after the schema migration adds the column.
 */
@Component
public class AgentStyleInitializer implements CommandLineRunner {

    private static final Logger logger = LoggerFactory.getLogger(AgentStyleInitializer.class);

    private final TradingAgentRepository agentRepository;

    // Agent name to style mapping
    private static final Map<String, String> AGENT_STYLES = Map.of(
        "Warren", "Value Investor",
        "George", "Contrarian Macro",
        "Ray", "Risk Parity",
        "Cathie", "Growth Innovation"
    );

    public AgentStyleInitializer(TradingAgentRepository agentRepository) {
        this.agentRepository = agentRepository;
    }

    @Override
    @Transactional
    public void run(String... args) {
        logger.info("Checking agent styles...");
        
        for (Map.Entry<String, String> entry : AGENT_STYLES.entrySet()) {
            String agentName = entry.getKey();
            String style = entry.getValue();
            
            agentRepository.findByName(agentName).ifPresent(agent -> {
                if (agent.getStyle() == null || agent.getStyle().isEmpty()) {
                    agent.setStyle(style);
                    agentRepository.save(agent);
                    logger.info("Set style for {}: {}", agentName, style);
                }
            });
        }
        
        logger.info("Agent style initialization complete");
    }
}
