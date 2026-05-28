package com.trading.service;

import com.trading.config.AgentProperties;
import com.trading.dto.response.AccountReportDto;
import com.trading.dto.response.HoldingDto;
import com.trading.entity.*;
import com.trading.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import com.trading.exception.ResourceNotFoundException;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class AccountService {

    private static final Logger logger = LoggerFactory.getLogger(AccountService.class);

    // Agent name → display style. Values match Python InvestmentStyle enum.
    private static final Map<String, String> AGENT_STYLES = Map.of(
        "Warren", "Value Investor",
        "George", "Contrarian Macro",
        "Ray", "Risk Parity",
        "Cathie", "Growth Innovation"
    );

    private final TradingAccountRepository tradingAccountRepository;
    private final AccountTransactionRepository transactionRepository;
    private final AccountHoldingRepository holdingRepository;
    private final TradingAgentRepository agentRepository;
    private final MarketService marketService;
    private final AgentProperties agentProperties;
    private final HoldingsValuationService holdingsValuationService;

    /**
     * Constructor injection for all dependencies.
     * Ensures immutability and makes dependencies explicit.
     * Spring auto-wires this constructor (no @Autowired needed since Spring 4.3+).
     */
    public AccountService(
            TradingAccountRepository tradingAccountRepository,
            AccountTransactionRepository transactionRepository,
            AccountHoldingRepository holdingRepository,
            TradingAgentRepository agentRepository,
            MarketService marketService,
            AgentProperties agentProperties,
            HoldingsValuationService holdingsValuationService) {
        this.tradingAccountRepository = tradingAccountRepository;
        this.transactionRepository = transactionRepository;
        this.holdingRepository = holdingRepository;
        this.agentRepository = agentRepository;
        this.marketService = marketService;
        this.agentProperties = agentProperties;
        this.holdingsValuationService = holdingsValuationService;
    }

    /**
     * Initialize agent and create trading account - should be called when agent starts
     * @param agentName Name of the agent (validated at controller layer)
     * @param initialBalance Initial cash balance (validated at controller layer)
     * @return TradingAccount for the agent
     */
    public TradingAccount initializeAgent(String agentName, Double initialBalance) {
        Optional<TradingAgent> agentOpt = agentRepository.findByName(agentName);

        if (agentOpt.isPresent()) {
            TradingAgent agent = agentOpt.get();
            populateStyle(agent);

            Optional<TradingAccount> accountOpt = tradingAccountRepository.findByAgentName(agentName);
            if (accountOpt.isPresent()) {
                return accountOpt.get();
            }
            return tradingAccountRepository.save(new TradingAccount(agent, initialBalance));
        }

        // Agent doesn't exist - create agent and account
        TradingAgent agent = new TradingAgent(agentName, "Autonomous trading agent");
        agent.setInitialCapital(initialBalance);
        populateStyle(agent);
        agent = agentRepository.save(agent);

        return tradingAccountRepository.save(new TradingAccount(agent, initialBalance));
    }

    /**
     * Populate style on the entity if missing.
     */
    private void populateStyle(TradingAgent agent) {
        if (agent.getStyle() == null || agent.getStyle().isEmpty()) {
            String style = AGENT_STYLES.get(agent.getName());
            if (style != null) {
                agent.setStyle(style);
            }
        }
    }

    /**
     * Get account balance for an agent
     */
    public Double getBalance(String agentName) {
        TradingAccount account = getAccount(agentName);
        return account.getBalance();
    }

    /**
     * Get holdings for an agent as List<HoldingDto>
     */
    public List<HoldingDto> getHoldings(String agentName) {
        TradingAccount account = getAccount(agentName);
        List<AccountHolding> holdings = holdingRepository.findByAccount(account);
        return toHoldingDtos(holdings);
    }

    /**
     * Get account report for an agent.
     * Returns DTO that Spring auto-serializes to JSON for MCP resource endpoint.
     * Used by Python agents to provide context to AI for trading decisions.
     */
    public AccountReportDto getAccountReport(String agentName) {
        TradingAccount account = getAccount(agentName);

        // Get current holdings and calculate their value
        List<AccountHolding> holdings = holdingRepository.findByAccount(account);
        Double holdingsValue = holdingsValuationService.calculateHoldingsValue(holdings);

        // Calculate total portfolio value
        Double totalValue = account.getBalance() + holdingsValue;

        double initialCapital = agentProperties.getInitialCapital(agentName);

        // Build and return DTO (Spring will serialize to JSON)
        return new AccountReportDto(
            agentName,
            account.getBalance(),
            holdingsValue,
            totalValue,
            initialCapital,
            totalValue - initialCapital,
            ((totalValue - initialCapital) / initialCapital) * 100,
            account.getUpdatedAt(),
            holdings.size(),
            transactionRepository.countByAccount(account),
            toHoldingDtos(holdings)
        );
    }

    // getStrategy method removed - using hardcoded strategies only

    /**
     * Get total portfolio value for an agent
     */
    public Double getTotalPortfolioValue(String agentName) {
        Double balance = getBalance(agentName);
        Optional<TradingAccount> accountOpt = tradingAccountRepository.findByAgentName(agentName);
        if (accountOpt.isEmpty()) {
            return balance;
        }

        // Calculate holdings value using LIVE market prices (cached for 60 minutes)
        List<AccountHolding> holdings = holdingRepository.findByAccount(accountOpt.get());
        Double holdingsValue = holdingsValuationService.calculateHoldingsValue(holdings);

        return balance + holdingsValue;
    }

    /**
     * Get trading account for an agent - expects account to already exist
     */
    /**
     * Get account for agent (package-private for use by BuyTradeExecutor)
     */
    TradingAccount getAccount(String agentName) {
        return tradingAccountRepository.findByAgentName(agentName)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Trading account not found for agent: " + agentName +
                ". Agent must be initialized before trading operations."));
    }


    /**
     * Update agent activity timestamp (called on every cycle check via trading_system.py)
     * Single source of truth for lastActivity updates
     */
    public void updateAgentActivity(String agentName) {
        Optional<TradingAgent> agentOpt = agentRepository.findByName(agentName);
        if (agentOpt.isPresent()) {
            TradingAgent agent = agentOpt.get();
            agent.updateActivity();
            agentRepository.save(agent);
            logger.debug("Updated activity timestamp for agent: {}", agentName);
        } else {
            throw new ResourceNotFoundException("Agent not found: " + agentName);
        }
    }

    private List<HoldingDto> toHoldingDtos(List<AccountHolding> holdings) {
        List<HoldingDto> dtos = new ArrayList<>();
        for (AccountHolding holding : holdings) {
            try {
                // Fetch current market price (cached for 60 minutes)
                MarketService.PriceData priceData = marketService.getSharePrice(holding.getSymbol());
                double currentPrice = priceData.getPrice();
                double marketValue = holding.getQuantity() * currentPrice;
                double costBasis = holding.getQuantity() * holding.getAveragePrice();
                double unrealizedPnl = marketValue - costBasis;

                // Guard against division by zero when calculating percentage
                double gainLossPercent = (costBasis != 0)
                    ? (unrealizedPnl / costBasis) * 100
                    : 0.0;

                dtos.add(new HoldingDto(
                    holding.getSymbol(),
                    holding.getQuantity(),
                    holding.getAveragePrice(),
                    currentPrice,
                    marketValue,
                    costBasis,
                    unrealizedPnl,
                    gainLossPercent,
                    priceData.isCached(),
                    priceData.getTimestamp()
                ));

            } catch (Exception e) {
                // Fallback: return nulls for price fields so frontend shows "N/A" instead of misleading zeros
                logger.warn("Failed to get current price for {}: {}. Price fields will be null.",
                    holding.getSymbol(), e.getMessage());

                dtos.add(new HoldingDto(
                    holding.getSymbol(),
                    holding.getQuantity(),
                    holding.getAveragePrice()
                ));
            }
        }
        return dtos;
    }
}
