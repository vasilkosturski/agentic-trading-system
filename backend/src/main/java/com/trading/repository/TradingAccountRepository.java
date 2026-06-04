package com.trading.repository;

import com.trading.entity.TradingAccount;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface TradingAccountRepository extends JpaRepository<TradingAccount, Long> {

    /**
     * Find trading account by agent name (using agent relationship)
     */
    @Query("SELECT ta FROM TradingAccount ta WHERE ta.agent.name = :agentName")
    Optional<TradingAccount> findByAgentName(@Param("agentName") String agentName);

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
}
