package com.trading.service;

import com.trading.config.AgentProperties;
import com.trading.dto.response.AccountReportDto;
import com.trading.dto.response.HoldingDto;
import com.trading.entity.AccountHolding;
import com.trading.entity.TradingAccount;
import com.trading.exception.ResourceNotFoundException;
import com.trading.repository.AccountHoldingRepository;
import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.TradingAccountRepository;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class AccountQueryService {

    private static final Logger logger = LoggerFactory.getLogger(AccountQueryService.class);

    private final TradingAccountRepository tradingAccountRepository;
    private final AccountTransactionRepository transactionRepository;
    private final AccountHoldingRepository holdingRepository;
    private final MarketService marketService;
    private final AgentProperties agentProperties;
    private final HoldingsValuationService holdingsValuationService;

    public AccountQueryService(
            TradingAccountRepository tradingAccountRepository,
            AccountTransactionRepository transactionRepository,
            AccountHoldingRepository holdingRepository,
            MarketService marketService,
            AgentProperties agentProperties,
            HoldingsValuationService holdingsValuationService) {
        this.tradingAccountRepository = tradingAccountRepository;
        this.transactionRepository = transactionRepository;
        this.holdingRepository = holdingRepository;
        this.marketService = marketService;
        this.agentProperties = agentProperties;
        this.holdingsValuationService = holdingsValuationService;
    }

    public Double getBalance(String agentName) {
        TradingAccount account = getAccount(agentName);
        return account.getBalance();
    }

    public List<HoldingDto> getHoldings(String agentName) {
        TradingAccount account = getAccount(agentName);
        List<AccountHolding> holdings = holdingRepository.findByAccount(account);
        return toHoldingDtos(holdings);
    }

    public AccountReportDto getAccountReport(String agentName) {
        TradingAccount account = getAccount(agentName);

        List<AccountHolding> holdings = holdingRepository.findByAccount(account);
        Double holdingsValue = holdingsValuationService.calculateHoldingsValue(holdings);

        Double totalValue = account.getBalance() + holdingsValue;

        double initialCapital = agentProperties.getInitialCapital(agentName);

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
                toHoldingDtos(holdings));
    }

    public Double getTotalPortfolioValue(String agentName) {
        Double balance = getBalance(agentName);
        Optional<TradingAccount> accountOpt = tradingAccountRepository.findByAgentName(agentName);
        if (accountOpt.isEmpty()) {
            return balance;
        }

        List<AccountHolding> holdings = holdingRepository.findByAccount(accountOpt.get());
        Double holdingsValue = holdingsValuationService.calculateHoldingsValue(holdings);

        return balance + holdingsValue;
    }

    private TradingAccount getAccount(String agentName) {
        return tradingAccountRepository
                .findByAgentName(agentName)
                .orElseThrow(() -> new ResourceNotFoundException("Trading account not found for agent: " + agentName
                        + ". Agent must be initialized before trading operations."));
    }

    @SuppressWarnings("checkstyle:IllegalCatch") // per-symbol price lookup degrades gracefully on any upstream failure
    private List<HoldingDto> toHoldingDtos(List<AccountHolding> holdings) {
        List<HoldingDto> dtos = new ArrayList<>();
        for (AccountHolding holding : holdings) {
            try {
                MarketService.PriceData priceData = marketService.getSharePrice(holding.getSymbol());
                double currentPrice = priceData.getPrice();
                double marketValue = holding.getQuantity() * currentPrice;
                double costBasis = holding.getQuantity() * holding.getAveragePrice();
                double unrealizedPnl = marketValue - costBasis;

                double gainLossPercent = (costBasis != 0) ? (unrealizedPnl / costBasis) * 100 : 0.0;

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
                        priceData.getTimestamp()));

            } catch (Exception e) {
                logger.warn(
                        "Failed to get current price for {}: {}. Price fields will be null.",
                        holding.getSymbol(),
                        e.getMessage());

                dtos.add(new HoldingDto(holding.getSymbol(), holding.getQuantity(), holding.getAveragePrice()));
            }
        }
        return dtos;
    }
}
