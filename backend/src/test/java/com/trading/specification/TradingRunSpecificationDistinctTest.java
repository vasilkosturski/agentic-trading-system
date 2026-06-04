package com.trading.specification;

import static org.assertj.core.api.Assertions.assertThat;

import com.trading.entity.DecisionPhase;
import com.trading.entity.TradingAgent;
import com.trading.entity.TradingRun;
import com.trading.enums.TradeDecision;
import com.trading.repository.BaseRepositoryTest;
import com.trading.repository.DecisionPhaseRepository;
import com.trading.repository.TradingAgentRepository;
import com.trading.repository.TradingRunRepository;
import jakarta.persistence.EntityManager;
import jakarta.persistence.criteria.CriteriaBuilder;
import jakarta.persistence.criteria.CriteriaQuery;
import jakarta.persistence.criteria.Predicate;
import jakarta.persistence.criteria.Root;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.jpa.domain.Specification;

/**
 * Verifies that LEFT JOIN-based specifications (hasDecision, hasSymbol) toggle
 * DISTINCT on the content query so the join cannot duplicate parent rows.
 *
 * <p>Background: when {@code DecisionPhase.run_id} is NOT unique (a legitimate
 * future schema: versioned decisions, drafts, retries), the JPA Specification
 * re-runs its LEFT JOIN in BOTH the content query AND the count query that
 * Spring Data emits for {@code findAll(Specification, Pageable)}. Without
 * DISTINCT, the content query returns the parent row N times (once per
 * matching child) — the user-visible symptom is duplicate rows on the page
 * and an inflated total. The fix toggles {@code query.distinct(true)} guarded
 * by {@code query.getResultType()} so the count query is left alone (Spring
 * Data JPA issue #3220: DISTINCT inside the COUNT projection breaks
 * {@code COUNT(DISTINCT x)} aggregation).
 *
 * <p>The existing {@code @UniqueConstraint} on {@code decision_phases.run_id}
 * hides the bug at runtime today; this test drops that constraint at setup so
 * the inflation surfaces, then issues the same Criteria shapes Spring Data
 * emits to verify the spec applies DISTINCT to the content path and skips it
 * on the count path.
 *
 * <p>Implementation note: this test deliberately AVOIDS reading TradingRun
 * entities back through the repository. {@link TradingRun} declares a
 * bidirectional {@code @OneToOne(mappedBy="run") DecisionPhase decision} which
 * Hibernate eagerly resolves during result materialization (mapped-by 1:1
 * with lazy-without-bytecode-enhancement is always loaded eagerly). When the
 * unique constraint is dropped, that fetch throws "More than one row" before
 * the join-inflation can be observed. Projecting to scalar primary keys
 * via raw Criteria queries dodges the bidirectional load while exercising
 * the exact predicate the production spec builds.
 */
@DisplayName("TradingRunSpecification distinct-on-join Tests")
class TradingRunSpecificationDistinctTest extends BaseRepositoryTest {

    @Autowired
    private TradingRunRepository tradingRunRepository;

    @Autowired
    private DecisionPhaseRepository decisionPhaseRepository;

    @Autowired
    private TradingAgentRepository tradingAgentRepository;

    @Autowired
    private EntityManager entityManager;

    private TradingAgent agent;

    @BeforeEach
    void setUp() {
        decisionPhaseRepository.deleteAll();
        tradingRunRepository.deleteAll();
        tradingAgentRepository.deleteAll();

        // Drop the unique constraint on decision_phases.run_id so multiple
        // decision rows per run become legal — this models the future schema
        // (versioned decisions, drafts, retries) where the JBR E4 bug surfaces.
        entityManager.flush();
        entityManager
                .createNativeQuery("DO $$\n" + "DECLARE\n"
                        + "    cname text;\n"
                        + "BEGIN\n"
                        + "    FOR cname IN\n"
                        + "        SELECT conname FROM pg_constraint\n"
                        + "        WHERE conrelid = 'trading.decision_phases'::regclass\n"
                        + "          AND contype = 'u'\n"
                        + "    LOOP\n"
                        + "        EXECUTE 'ALTER TABLE trading.decision_phases DROP CONSTRAINT ' || quote_ident(cname);\n"
                        + "    END LOOP;\n"
                        + "END$$;")
                .executeUpdate();

        agent = tradingAgentRepository.save(new TradingAgent("DistinctTestAgent", "Agent for distinct join tests"));
    }

    @Test
    @DisplayName("hasDecision: distinct content query collapses duplicate run rows from a one-to-many join")
    void hasDecision_multipleMatchingDecisions_contentQueryCollapsesDuplicateRunRows() {
        TradingRun run = tradingRunRepository.save(new TradingRun(agent));
        persistDecision(run, TradeDecision.BUY, "JPM");
        persistDecision(run, TradeDecision.BUY, "BAC");
        entityManager.flush();
        entityManager.clear();

        long distinctRunCount = runDistinctIdsViaContentQuery(TradingRunSpecification.hasDecision(TradeDecision.BUY));

        assertThat(distinctRunCount)
                .as("Content query must collapse duplicate run rows produced by the LEFT JOIN")
                .isEqualTo(1L);
    }

    @Test
    @DisplayName("hasSymbol: distinct content query collapses duplicate run rows from a one-to-many join")
    void hasSymbol_multipleMatchingSymbols_contentQueryCollapsesDuplicateRunRows() {
        TradingRun run = tradingRunRepository.save(new TradingRun(agent));
        persistDecision(run, TradeDecision.BUY, "JPM");
        persistDecision(run, TradeDecision.SELL, "JPM");
        entityManager.flush();
        entityManager.clear();

        long distinctRunCount = runDistinctIdsViaContentQuery(TradingRunSpecification.hasSymbol("JPM"));

        assertThat(distinctRunCount)
                .as("Content query must collapse duplicate run rows produced by the LEFT JOIN")
                .isEqualTo(1L);
    }

    @Test
    @DisplayName(
            "Spec must NOT toggle DISTINCT on a count query (Long result type) — preserves COUNT(DISTINCT) correctness")
    void countQuery_distinctNotApplied() {
        // The guard exists because Spring Data JPA's count path uses COUNT(DISTINCT x)
        // and toggling DISTINCT on the outer query trips issue #3220. We verify the
        // guard by inspecting query.isDistinct() after the spec runs against a
        // Long-typed CriteriaQuery (matches the production count query result type).
        CriteriaBuilder cb = entityManager.getCriteriaBuilder();
        CriteriaQuery<Long> countQuery = cb.createQuery(Long.class);
        Root<TradingRun> root = countQuery.from(TradingRun.class);
        Predicate predicate =
                TradingRunSpecification.hasDecision(TradeDecision.BUY).toPredicate(root, countQuery, cb);
        countQuery.select(cb.countDistinct(root));
        if (predicate != null) {
            countQuery.where(predicate);
        }

        assertThat(countQuery.isDistinct())
                .as("Count query (Long result type) must NOT have DISTINCT toggled — Spring Data JPA #3220")
                .isFalse();
    }

    /**
     * Issues a content-shaped Criteria query: result type is the entity (matching
     * Spring Data's content query) so the spec's distinct-guard triggers, but
     * the projection reads scalar primary keys so the bidirectional
     * {@code @OneToOne(mappedBy)} on {@link TradingRun} is not materialized.
     * Returns the row count actually emitted — duplicates included if DISTINCT
     * was not applied.
     */
    private long runDistinctIdsViaContentQuery(Specification<TradingRun> spec) {
        CriteriaBuilder cb = entityManager.getCriteriaBuilder();
        // Result type is the entity — mirrors Spring Data's content query so the
        // distinct-guard inside the Specification triggers.
        CriteriaQuery<TradingRun> entityQuery = cb.createQuery(TradingRun.class);
        Root<TradingRun> root = entityQuery.from(TradingRun.class);
        Predicate predicate = spec.toPredicate(root, entityQuery, cb);
        boolean distinct = entityQuery.isDistinct();

        // Now build a Long-typed projection query mirroring the same join + predicate
        // (and the distinct flag the spec set), but reading scalar ids so we
        // don't trigger the bidirectional @OneToOne load on TradingRun.
        CriteriaQuery<Long> idQuery = cb.createQuery(Long.class);
        Root<TradingRun> idRoot = idQuery.from(TradingRun.class);
        // Re-run the spec on the new root to attach the same join + predicate.
        Predicate idPredicate = spec.toPredicate(idRoot, idQuery, cb);
        idQuery.select(idRoot.get("id"));
        if (idPredicate != null) {
            idQuery.where(idPredicate);
        }
        if (distinct) {
            idQuery.distinct(true);
        }
        List<Long> ids = entityManager.createQuery(idQuery).getResultList();
        return ids.size();
    }

    private void persistDecision(TradingRun run, TradeDecision decision, String symbol) {
        DecisionPhase phase = new DecisionPhase(run);
        phase.setDecision(decision);
        phase.setSymbol(symbol);
        decisionPhaseRepository.save(phase);
    }
}
