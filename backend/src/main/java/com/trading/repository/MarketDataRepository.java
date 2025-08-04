package com.trading.repository;

import com.trading.entity.MarketData;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface MarketDataRepository extends JpaRepository<MarketData, String> {
    MarketData findByDate(String date);
}