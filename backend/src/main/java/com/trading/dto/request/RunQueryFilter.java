package com.trading.dto.request;

import com.trading.enums.RunStatus;
import com.trading.enums.TradeDecision;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class RunQueryFilter {

    private Long agentId;

    private RunStatus status;

    private TradeDecision decision;

    private String symbol;

    public boolean hasFilters() {
        return agentId != null || status != null || decision != null || symbol != null;
    }
}
