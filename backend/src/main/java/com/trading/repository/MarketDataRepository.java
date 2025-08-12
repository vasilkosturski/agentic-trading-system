package com.trading.repository;

import com.trading.entity.MarketData;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface MarketDataRepository extends JpaRepository<MarketData, String> {
    
    /**
     * Find market data by market date
     */
    MarketData findByMarketDate(LocalDate marketDate);
    
    /**
     * Find market data by date string (backward compatibility)
     */
    @Query("SELECT md FROM MarketData md WHERE md.marketDate = :date")
    MarketData findByDate(@Param("date") LocalDate date);
    
    /**
     * Find market data within date range
     */
    @Query("SELECT md FROM MarketData md WHERE md.marketDate BETWEEN :startDate AND :endDate ORDER BY md.marketDate DESC")
    List<MarketData> findByMarketDateBetween(@Param("startDate") LocalDate startDate,
                                           @Param("endDate") LocalDate endDate);
    
    /**
     * Find market data by data source
     */
    List<MarketData> findByDataSourceOrderByMarketDateDesc(String dataSource);
    
    /**
     * Find market data by data tier (JSON query)
     */
    @Query(value = "SELECT * FROM market_data WHERE data_json::jsonb->>'dataTier' = :dataTier ORDER BY market_date DESC", nativeQuery = true)
    List<MarketData> findByDataTier(@Param("dataTier") String dataTier);
    
    /**
     * Find fresh market data (within last day)
     */
    @Query("SELECT md FROM MarketData md WHERE md.createdAt > :cutoffTime ORDER BY md.marketDate DESC")
    List<MarketData> findFreshData(@Param("cutoffTime") LocalDateTime cutoffTime);
    
    /**
     * Get latest market data entry
     */
    @Query("SELECT md FROM MarketData md ORDER BY md.marketDate DESC")
    List<MarketData> findAllOrderByMarketDateDesc();
    
    default Optional<MarketData> findLatestMarketData() {
        List<MarketData> results = findAllOrderByMarketDateDesc();
        return results.isEmpty() ? Optional.empty() : Optional.of(results.get(0));
    }
    
    /**
     * Count market data entries by data source
     */
    Long countByDataSource(String dataSource);
    
    /**
     * Delete old market data (older than specified date)
     */
    @Query("DELETE FROM MarketData md WHERE md.marketDate < :cutoffDate")
    void deleteDataOlderThan(@Param("cutoffDate") LocalDate cutoffDate);
}