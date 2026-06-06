package com.trading.service;

import com.trading.dto.request.RunQueryFilter;
import com.trading.entity.TradingRun;
import com.trading.specification.TradingRunSpecification;
import java.time.Instant;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Component;

@Component
public class RunSpecificationFactory {

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
