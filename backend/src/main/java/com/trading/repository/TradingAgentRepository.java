package com.trading.repository;

import com.trading.entity.TradingAgent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface TradingAgentRepository extends JpaRepository<TradingAgent, Long> {
    
    /**
     * Find trading agent by name
     */
    Optional<TradingAgent> findByName(String name);
    
    /**
     * Find trading agent by name (case insensitive)
     */
    Optional<TradingAgent> findByNameIgnoreCase(String name);
    
    /**
     * Check if agent exists by name
     */
    boolean existsByName(String name);
    
    /**
     * Find agents by active status
     */
    List<TradingAgent> findByIsActive(Boolean isActive);
    
    /**
     * Find active agents
     */
    @Query("SELECT ta FROM TradingAgent ta WHERE ta.isActive = true")
    List<TradingAgent> findActiveAgents();
    
    
    /**
     * Find agents with P&L above threshold
     */
    @Query("SELECT ta FROM TradingAgent ta WHERE ta.totalPnl > :minPnl")
    List<TradingAgent> findAgentsWithPnlAbove(@Param("minPnl") Double minPnl);
    
    /**
     * Find agents last active after specified date
     */
    @Query("SELECT ta FROM TradingAgent ta WHERE ta.lastActivity > :cutoffDate")
    List<TradingAgent> findAgentsActiveAfter(@Param("cutoffDate") LocalDateTime cutoffDate);
    
    /**
     * Get agent performance ranking by total P&L
     */
    @Query("SELECT ta FROM TradingAgent ta ORDER BY ta.totalPnl DESC")
    List<TradingAgent> findAgentsRankedByPnl();
    
    /**
     * Get agent performance ranking by total trades (activity)
     */
    @Query("SELECT ta FROM TradingAgent ta ORDER BY ta.totalTrades DESC")
    List<TradingAgent> findAgentsRankedByActivity();
    
    /**
     * Find agents with total trades above threshold
     */
    @Query("SELECT ta FROM TradingAgent ta WHERE ta.totalTrades > :minTrades")
    List<TradingAgent> findAgentsWithTradesAbove(@Param("minTrades") Integer minTrades);
    
    /**
     * Get average performance metrics across all active agents
     */
    @Query("SELECT AVG(ta.totalPnl), AVG(ta.totalTrades) FROM TradingAgent ta WHERE ta.isActive = true")
    Object[] getAveragePerformanceMetrics();
    
    /**
     * Find top performing agents (by total P&L)
     */
    @Query("SELECT ta FROM TradingAgent ta WHERE ta.isActive = true ORDER BY ta.totalPnl DESC LIMIT :limit")
    List<TradingAgent> findTopPerformingAgents(@Param("limit") int limit);
    
    /**
     * Update agent last active date
     */
    @Query("UPDATE TradingAgent ta SET ta.lastActivity = :activeDate WHERE ta.name = :name")
    void updateLastActiveDate(@Param("name") String name, @Param("activeDate") LocalDateTime activeDate);
}