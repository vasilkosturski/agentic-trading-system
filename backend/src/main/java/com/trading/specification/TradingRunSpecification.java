package com.trading.specification;

import com.trading.dto.request.RunQueryFilter;
import com.trading.entity.DecisionPhase;
import com.trading.entity.TradingRun;
import jakarta.persistence.criteria.*;
import org.springframework.data.jpa.domain.Specification;

import java.time.Instant;

/**
 * JPA Specification for dynamic TradingRun filtering.
 * Supports filtering by agentId, status, decision, and symbol.
 * Decision and symbol filters require join to DecisionPhase.
 */
public class TradingRunSpecification {

    private TradingRunSpecification() {
        // Utility class - prevent instantiation
    }

    /**
     * Build specification from RunQueryFilter.
     * Combines all non-null filters with AND logic.
     */
    public static Specification<TradingRun> fromFilter(RunQueryFilter filter) {
        return Specification
            .where(hasAgentId(filter.getAgentId()))
            .and(hasStatus(filter.getStatus()))
            .and(hasDecision(filter.getDecision()))
            .and(hasSymbol(filter.getSymbol()));
    }

    /**
     * Build specification with date filter for public display delay.
     * Combines filter criteria with startedAt before cutoff date.
     */
    public static Specification<TradingRun> fromFilterWithDateCutoff(RunQueryFilter filter, Instant cutoffDate) {
        return Specification
            .where(hasAgentId(filter.getAgentId()))
            .and(hasStatus(filter.getStatus()))
            .and(hasDecision(filter.getDecision()))
            .and(hasSymbol(filter.getSymbol()))
            .and(startedAtBefore(cutoffDate));
    }

    /**
     * Filter by agent ID.
     */
    public static Specification<TradingRun> hasAgentId(Long agentId) {
        return (root, query, cb) -> {
            if (agentId == null) {
                return null;  // No filter applied
            }
            return cb.equal(root.get("agent").get("id"), agentId);
        };
    }

    /**
     * Filter by run status.
     */
    public static Specification<TradingRun> hasStatus(com.trading.enums.RunStatus status) {
        return (root, query, cb) -> {
            if (status == null) {
                return null;
            }
            return cb.equal(root.get("status"), status);
        };
    }

    /**
     * Filter by trade decision (requires join to DecisionPhase).
     */
    public static Specification<TradingRun> hasDecision(com.trading.enums.TradeDecision decision) {
        return (root, query, cb) -> {
            if (decision == null) {
                return null;
            }
            // Join to decision_phases table
            Join<TradingRun, DecisionPhase> decisionJoin = root.join("decision", JoinType.LEFT);
            return cb.equal(decisionJoin.get("decision"), decision);
        };
    }

    /**
     * Filter by symbol (requires join to DecisionPhase).
     */
    public static Specification<TradingRun> hasSymbol(String symbol) {
        return (root, query, cb) -> {
            if (symbol == null || symbol.trim().isEmpty()) {
                return null;
            }
            // Join to decision_phases table
            Join<TradingRun, DecisionPhase> decisionJoin = root.join("decision", JoinType.LEFT);
            return cb.equal(cb.upper(decisionJoin.get("symbol")), symbol.toUpperCase().trim());
        };
    }

    /**
     * Filter by startedAt before cutoff date.
     * Used for publicDisplayDelayDays filtering.
     */
    public static Specification<TradingRun> startedAtBefore(Instant cutoffDate) {
        return (root, query, cb) -> {
            if (cutoffDate == null) {
                return null;
            }
            return cb.lessThan(root.get("startedAt"), cutoffDate);
        };
    }
}
