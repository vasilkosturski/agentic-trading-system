package com.trading.repository;

import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.entity.TradingAccount;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;

@Repository
public interface AccountPortfolioSnapshotRepository extends JpaRepository<AccountPortfolioSnapshot, Long> {

    /**
     * Find all snapshots ordered by timestamp descending, eagerly loading account and agent.
     */
    @Query("SELECT aps FROM AccountPortfolioSnapshot aps " +
           "JOIN FETCH aps.account a " +
           "JOIN FETCH a.agent " +
           "ORDER BY aps.timestamp DESC")
    List<AccountPortfolioSnapshot> findAllOrderByTimestampDesc();

    /**
     * Find snapshots by agent name, eagerly loading account and agent.
     */
    @Query("SELECT aps FROM AccountPortfolioSnapshot aps " +
           "JOIN FETCH aps.account a " +
           "JOIN FETCH a.agent " +
           "WHERE a.agent.name = :agentName " +
           "ORDER BY aps.timestamp DESC")
    List<AccountPortfolioSnapshot> findByAgentNameOrderByTimestampDesc(@Param("agentName") String agentName);

    /**
     * Find snapshots within date range, eagerly loading account and agent.
     */
    @Query("SELECT aps FROM AccountPortfolioSnapshot aps " +
           "JOIN FETCH aps.account a " +
           "JOIN FETCH a.agent " +
           "WHERE aps.timestamp BETWEEN :startDate AND :endDate " +
           "ORDER BY aps.timestamp DESC")
    List<AccountPortfolioSnapshot> findByTimestampBetween(@Param("startDate") Instant startDate,
                                                         @Param("endDate") Instant endDate);

    /**
     * Find snapshots by agent name and date range, eagerly loading account and agent.
     */
    @Query("SELECT aps FROM AccountPortfolioSnapshot aps " +
           "JOIN FETCH aps.account a " +
           "JOIN FETCH a.agent " +
           "WHERE a.agent.name = :agentName " +
           "AND aps.timestamp BETWEEN :startDate AND :endDate " +
           "ORDER BY aps.timestamp DESC")
    List<AccountPortfolioSnapshot> findByAgentNameAndDateRange(@Param("agentName") String agentName,
                                                              @Param("startDate") Instant startDate,
                                                              @Param("endDate") Instant endDate);

    /**
     * Find latest snapshot by account (used by AccountService for snapshot creation).
     */
    AccountPortfolioSnapshot findTopByAccountOrderByTimestampDesc(TradingAccount account);
}
