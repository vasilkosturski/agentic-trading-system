package com.trading.repository;

import com.trading.entity.AccountHolding;
import com.trading.entity.TradingAccount;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface AccountHoldingRepository extends JpaRepository<AccountHolding, Long> {
    
    /**
     * Find all holdings for a specific account
     */
    List<AccountHolding> findByAccount(TradingAccount account);
    
    /**
     * Find specific holding by account and symbol
     */
    AccountHolding findByAccountAndSymbol(TradingAccount account, String symbol);
    
    /**
     * Find holdings by agent name
     */
    @Query("SELECT ah FROM AccountHolding ah WHERE ah.account.agent.name = :agentName")
    List<AccountHolding> findByAgentName(@Param("agentName") String agentName);
    
    /**
     * Find specific holding by agent and symbol
     */
    @Query("SELECT ah FROM AccountHolding ah WHERE ah.account.agent.name = :agentName AND ah.symbol = :symbol")
    Optional<AccountHolding> findByAgentNameAndSymbol(@Param("agentName") String agentName,
                                                     @Param("symbol") String symbol);
    
    /**
     * Find holdings by symbol across all agents
     */
    List<AccountHolding> findBySymbol(String symbol);
    
    /**
     * Find holdings with quantity greater than zero
     */
    @Query("SELECT ah FROM AccountHolding ah WHERE ah.quantity > 0")
    List<AccountHolding> findActiveHoldings();
    
    /**
     * Find active holdings for a specific agent
     */
    @Query("SELECT ah FROM AccountHolding ah WHERE ah.account.agent.name = :agentName AND ah.quantity > 0")
    List<AccountHolding> findActiveHoldingsByAgent(@Param("agentName") String agentName);
    
    
    /**
     * Get total quantity of a symbol held by an agent
     */
    @Query("SELECT COALESCE(SUM(ah.quantity), 0) FROM AccountHolding ah WHERE ah.account.agent.name = :agentName AND ah.symbol = :symbol")
    Integer getTotalQuantityByAgentAndSymbol(@Param("agentName") String agentName,
                                           @Param("symbol") String symbol);
    
    
    /**
     * Get holdings summary for an agent (count of different symbols)
     */
    @Query("SELECT COUNT(DISTINCT ah.symbol) FROM AccountHolding ah WHERE ah.account.agent.name = :agentName AND ah.quantity > 0")
    Long getUniqueSymbolCountByAgent(@Param("agentName") String agentName);
    
}