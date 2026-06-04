package com.trading.dto.response;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("TradingHistoryResponse factory tests")
class TradingHistoryResponseTest {

    @Test
    @DisplayName("empty(...) returns fully-populated empty-shape DTO")
    void emptyFactoryProducesExpectedShape() {
        TradingHistoryResponse response = TradingHistoryResponse.empty("AAPL", "warren", 30);

        assertThat(response).isNotNull();
        assertThat(response.getSymbol()).isEqualTo("AAPL");
        assertThat(response.getAgentName()).isEqualTo("warren");
        assertThat(response.getDays()).isEqualTo(30);

        assertThat(response.getCurrentPosition()).isNotNull();
        assertThat(response.getCurrentPosition().getShares()).isEqualTo(0);
        assertThat(response.getCurrentPosition().getAverageCost()).isEqualTo(0.0);

        assertThat(response.getTrades()).isNotNull();
        assertThat(response.getTrades()).isEmpty();

        assertThat(response.getSummary()).isNotNull();
        assertThat(response.getSummary().getTotalTrades()).isEqualTo(0);
        assertThat(response.getSummary().getBuys()).isEqualTo(0);
        assertThat(response.getSummary().getSells()).isEqualTo(0);
        assertThat(response.getSummary().getPattern()).isEqualTo("none");
    }
}
