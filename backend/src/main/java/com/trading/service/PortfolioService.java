package com.trading.service;

import com.trading.dto.response.PortfolioSnapshotDto;
import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.repository.AccountPortfolioSnapshotRepository;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Service for portfolio snapshot operations.
 */
@Service
public class PortfolioService {

    private final AccountPortfolioSnapshotRepository snapshotRepository;

    public PortfolioService(AccountPortfolioSnapshotRepository snapshotRepository) {
        this.snapshotRepository = snapshotRepository;
    }

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

    private PortfolioSnapshotDto convertToDto(AccountPortfolioSnapshot snapshot) {
        return new PortfolioSnapshotDto(
            snapshot.getAccount().getAgent().getName(),
            snapshot.getTimestamp(),
            snapshot.getTotalValue(),
            snapshot.getCashBalance(),
            snapshot.getHoldingsValue(),
            snapshot.getTotalPnl(),
            snapshot.getTotalReturnPercent()
        );
    }
}
