package com.trading.service;

import com.trading.entity.AccountHolding;
import java.util.List;
import org.springframework.stereotype.Component;

/**
 * Computes the live-market value of an agent's holdings.
 *
 * <p>For each holding, attempts to fetch the current market price via
 * {@link MarketService}. Falls back to the holding's average purchase price
 * (cost basis) when the market lookup fails, so a transient API outage
 * doesn't surface as a zeroed-out portfolio value.</p>
 */
@Component
public class HoldingsValuationService {

    private final MarketService marketService;

    public HoldingsValuationService(MarketService marketService) {
        this.marketService = marketService;
    }

    public double calculateHoldingsValue(List<AccountHolding> holdings) {
        return holdings.stream().mapToDouble(this::valueOf).sum();
    }

    @SuppressWarnings("checkstyle:IllegalCatch") // valuation falls back to cost basis on any upstream price failure
    private double valueOf(AccountHolding holding) {
        try {
            MarketService.PriceData priceData = marketService.getSharePrice(holding.getSymbol());
            return holding.getQuantity() * priceData.getPrice();
        } catch (Exception e) {
            return holding.getQuantity() * holding.getAveragePrice();
        }
    }
}
