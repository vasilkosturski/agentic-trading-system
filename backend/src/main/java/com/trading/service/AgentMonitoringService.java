package com.trading.service;

import com.trading.model.Account;
import com.trading.repository.AccountRepository;
import com.trading.service.TradingService.AgentStatusResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
public class AgentMonitoringService {
    
    @Autowired
    private AccountRepository accountRepository;
    
    private static final List<String> AGENT_NAMES = Arrays.asList("warren", "george", "ray", "cathie");
    
    /**
     * Get real agent statuses from SQLite database (replaces mock data)
     */
    public List<AgentStatusResponse> getRealAgentStatuses() {
        return AGENT_NAMES.stream()
            .map(this::getRealAgentStatus)
            .collect(Collectors.toList());
    }
    
    /**
     * Get real agent status from SQLite database
     */
    public AgentStatusResponse getRealAgentStatus(String agentName) {
        Optional<Account> accountOpt = accountRepository.findByName(agentName.toLowerCase());
        
        if (accountOpt.isPresent()) {
            Account account = accountOpt.get();
            
            // Calculate metrics from real data
            int totalTrades = account.getTransactions() != null ? account.getTransactions().size() : 0;
            double portfolioValue = account.calculatePortfolioValue();
            double dayPnL = account.calculateProfitLoss();
            double dayPnLPercent = portfolioValue > 0 ? (dayPnL / portfolioValue) * 100 : 0.0;
            int currentPositions = account.getHoldings() != null ? account.getHoldings().size() : 0;
            
            // Calculate success rate (simplified - could be enhanced)
            double successRate = totalTrades > 0 ? 0.85 : 0.0; // Default success rate
            
            return new AgentStatusResponse(
                capitalizeFirst(agentName),
                true, // Assume active if account exists with transactions
                LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME), // Could get from logs
                totalTrades,
                successRate,
                portfolioValue,
                dayPnL,
                dayPnLPercent,
                currentPositions
            );
        } else {
            // Return inactive status if no account found
            return new AgentStatusResponse(
                capitalizeFirst(agentName),
                false,
                LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
                0,
                0.0,
                10000.0, // Initial balance
                0.0,
                0.0,
                0
            );
        }
    }
    
    /**
     * Get recent activity logs for an agent
     */
    public List<String> getAgentLogs(String agentName, int limit) {
        return accountRepository.getAccountLogs(agentName.toLowerCase(), limit);
    }
    
    /**
     * Check if Python trading system is running (could be enhanced with actual process check)
     */
    public boolean isPythonTradingSystemActive() {
        // Simple check: if any agent has recent transactions, system is likely active
        return AGENT_NAMES.stream()
            .anyMatch(name -> {
                Optional<Account> account = accountRepository.findByName(name);
                return account.isPresent() && 
                       account.get().getTransactions() != null && 
                       !account.get().getTransactions().isEmpty();
            });
    }
    
    private String capitalizeFirst(String str) {
        if (str == null || str.isEmpty()) {
            return str;
        }
        return str.substring(0, 1).toUpperCase() + str.substring(1).toLowerCase();
    }
}