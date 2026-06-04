package com.trading.service;

import com.trading.dto.request.RunQueryFilter;
import com.trading.entity.TradingRun;
import com.trading.specification.TradingRunSpecification;
import java.time.Instant;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Component;

/**
 * Assembles a {@link Specification} for {@link TradingRun} listing queries.
 *
 * <p>Centralises the predicate composition that callers of
 * {@code TradingRunRepository.findAll(Specification, Pageable)} need, so the
 * service layer can issue a single repository call regardless of whether
 * filters, a cutoff date, both, or neither are supplied.
 *
 * <p>Semantics:
 * <ul>
 *     <li>{@code filter == null} or {@code filter.hasFilters() == false} ⇒
 *         no filter predicates are attached.</li>
 *     <li>{@code cutoffDate == null} ⇒ no date constraint is attached. Callers
 *         use this for admin-mode listings that need to see all runs regardless
 *         of the public display delay.</li>
 *     <li>Both arguments null ⇒ unconstrained specification (matches every
 *         {@code TradingRun}); pair with the desired {@code Pageable} at the
 *         call site.</li>
 * </ul>
 */
@Component
public class RunSpecificationFactory {

    /**
     * Build a composite specification from optional filter criteria and an
     * optional public-display cutoff. {@code null} arguments are treated as
     * "no constraint" rather than empty matches.
     *
     * @param filter     filter criteria; {@code null} or {@code filter.hasFilters() == false} attaches no predicates
     * @param cutoffDate run-start ceiling for public display; {@code null} skips the date constraint
     * @return a specification ready to pass to {@code findAll(Specification, Pageable)}
     */
    public Specification<TradingRun> build(RunQueryFilter filter, Instant cutoffDate) {
        Specification<TradingRun> spec = Specification.where(null);
        if (filter != null && filter.hasFilters()) {
            spec = spec.and(TradingRunSpecification.hasAgentId(filter.getAgentId()))
                    .and(TradingRunSpecification.hasStatus(filter.getStatus()))
                    .and(TradingRunSpecification.hasDecision(filter.getDecision()))
                    .and(TradingRunSpecification.hasSymbol(filter.getSymbol()));
        }
        if (cutoffDate != null) {
            spec = spec.and(TradingRunSpecification.startedAtBefore(cutoffDate));
        }
        return spec;
    }
}
