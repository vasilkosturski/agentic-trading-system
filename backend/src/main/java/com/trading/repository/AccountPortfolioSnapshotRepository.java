package com.trading.repository;

import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.entity.TradingAccount;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface AccountPortfolioSnapshotRepository extends JpaRepository<AccountPortfolioSnapshot, Long> {
    
    /**
     * Find all snapshots for a specific trading account
     */
    List<AccountPortfolioSnapshot> findByAccountOrderByTimestampDesc(TradingAccount account);
    
    /**
     * Find snapshots by agent name
     */
    @Query("SELECT aps FROM AccountPortfolioSnapshot aps WHERE aps.account.agent.name = :agentName ORDER BY aps.timestamp DESC")
    List<AccountPortfolioSnapshot> findByAgentNameOrderByTimestampDesc(@Param("agentName") String agentName);
    
    /**
     * Find snapshots within date range
     */
    @Query("SELECT aps FROM AccountPortfolioSnapshot aps WHERE aps.timestamp BETWEEN :startDate AND :endDate ORDER BY aps.timestamp DESC")
    List<AccountPortfolioSnapshot> findByTimestampBetween(@Param("startDate") Instant startDate,
                                                         @Param("endDate") Instant endDate);
    
    /**
     * Find latest snapshot for an agent
     */
    @Query("SELECT aps FROM AccountPortfolioSnapshot aps WHERE aps.account.agent.name = :agentName ORDER BY aps.timestamp DESC LIMIT 1")
    Optional<AccountPortfolioSnapshot> findLatestByAgentName(@Param("agentName") String agentName);
    
    /**
     * Find recent snapshots for an agent (last N snapshots)
     */
    @Query(value = "SELECT * FROM trading.account_portfolio_snapshots aps " +
                   "JOIN trading.trading_accounts ta ON aps.account_id = ta.id " +
                   "JOIN trading.trading_agents ag ON ta.agent_id = ag.id " +
                   "WHERE ag.name = :agentName " +
                   "ORDER BY aps.timestamp DESC LIMIT :limit", nativeQuery = true)
    List<AccountPortfolioSnapshot> findRecentSnapshotsByAgent(@Param("agentName") String agentName,
                                                             @Param("limit") int limit);
    
    /**
     * Get portfolio performance over time for an agent
     */
    @Query("SELECT aps FROM AccountPortfolioSnapshot aps WHERE aps.account.agent.name = :agentName AND aps.timestamp >= :fromDate ORDER BY aps.timestamp ASC")
    List<AccountPortfolioSnapshot> getPortfolioPerformance(@Param("agentName") String agentName,
                                                          @Param("fromDate") Instant fromDate);
    
    /**
     * Find latest snapshot by account
     */
    AccountPortfolioSnapshot findTopByAccountOrderByTimestampDesc(TradingAccount account);
    
    /**
     * Find snapshots with total value greater than specified amount
     */
    @Query("SELECT aps FROM AccountPortfolioSnapshot aps WHERE aps.totalValue > :minValue ORDER BY aps.timestamp DESC")
    List<AccountPortfolioSnapshot> findSnapshotsWithValueGreaterThan(@Param("minValue") Double minValue);
    
    /**
     * Get average portfolio value for an agent over a period
     */
    @Query("SELECT AVG(aps.totalValue) FROM AccountPortfolioSnapshot aps WHERE aps.account.agent.name = :agentName AND aps.timestamp >= :fromDate")
    Optional<Double> getAveragePortfolioValue(@Param("agentName") String agentName,
                                            @Param("fromDate") Instant fromDate);
    
    /**
     * Get maximum portfolio value for an agent
     */
    @Query("SELECT MAX(aps.totalValue) FROM AccountPortfolioSnapshot aps WHERE aps.account.agent.name = :agentName")
    Optional<Double> getMaxPortfolioValue(@Param("agentName") String agentName);
    
    /**
     * Get minimum portfolio value for an agent
     */
    @Query("SELECT MIN(aps.totalValue) FROM AccountPortfolioSnapshot aps WHERE aps.account.agent.name = :agentName")
    Optional<Double> getMinPortfolioValue(@Param("agentName") String agentName);
    
    /**
     * Count snapshots for an agent
     */
    @Query("SELECT COUNT(aps) FROM AccountPortfolioSnapshot aps WHERE aps.account.agent.name = :agentName")
    Long countSnapshotsByAgent(@Param("agentName") String agentName);
    
    /**
     * Delete old snapshots (older than specified date)
     */
    @Query("DELETE FROM AccountPortfolioSnapshot aps WHERE aps.timestamp < :cutoffDate")
    void deleteSnapshotsOlderThan(@Param("cutoffDate") Instant cutoffDate);
}