package com.trading.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.trading.entity.AccountHolding;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
@DisplayName("HoldingsValuationService Tests")
class HoldingsValuationServiceTest {

    @Mock
    private MarketService marketService;

    @InjectMocks
    private HoldingsValuationService valuationService;

    @Test
    @DisplayName("Sums quantity x live price for each holding on the happy path")
    void calculateHoldingsValue_LivePrices_SumsQuantityTimesPrice() {
        when(marketService.getSharePrice("NVDA")).thenReturn(priceData(200.0));
        when(marketService.getSharePrice("AAPL")).thenReturn(priceData(150.0));

        double value =
                valuationService.calculateHoldingsValue(List.of(holding("NVDA", 10, 180.0), holding("AAPL", 5, 140.0)));

        // 10 * 200.0 + 5 * 150.0 = 2000 + 750 = 2750
        assertThat(value).isEqualTo(2750.0);
    }

    @Test
    @DisplayName("Market API failure falls back to cost basis (quantity x averagePrice)")
    void calculateHoldingsValue_MarketFails_FallsBackToCostBasis() {
        when(marketService.getSharePrice("NVDA")).thenThrow(new RuntimeException("API down"));

        double value = valuationService.calculateHoldingsValue(List.of(holding("NVDA", 10, 180.0)));

        // Cost basis fallback: 10 * 180.0 = 1800
        assertThat(value).isEqualTo(1800.0);
    }

    @Test
    @DisplayName("Mixed outcomes: live price for one symbol, fallback for another, summed correctly")
    void calculateHoldingsValue_MixedOutcomes_SumsLiveAndFallback() {
        when(marketService.getSharePrice("NVDA")).thenReturn(priceData(200.0));
        when(marketService.getSharePrice("AAPL")).thenThrow(new RuntimeException("rate limit"));

        double value = valuationService.calculateHoldingsValue(List.of(
                holding("NVDA", 10, 180.0), // live: 10 * 200 = 2000
                holding("AAPL", 5, 140.0) // fallback: 5 * 140 = 700
                ));

        assertThat(value).isEqualTo(2700.0).isCloseTo(2700.0, within(0.0001));
    }

    @Test
    @DisplayName("Empty holdings list returns 0.0 and never calls the market")
    void calculateHoldingsValue_EmptyHoldings_ReturnsZeroAndDoesNotHitMarket() {
        double value = valuationService.calculateHoldingsValue(List.of());

        assertThat(value).isEqualTo(0.0);
        verifyNoInteractions(marketService);
    }

    // ---------- Helpers ----------

    private MarketService.PriceData priceData(double price) {
        return new MarketService.PriceData(price, false, Instant.now(), "test");
    }

    private AccountHolding holding(String symbol, int quantity, double averagePrice) {
        AccountHolding h = new AccountHolding();
        h.setSymbol(symbol);
        h.setQuantity(quantity);
        h.setAveragePrice(averagePrice);
        return h;
    }
}
