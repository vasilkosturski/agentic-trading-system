package com.trading.repository;

import com.trading.entity.AccountTransaction;
import com.trading.entity.TradingAccount;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface AccountTransactionRepository extends JpaRepository<AccountTransaction, Long> {
    
    /**
     * Find all transactions for a specific trading account
     */
    @Query("SELECT at FROM AccountTransaction at WHERE at.account = :account ORDER BY at.timestamp DESC")
    List<AccountTransaction> findByTradingAccountOrderByTransactionDateDesc(@Param("account") TradingAccount tradingAccount);
    
    /**
     * Find transactions by agent name
     */
    @Query("SELECT at FROM AccountTransaction at WHERE at.account.agent.name = :agentName ORDER BY at.timestamp DESC")
    List<AccountTransaction> findByAgentNameOrderByTransactionDateDesc(@Param("agentName") String agentName);
    
    /**
     * Find transactions by symbol
     */
    List<AccountTransaction> findBySymbolOrderByTimestampDesc(String symbol);
    
    /**
     * Find transactions by type (BUY, SELL)
     */
    List<AccountTransaction> findByTransactionTypeOrderByTimestampDesc(String transactionType);
    
    /**
     * Find transactions within date range
     */
    @Query("SELECT at FROM AccountTransaction at WHERE at.timestamp BETWEEN :startDate AND :endDate ORDER BY at.timestamp DESC")
    List<AccountTransaction> findByTransactionDateBetween(@Param("startDate") LocalDateTime startDate,
                                                         @Param("endDate") LocalDateTime endDate);
    
    /**
     * Find recent transactions for an agent (last N transactions)
     */
    @Query(value = "SELECT * FROM trading.account_transactions at " +
                   "JOIN trading.trading_accounts ta ON at.account_id = ta.id " +
                   "JOIN agents.trading_agents ag ON ta.agent_id = ag.id " +
                   "WHERE ag.name = :agentName " +
                   "ORDER BY at.timestamp DESC LIMIT :limit", nativeQuery = true)
    List<AccountTransaction> findRecentTransactionsByAgent(@Param("agentName") String agentName,
                                                          @Param("limit") int limit);
    
    /**
     * Get total transaction volume for an agent
     */
    @Query("SELECT COALESCE(SUM(at.quantity * at.price), 0) FROM AccountTransaction at WHERE at.account.agent.name = :agentName")
    Double getTotalTransactionVolumeByAgent(@Param("agentName") String agentName);
    
    /**
     * Get transaction count by type for an agent
     */
    @Query("SELECT COUNT(at) FROM AccountTransaction at WHERE at.account.agent.name = :agentName AND at.transactionType = :transactionType")
    Long getTransactionCountByAgentAndType(@Param("agentName") String agentName,
                                          @Param("transactionType") String transactionType);
    
    /**
     * Find transactions by agent and symbol
     */
    @Query("SELECT at FROM AccountTransaction at WHERE at.account.agent.name = :agentName AND at.symbol = :symbol ORDER BY at.timestamp DESC")
    List<AccountTransaction> findByAgentNameAndSymbol(@Param("agentName") String agentName,
                                                     @Param("symbol") String symbol);
    
    /**
     * Count transactions by trading account
     */
    Long countByAccount(TradingAccount account);
    
    /**
     * Find transactions by account ordered by timestamp descending (PostgreSQL schema)
     */
    @Query("SELECT at FROM AccountTransaction at WHERE at.account = :account ORDER BY at.timestamp DESC")
    List<AccountTransaction> findByAccountOrderByTimestampDesc(@Param("account") TradingAccount account);
}