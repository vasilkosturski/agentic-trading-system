package com.trading.service;

import com.trading.dto.request.RunQueryFilter;
import com.trading.entity.DecisionPhase;
import com.trading.entity.TradingAgent;
import com.trading.entity.TradingRun;
import com.trading.enums.RunStatus;
import com.trading.enums.TradeDecision;
import com.trading.repository.BaseRepositoryTest;
import com.trading.repository.DecisionPhaseRepository;
import com.trading.repository.TradingAgentRepository;
import com.trading.repository.TradingRunRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;

import java.time.Instant;
import java.time.temporal.ChronoUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Verifies that {@link RunSpecificationFactory} composes the four input shapes
 * (filter × cutoff present/absent) into specifications the repository can
 * execute against a real PostgreSQL schema.
 */
@DisplayName("RunSpecificationFactory Tests")
class RunSpecificationFactoryTest extends BaseRepositoryTest {

    private final RunSpecificationFactory factory = new RunSpecificationFactory();

    @Autowired
    private TradingRunRepository tradingRunRepository;

    @Autowired
    private DecisionPhaseRepository decisionPhaseRepository;

    @Autowired
    private TradingAgentRepository tradingAgentRepository;

    private TradingAgent agent;

    @BeforeEach
    void setUp() {
        decisionPhaseRepository.deleteAll();
        tradingRunRepository.deleteAll();
        tradingAgentRepository.deleteAll();
        agent = tradingAgentRepository.save(new TradingAgent("FactoryAgent", "Factory test agent"));
    }

    @Nested
    @DisplayName("build() compose rules")
    class BuildComposeRules {

        @Test
        @DisplayName("null filter + null cutoff returns all runs")
        void nullFilter_nullCutoff_returnsAllRuns() {
            persistRun(Instant.now().minus(2, ChronoUnit.DAYS));
            persistRun(Instant.now().minus(10, ChronoUnit.DAYS));

            Page<TradingRun> page = tradingRunRepository.findAll(
                    factory.build(null, null),
                    PageRequest.of(0, 10));

            assertThat(page.getTotalElements()).isEqualTo(2L);
        }

        @Test
        @DisplayName("null cutoff with filter applies filter only")
        void filterOnly_nullCutoff_appliesFilterOnly() {
            persistRun(Instant.now().minus(1, ChronoUnit.DAYS));    // recent
            TradingRun oldOne = persistRun(Instant.now().minus(20, ChronoUnit.DAYS));
            oldOne.setStatus(RunStatus.COMPLETED);
            tradingRunRepository.save(oldOne);

            RunQueryFilter filter = new RunQueryFilter(null, RunStatus.COMPLETED, null, null);

            Page<TradingRun> page = tradingRunRepository.findAll(
                    factory.build(filter, null),
                    PageRequest.of(0, 10));

            assertThat(page.getTotalElements()).isEqualTo(1L);
            assertThat(page.getContent().get(0).getStatus()).isEqualTo(RunStatus.COMPLETED);
        }

        @Test
        @DisplayName("null filter with cutoff applies cutoff only")
        void nullFilter_withCutoff_appliesCutoffOnly() {
            persistRun(Instant.now().minus(2, ChronoUnit.DAYS));    // newer than cutoff — excluded
            persistRun(Instant.now().minus(10, ChronoUnit.DAYS));   // older than cutoff — included

            Instant cutoff = Instant.now().minus(7, ChronoUnit.DAYS);

            Page<TradingRun> page = tradingRunRepository.findAll(
                    factory.build(null, cutoff),
                    PageRequest.of(0, 10));

            assertThat(page.getTotalElements()).isEqualTo(1L);
        }

        @Test
        @DisplayName("both filter and cutoff applied together")
        void filterAndCutoff_combinedWithAnd() {
            // Recent, BUY — excluded by cutoff
            TradingRun recentBuy = persistRun(Instant.now().minus(2, ChronoUnit.DAYS));
            persistDecision(recentBuy, TradeDecision.BUY, "JPM");
            // Old, BUY — passes both
            TradingRun oldBuy = persistRun(Instant.now().minus(10, ChronoUnit.DAYS));
            persistDecision(oldBuy, TradeDecision.BUY, "BAC");
            // Old, SELL — excluded by filter
            TradingRun oldSell = persistRun(Instant.now().minus(10, ChronoUnit.DAYS));
            persistDecision(oldSell, TradeDecision.SELL, "WFC");

            RunQueryFilter filter = new RunQueryFilter(null, null, TradeDecision.BUY, null);
            Instant cutoff = Instant.now().minus(7, ChronoUnit.DAYS);

            Page<TradingRun> page = tradingRunRepository.findAll(
                    factory.build(filter, cutoff),
                    PageRequest.of(0, 10));

            assertThat(page.getTotalElements()).isEqualTo(1L);
            assertThat(page.getContent().get(0).getId()).isEqualTo(oldBuy.getId());
        }

        @Test
        @DisplayName("filter with hasFilters()==false treated as no-filter")
        void emptyFilter_treatedAsNoFilter() {
            persistRun(Instant.now().minus(2, ChronoUnit.DAYS));
            persistRun(Instant.now().minus(10, ChronoUnit.DAYS));

            RunQueryFilter empty = new RunQueryFilter(null, null, null, null);
            assertThat(empty.hasFilters()).isFalse();

            Page<TradingRun> page = tradingRunRepository.findAll(
                    factory.build(empty, null),
                    PageRequest.of(0, 10));

            assertThat(page.getTotalElements()).isEqualTo(2L);
        }
    }

    private TradingRun persistRun(Instant startedAt) {
        TradingRun run = new TradingRun(agent);
        run.setStartedAt(startedAt);
        return tradingRunRepository.save(run);
    }

    private void persistDecision(TradingRun run, TradeDecision decision, String symbol) {
        DecisionPhase phase = new DecisionPhase(run);
        phase.setDecision(decision);
        phase.setSymbol(symbol);
        decisionPhaseRepository.save(phase);
    }
}
