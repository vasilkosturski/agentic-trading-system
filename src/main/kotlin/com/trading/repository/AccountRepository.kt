package com.trading.repository

import com.trading.entity.Account
import com.trading.entity.LogEntry
import com.trading.entity.MarketData
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import org.springframework.stereotype.Repository

@Repository
interface AccountRepository : JpaRepository<Account, String> {
    fun findByName(name: String): Account?
}

@Repository
interface LogRepository : JpaRepository<LogEntry, Long> {
    @Query("SELECT l FROM LogEntry l WHERE l.name = :name ORDER BY l.datetime DESC")
    fun findByNameOrderByDatetimeDesc(name: String): List<LogEntry>
    
    @Query("SELECT l FROM LogEntry l WHERE l.name = :name ORDER BY l.datetime DESC LIMIT :limit")
    fun findTopByNameOrderByDatetimeDesc(name: String, limit: Int): List<LogEntry>
}

@Repository
interface MarketDataRepository : JpaRepository<MarketData, String> {
    fun findByDate(date: String): MarketData?
}