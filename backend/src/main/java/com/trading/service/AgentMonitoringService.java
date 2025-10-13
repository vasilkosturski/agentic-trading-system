package com.trading.service;

import com.trading.entity.TradingAgent;
import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.repository.TradingAgentRepository;
import com.trading.repository.AccountPortfolioSnapshotRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.ZoneId;
import java.time.LocalDate;
import java.util.List;
import java.util.ArrayList;
import java.util.Optional;

@Service
public class AgentMonitoringService {
    
    @Autowired
    private TradingAgentRepository agentRepository;
    
    @Autowired
    private AccountPortfolioSnapshotRepository snapshotRepository;
    
    @Autowired
    private AccountService accountService;
    
    @Autowired
    private TradingService tradingService;
    
    /**
     * Get real agent statuses from PostgreSQL database
     */
    public List<TradingService.AgentStatusResponse> getRealAgentStatuses() {
        List<TradingAgent> agents = agentRepository.findAll();
        List<TradingService.AgentStatusResponse> statuses = new ArrayList<>();
        
        for (TradingAgent agent : agents) {
            TradingService.AgentStatusResponse status = buildAgentStatusFromEntity(agent);
            statuses.add(status);
        }
        
        return statuses;
    }
    
    /**
     * Get real agent status for a specific agent
     */
    public TradingService.AgentStatusResponse getRealAgentStatus(String agentName) {
        Optional<TradingAgent> agentOpt = agentRepository.findByName(agentName);
        if (agentOpt.isEmpty()) {
            throw new RuntimeException("Agent not found: " + agentName);
        }
        
        return buildAgentStatusFromEntity(agentOpt.get());
    }
    
    /**
     * Build AgentStatusResponse from TradingAgent entity using real database data
     */
    private TradingService.AgentStatusResponse buildAgentStatusFromEntity(TradingAgent agent) {
        String agentName = agent.getName();
        boolean isActive = agent.getIsActive() != null ? agent.getIsActive() : false;
        
        // Format last activity
        String lastActivity = agent.getLastActivity() != null
            ? agent.getLastActivity().toString()
            : Instant.now().toString();
        
        // Get real trade data using existing TradingService method
        int totalTrades = tradingService.getAgentTrades(agentName).size();

        // Get real portfolio value using existing service method
        Double portfolioValue = accountService.getTotalPortfolioValue(agentName);
        if (portfolioValue == null) {
            portfolioValue = 10000.0; // Default initial balance if no account exists yet
        }

        // Calculate total return from current portfolio value vs initial capital
        Double initialCapital = agent.getInitialCapital() != null ? agent.getInitialCapital() : 100000.0;
        double totalReturnPercent = ((portfolioValue - initialCapital) / initialCapital) * 100;

        // Calculate daily P&L from portfolio snapshots
        double dayPnL = calculateDailyPnL(agentName);
        double dayPnLPercent = portfolioValue > 0 ? (dayPnL / portfolioValue) * 100 : 0.0;

        // Get current positions count
        int currentPositions = getCurrentPositionsCount(agentName);

        // Cycle interval (30 minutes = 1800 seconds)
        // Frontend will calculate: nextCycleTime = lastActivity + cycleIntervalSeconds
        int cycleIntervalSeconds = 1800;

        return new TradingService.AgentStatusResponse(
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
     * Calculate daily P&L by comparing current portfolio value with yesterday's snapshot
     */
    private double calculateDailyPnL(String agentName) {
        try {
            Optional<AccountPortfolioSnapshot> latestSnapshot = snapshotRepository.findLatestByAgentName(agentName);
            if (latestSnapshot.isEmpty()) {
                return 0.0;
            }
            
            // Get current portfolio value
            Double currentValue = accountService.getTotalPortfolioValue(agentName);
            if (currentValue == null) {
                return 0.0;
            }
            
            // Find yesterday's snapshot for comparison
            List<AccountPortfolioSnapshot> snapshots = snapshotRepository.findByAgentNameOrderByTimestampDesc(agentName);

            // Get start of today (midnight UTC)
            Instant startOfToday = LocalDate.now(ZoneId.of("UTC")).atStartOfDay(ZoneId.of("UTC")).toInstant();

            // Find the closest snapshot to yesterday
            for (AccountPortfolioSnapshot snapshot : snapshots) {
                if (snapshot.getTimestamp().isBefore(startOfToday)) {
                    double previousValue = snapshot.getTotalValue() != null ? snapshot.getTotalValue() : currentValue;
                    return currentValue - previousValue;
                }
            }
            
            // If no previous snapshot, assume no change
            return 0.0;
        } catch (Exception e) {
            // If any error in calculation, return 0
            return 0.0;
        }
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
    
    /**
     * Start an agent (update database to set active status)
     */
    public void startAgent(String agentName) {
        Optional<TradingAgent> agentOpt = agentRepository.findByName(agentName);
        if (agentOpt.isEmpty()) {
            throw new RuntimeException("Agent not found: " + agentName);
        }
        
        TradingAgent agent = agentOpt.get();
        agent.setIsActive(true);
        agent.updateActivity();
        agentRepository.save(agent);
    }
    
    /**
     * Stop an agent (update database to set inactive status)
     */
    public void stopAgent(String agentName) {
        Optional<TradingAgent> agentOpt = agentRepository.findByName(agentName);
        if (agentOpt.isEmpty()) {
            throw new RuntimeException("Agent not found: " + agentName);
        }
        
        TradingAgent agent = agentOpt.get();
        agent.setIsActive(false);
        agent.updateActivity();
        agentRepository.save(agent);
    }
    
}