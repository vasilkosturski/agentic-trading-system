package com.trading.repository;

import com.trading.entity.TradingAccount;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.List;

@Repository
public interface TradingAccountRepository extends JpaRepository<TradingAccount, Long> {
    
    /**
     * Find trading account by agent name (using agent relationship)
     */
    @Query("SELECT ta FROM TradingAccount ta WHERE ta.agent.name = :agentName")
    Optional<TradingAccount> findByAgentName(@Param("agentName") String agentName);
    
    /**
     * Find trading account by name (for PostgreSQL schema)
     */
    TradingAccount findByName(String name);
    
    /**
     * Find all accounts for a specific agent (case-insensitive by account name)
     */
    @Query("SELECT ta FROM TradingAccount ta WHERE UPPER(ta.name) = UPPER(:agentName)")
    List<TradingAccount> findByAgentNameIgnoreCase(@Param("agentName") String agentName);
    
    /**
     * Check if account exists by agent name
     */
    @Query("SELECT COUNT(ta) > 0 FROM TradingAccount ta WHERE ta.agent.name = :agentName")
    boolean existsByAgentName(@Param("agentName") String agentName);
    
    /**
     * Find accounts with balance greater than specified amount
     */
    @Query("SELECT ta FROM TradingAccount ta WHERE ta.balance > :minBalance")
    List<TradingAccount> findAccountsWithBalanceGreaterThan(@Param("minBalance") Double minBalance);
    
    /**
     * Get total portfolio value for an agent (balance + holdings value)
     */
    @Query("SELECT ta.balance + COALESCE(SUM(ah.quantity * ah.currentPrice), 0) " +
           "FROM TradingAccount ta " +
           "LEFT JOIN ta.holdings ah " +
           "WHERE ta.agent.name = :agentName " +
           "GROUP BY ta.id, ta.balance")
    Optional<Double> getTotalPortfolioValue(@Param("agentName") String agentName);
    
    /**
     * Find accounts by strategy type
     */
    List<TradingAccount> findByStrategyContainingIgnoreCase(String strategy);
}