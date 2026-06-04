package com.trading.service;

import com.trading.config.AgentProperties;
import com.trading.entity.AccountHolding;
import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.entity.TradingAccount;
import com.trading.exception.ResourceNotFoundException;
import com.trading.repository.AccountHoldingRepository;
import com.trading.repository.AccountPortfolioSnapshotRepository;
import com.trading.repository.TradingAccountRepository;
import java.time.Instant;
import java.util.List;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Owns portfolio-snapshot creation: looks up the agent's account, values the
 * current holdings (via {@link HoldingsValuationService}), computes PnL against
 * the agent's configured {@code initialCapital}, and persists the snapshot row.
 *
 * <p>Account lookup lives inside the transactional boundary so any failure
 * (lookup, valuation, persist) rolls back as a unit.</p>
 */
@Component
public class PortfolioSnapshotService {

    private final TradingAccountRepository tradingAccountRepository;
    private final AccountHoldingRepository holdingRepository;
    private final AccountPortfolioSnapshotRepository snapshotRepository;
    private final HoldingsValuationService holdingsValuationService;
    private final AgentProperties agentProperties;

    public PortfolioSnapshotService(
            TradingAccountRepository tradingAccountRepository,
            AccountHoldingRepository holdingRepository,
            AccountPortfolioSnapshotRepository snapshotRepository,
            HoldingsValuationService holdingsValuationService,
            AgentProperties agentProperties) {
        this.tradingAccountRepository = tradingAccountRepository;
        this.holdingRepository = holdingRepository;
        this.snapshotRepository = snapshotRepository;
        this.holdingsValuationService = holdingsValuationService;
        this.agentProperties = agentProperties;
    }

    @Transactional
    public void createSnapshot(String agentName) {
        TradingAccount account = tradingAccountRepository
                .findByAgentName(agentName)
                .orElseThrow(() -> new ResourceNotFoundException("Trading account not found for agent: " + agentName
                        + ". Agent must be initialized before snapshot creation."));

        List<AccountHolding> holdings = holdingRepository.findByAccount(account);
        double holdingsValue = holdingsValuationService.calculateHoldingsValue(holdings);
        double totalValue = account.getBalance() + holdingsValue;

        AccountPortfolioSnapshot snapshot = new AccountPortfolioSnapshot();
        snapshot.setAccount(account);
        snapshot.setTimestamp(Instant.now());
        snapshot.setTotalValue(totalValue);
        snapshot.setCashBalance(account.getBalance());
        snapshot.setHoldingsValue(holdingsValue);

        AccountPortfolioSnapshot previousSnapshot = snapshotRepository.findTopByAccountOrderByTimestampDesc(account);
        if (previousSnapshot != null) {
            double initialCapital = agentProperties.getInitialCapital(agentName);
            snapshot.calculateMetrics(initialCapital, previousSnapshot.getTotalValue());
        }

        snapshotRepository.save(snapshot);
    }
}
