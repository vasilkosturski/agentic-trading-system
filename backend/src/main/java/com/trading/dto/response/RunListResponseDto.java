package com.trading.dto.response;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * Paginated response for trading runs list.
 * Per design.md: Used by GET /api/runs?filters to return paginated results.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RunListResponseDto {
    private List<TradingRunDto> runs;
    private Long total;
    private Integer page;
    private Integer limit;
}
