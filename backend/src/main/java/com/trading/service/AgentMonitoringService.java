package com.trading.service;

import com.trading.dto.response.AgentStatusResponse;
import com.trading.entity.TradingAgent;
import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.repository.TradingAgentRepository;
import com.trading.repository.AccountPortfolioSnapshotRepository;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.ArrayList;
import java.util.Optional;

@Service
public class AgentMonitoringService {
    
    private final TradingAgentRepository agentRepository;
    private final AccountPortfolioSnapshotRepository snapshotRepository;
    private final AccountService accountService;
    private final TradingService tradingService;
    
    public AgentMonitoringService(
            TradingAgentRepository agentRepository,
            AccountPortfolioSnapshotRepository snapshotRepository,
            AccountService accountService,
            TradingService tradingService) {
        this.agentRepository = agentRepository;
        this.snapshotRepository = snapshotRepository;
        this.accountService = accountService;
        this.tradingService = tradingService;
    }
    
    /**
     * Get real agent statuses from PostgreSQL database
     */
    public List<AgentStatusResponse> getRealAgentStatuses() {
        List<TradingAgent> agents = agentRepository.findAll();
        List<AgentStatusResponse> statuses = new ArrayList<>();
        
        for (TradingAgent agent : agents) {
            AgentStatusResponse status = buildAgentStatusFromEntity(agent);
            statuses.add(status);
        }
        
        return statuses;
    }
    
    /**
     * Build AgentStatusResponse from TradingAgent entity using CACHED snapshot data.
     * This avoids expensive live API calls to Polygon.io on every dashboard load.
     * Snapshots are created hourly by ScheduledSnapshotService.
     */
    private AgentStatusResponse buildAgentStatusFromEntity(TradingAgent agent) {
        String agentName = agent.getName();
        boolean isActive = agent.getIsActive() != null ? agent.getIsActive() : false;

        // Format last activity
        String lastActivity = agent.getLastActivity() != null
            ? agent.getLastActivity().toString()
            : Instant.now().toString();

        // Get real trade count (cheap DB query)
        int totalTrades = tradingService.getAgentTrades(agentName).size();

        // Get portfolio data from LATEST SNAPSHOT (no live API calls!)
        Double portfolioValue;
        double dayPnL;
        int currentPositions;

        Optional<AccountPortfolioSnapshot> latestSnapshot = snapshotRepository.findLatestByAgentName(agentName);
        if (latestSnapshot.isPresent()) {
            AccountPortfolioSnapshot snapshot = latestSnapshot.get();
            portfolioValue = snapshot.getTotalValue();
            dayPnL = snapshot.getDailyPnl() != null ? snapshot.getDailyPnl() : 0.0;
            // Get positions count from holdings (cheap DB query)
            currentPositions = getCurrentPositionsCount(agentName);
        } else {
            // No snapshot yet - fall back to default values
            portfolioValue = agent.getInitialCapital() != null ? agent.getInitialCapital() : 100000.0;
            dayPnL = 0.0;
            currentPositions = 0;
        }

        // Calculate total return from current portfolio value vs initial capital
        Double initialCapital = agent.getInitialCapital() != null ? agent.getInitialCapital() : 100000.0;
        double totalReturnPercent = ((portfolioValue - initialCapital) / initialCapital) * 100;

        double dayPnLPercent = portfolioValue > 0 ? (dayPnL / portfolioValue) * 100 : 0.0;

        // Cycle interval (30 minutes = 1800 seconds)
        int cycleIntervalSeconds = 1800;

        return new AgentStatusResponse(
            agent.getId(),
            agentName,
            isActive,
            lastActivity,
            totalTrades,
            totalReturnPercent,
            portfolioValue,
            dayPnL,
            dayPnLPercent,
            currentPositions,
            cycleIntervalSeconds
        );
    }
    
    /**
     * Get current positions count for an agent
     */
    private int getCurrentPositionsCount(String agentName) {
        try {
            // Use the existing holdings method from PostgreSQLAccountService
            var holdings = accountService.getHoldings(agentName);
            return holdings != null ? holdings.size() : 0;
        } catch (Exception e) {
            return 0;
        }
    }
    
}
