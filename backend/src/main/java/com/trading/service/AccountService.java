package com.trading.service;

import com.trading.dto.response.AccountReportDto;
import com.trading.dto.response.HoldingDto;
import com.trading.dto.response.TradeResult;
import com.trading.entity.*;
import com.trading.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.*;

@Service
@Transactional
public class AccountService {

    private static final Logger logger = LoggerFactory.getLogger(AccountService.class);
    private static final double DEFAULT_INITIAL_BALANCE = 100000.0;

    private final TradingAccountRepository tradingAccountRepository;
    private final AccountTransactionRepository transactionRepository;
    private final AccountHoldingRepository holdingRepository;
    private final AccountPortfolioSnapshotRepository snapshotRepository;
    private final TradingAgentRepository agentRepository;
    private final MarketService marketService;
    private final BuyTradeExecutor buyTradeExecutor;
    private final SellTradeExecutor sellTradeExecutor;

    /**
     * Constructor injection for all dependencies.
     * Ensures immutability and makes dependencies explicit.
     * Spring auto-wires this constructor (no @Autowired needed since Spring 4.3+).
     */
    public AccountService(
            TradingAccountRepository tradingAccountRepository,
            AccountTransactionRepository transactionRepository,
            AccountHoldingRepository holdingRepository,
            AccountPortfolioSnapshotRepository snapshotRepository,
            TradingAgentRepository agentRepository,
            MarketService marketService,
            BuyTradeExecutor buyTradeExecutor,
            SellTradeExecutor sellTradeExecutor) {
        this.tradingAccountRepository = tradingAccountRepository;
        this.transactionRepository = transactionRepository;
        this.holdingRepository = holdingRepository;
        this.snapshotRepository = snapshotRepository;
        this.agentRepository = agentRepository;
        this.marketService = marketService;
        this.buyTradeExecutor = buyTradeExecutor;
        this.sellTradeExecutor = sellTradeExecutor;
    }

    /**
     * Initialize agent and create trading account - should be called when agent starts
     * @param agentName Name of the agent (validated at controller layer)
     * @param initialBalance Initial cash balance (validated at controller layer)
     * @return TradingAccount for the agent
     */
    public TradingAccount initializeAgent(String agentName, Double initialBalance) {
        // Step 1: Check if TradingAgent exists
        Optional<TradingAgent> agentOpt = agentRepository.findByName(agentName);

        if (agentOpt.isPresent()) {
            // Agent exists - check if account exists
            TradingAgent agent = agentOpt.get();
            Optional<TradingAccount> accountOpt = tradingAccountRepository.findByAgentName(agentName);

            if (accountOpt.isPresent()) {
                // Account exists - return it
                return accountOpt.get();
            }
            else {
                return tradingAccountRepository.save(new TradingAccount(agent, initialBalance));
            }
        }

        // Agent doesn't exist - create agent and account
        TradingAgent agent = new TradingAgent(agentName, "Autonomous trading agent");
        agent.setInitialCapital(initialBalance);
        agent = agentRepository.save(agent);

        return tradingAccountRepository.save(new TradingAccount(agent, initialBalance));
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
        List<HoldingDto> holdingsList = new ArrayList<>();
        
        for (AccountHolding holding : holdings) {
            holdingsList.add(new HoldingDto(
                holding.getSymbol(),
                holding.getQuantity(),
                holding.getAveragePrice()
            ));
        }
        
        return holdingsList;
    }

    /**
     * Buy shares for an agent
     * Delegates to BuyTradeExecutor for execution
     * @param runId REQUIRED - Every transaction must be linked to an agent run
     * @return TradeResult with transaction details and updated balance
     */
    public TradeResult buyShares(String agentName, String symbol, Integer quantity, Long runId) {
        TradeResult result = buyTradeExecutor.executeBuy(agentName, symbol, quantity, runId);
        // Update snapshot immediately so dashboard reflects the new trade
        createPortfolioSnapshot(agentName);
        return result;
    }

    /**
     * Sell shares for an agent
     * Delegates to SellTradeExecutor for execution
     * @param runId REQUIRED - Every transaction must be linked to an agent run
     * @return TradeResult with transaction details and updated balance
     */
    public TradeResult sellShares(String agentName, String symbol, Integer quantity, Long runId) {
        TradeResult result = sellTradeExecutor.executeSell(agentName, symbol, quantity, runId);
        // Update snapshot immediately so dashboard reflects the new trade
        createPortfolioSnapshot(agentName);
        return result;
    }

    // changeStrategy method removed - using hardcoded strategies only

    /**
     * Get account report for an agent.
     * Returns DTO that Spring auto-serializes to JSON for MCP resource endpoint.
     * Used by Python agents to provide context to AI for trading decisions.
     */
    public AccountReportDto getAccountReport(String agentName) {
        try {
            TradingAccount account = getAccount(agentName);

            // Get current holdings and calculate their value
            List<AccountHolding> holdings = holdingRepository.findByAccount(account);
            Double holdingsValue = calculateHoldingsValue(holdings);

            // Calculate total portfolio value
            Double totalValue = account.getBalance() + holdingsValue;

            // Build and return DTO (Spring will serialize to JSON)
            return new AccountReportDto(
                agentName,
                account.getBalance(),
                holdingsValue,
                totalValue,
                DEFAULT_INITIAL_BALANCE,
                totalValue - DEFAULT_INITIAL_BALANCE,
                ((totalValue - DEFAULT_INITIAL_BALANCE) / DEFAULT_INITIAL_BALANCE) * 100,
                account.getUpdatedAt(),
                holdings.size(),
                transactionRepository.countByAccount(account)
            );

        } catch (Exception e) {
            throw new RuntimeException("Error getting account report for " + agentName + ": " + e.getMessage());
        }
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
        Double holdingsValue = calculateHoldingsValue(holdings);

        return balance + holdingsValue;
    }

    /**
     * Create portfolio snapshot for an agent
     */
    public void createPortfolioSnapshot(String agentName) {
        TradingAccount account = getAccount(agentName);
        createPortfolioSnapshot(account);
    }

    /**
     * Get trading account for an agent - expects account to already exist
     */
    /**
     * Get account for agent (package-private for use by BuyTradeExecutor)
     */
    TradingAccount getAccount(String agentName) {
        return tradingAccountRepository.findByAgentName(agentName)
            .orElseThrow(() -> new RuntimeException("Trading account not found for agent: " + agentName +
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
            throw new RuntimeException("Agent not found: " + agentName);
        }
    }

    /**
     * Create portfolio snapshot for an account
     */
    private void createPortfolioSnapshot(TradingAccount account) {
        // Calculate total portfolio value using live market prices
        List<AccountHolding> holdings = holdingRepository.findByAccount(account);
        double holdingsValue = calculateHoldingsValue(holdings);

        double totalValue = account.getBalance() + holdingsValue;

        AccountPortfolioSnapshot snapshot = new AccountPortfolioSnapshot();
        snapshot.setAccount(account);
        snapshot.setTimestamp(Instant.now());
        snapshot.setTotalValue(totalValue);
        snapshot.setCashBalance(account.getBalance());
        snapshot.setHoldingsValue(holdingsValue);

        // Calculate P&L if we have previous snapshots
        AccountPortfolioSnapshot previousSnapshot = snapshotRepository
            .findTopByAccountOrderByTimestampDesc(account);
        if (previousSnapshot != null) {
            snapshot.calculateMetrics(DEFAULT_INITIAL_BALANCE, previousSnapshot.getTotalValue());
        }

        snapshotRepository.save(snapshot);
    }

    /**
     * Calculate total value of holdings using live market prices.
     * Extracted method to eliminate duplication across 3 methods.
     * Falls back to average purchase price if market API fails.
     */
    private double calculateHoldingsValue(List<AccountHolding> holdings) {
        return holdings.stream()
            .mapToDouble(h -> {
                try {
                    MarketService.PriceData priceData = marketService.getSharePrice(h.getSymbol());
                    return h.getQuantity() * priceData.getPrice();
                } catch (Exception e) {
                    // Fallback to average purchase price if API fails
                    return h.getQuantity() * h.getAveragePrice();
                }
            })
            .sum();
    }

}