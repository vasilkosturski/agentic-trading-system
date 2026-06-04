package com.trading.dto.response;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("RecentActivityResponse factory tests")
class RecentActivityResponseTest {

    @Test
    @DisplayName("empty(...) returns fully-populated empty-shape DTO")
    void emptyFactoryProducesExpectedShape() {
        RecentActivityResponse response = RecentActivityResponse.empty("warren", 7);

        assertThat(response).isNotNull();
        assertThat(response.getAgentName()).isEqualTo("warren");
        assertThat(response.getDays()).isEqualTo(7);

        assertThat(response.getRuns()).isNotNull();
        assertThat(response.getRuns()).isEmpty();

        assertThat(response.getTotalRuns()).isEqualTo(0);
        assertThat(response.getTotalTrades()).isEqualTo(0);
    }
}
