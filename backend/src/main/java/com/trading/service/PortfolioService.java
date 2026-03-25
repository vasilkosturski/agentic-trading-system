package com.trading.service;

import com.trading.dto.response.PortfolioSnapshotDto;
import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.repository.AccountPortfolioSnapshotRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Service for portfolio snapshot operations.
 * Handles retrieval and conversion of portfolio snapshot data.
 */
@Service
@Transactional(readOnly = true)
public class PortfolioService {

    private final AccountPortfolioSnapshotRepository snapshotRepository;

    public PortfolioService(AccountPortfolioSnapshotRepository snapshotRepository) {
        this.snapshotRepository = snapshotRepository;
    }

    /**
     * Get portfolio snapshots with optional filtering by agent name, date range, and limit.
     *
     * @param agentName optional agent name filter
     * @param startDate optional start date for range
     * @param endDate   optional end date for range
     * @param limit     optional maximum number of snapshots to return
     * @return list of portfolio snapshot DTOs ordered by timestamp descending
     */
    public List<PortfolioSnapshotDto> getSnapshots(String agentName, Instant startDate, Instant endDate, Integer limit) {
        List<AccountPortfolioSnapshot> snapshots;

        if (agentName != null && startDate != null && endDate != null) {
            snapshots = snapshotRepository.findByAgentNameAndDateRange(agentName, startDate, endDate);
        } else if (agentName != null) {
            snapshots = snapshotRepository.findByAgentNameOrderByTimestampDesc(agentName);
        } else if (startDate != null && endDate != null) {
            snapshots = snapshotRepository.findByTimestampBetween(startDate, endDate);
        } else {
            snapshots = snapshotRepository.findAllOrderByTimestampDesc();
        }

        if (limit != null && limit > 0 && snapshots.size() > limit) {
            snapshots = snapshots.subList(0, limit);
        }

        return snapshots.stream()
            .map(this::convertToDto)
            .collect(Collectors.toList());
    }

    /**
     * Convert entity to DTO. Account and agent are already fetched via JOIN FETCH.
     * Only maps the 3 fields consumed by the frontend chart.
     */
    private PortfolioSnapshotDto convertToDto(AccountPortfolioSnapshot snapshot) {
        return new PortfolioSnapshotDto(
            snapshot.getAccount().getAgent().getName(),
            snapshot.getTimestamp(),
            snapshot.getTotalValue()
        );
    }
}
