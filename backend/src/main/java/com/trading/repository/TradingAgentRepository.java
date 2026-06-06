package com.trading.repository;

import com.trading.entity.TradingAgent;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface TradingAgentRepository extends JpaRepository<TradingAgent, Long> {

    Optional<TradingAgent> findByName(String name);

    Optional<TradingAgent> findByNameIgnoreCase(String name);

    boolean existsByName(String name);

    List<TradingAgent> findByIsActive(Boolean isActive);

    @Query("SELECT ta FROM TradingAgent ta WHERE ta.isActive = true")
    List<TradingAgent> findActiveAgents();

    @Query("SELECT ta FROM TradingAgent ta WHERE ta.totalPnl > :minPnl")
    List<TradingAgent> findAgentsWithPnlAbove(@Param("minPnl") Double minPnl);

    @Query("SELECT ta FROM TradingAgent ta WHERE ta.lastActivity > :cutoffDate")
    List<TradingAgent> findAgentsActiveAfter(@Param("cutoffDate") LocalDateTime cutoffDate);

    @Query("SELECT ta FROM TradingAgent ta ORDER BY ta.totalPnl DESC")
    List<TradingAgent> findAgentsRankedByPnl();

    @Query("SELECT ta FROM TradingAgent ta ORDER BY ta.totalTrades DESC")
    List<TradingAgent> findAgentsRankedByActivity();

    @Query("SELECT ta FROM TradingAgent ta WHERE ta.totalTrades > :minTrades")
    List<TradingAgent> findAgentsWithTradesAbove(@Param("minTrades") Integer minTrades);

    @Query("SELECT AVG(ta.totalPnl), AVG(ta.totalTrades) FROM TradingAgent ta WHERE ta.isActive = true")
    Object[] getAveragePerformanceMetrics();

    @Query("SELECT ta FROM TradingAgent ta WHERE ta.isActive = true ORDER BY ta.totalPnl DESC LIMIT :limit")
    List<TradingAgent> findTopPerformingAgents(@Param("limit") int limit);

    @Query("UPDATE TradingAgent ta SET ta.lastActivity = :activeDate WHERE ta.name = :name")
    void updateLastActiveDate(@Param("name") String name, @Param("activeDate") LocalDateTime activeDate);
}
