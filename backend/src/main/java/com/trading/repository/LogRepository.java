package com.trading.repository;

import com.trading.entity.LogEntry;
import java.time.LocalDateTime;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface LogRepository extends JpaRepository<LogEntry, Long> {

    /**
     * Find logs by name ordered by datetime (descending)
     */
    @Query("SELECT l FROM LogEntry l WHERE l.name = :name ORDER BY l.datetime DESC")
    List<LogEntry> findByNameOrderByDatetimeDesc(@Param("name") String name);

    /**
     * Find top N logs by name ordered by datetime (descending)
     */
    @Query(
            value = "SELECT * FROM agents.logs WHERE name = :name ORDER BY datetime DESC LIMIT :limit",
            nativeQuery = true)
    List<LogEntry> findTopByNameOrderByDatetimeDesc(@Param("name") String name, @Param("limit") int limit);

    /**
     * Find logs by log level
     */
    List<LogEntry> findByLogLevelOrderByDatetimeDesc(String logLevel);

    /**
     * Find logs by session ID
     */
    List<LogEntry> findBySessionIdOrderByDatetimeDesc(String sessionId);

    /**
     * Find logs within date range
     */
    @Query("SELECT l FROM LogEntry l WHERE l.datetime BETWEEN :startDate AND :endDate ORDER BY l.datetime DESC")
    List<LogEntry> findByDatetimeBetween(
            @Param("startDate") LocalDateTime startDate, @Param("endDate") LocalDateTime endDate);

    /**
     * Find logs by name and level
     */
    @Query("SELECT l FROM LogEntry l WHERE l.name = :name AND l.logLevel = :logLevel ORDER BY l.datetime DESC")
    List<LogEntry> findByNameAndLogLevel(@Param("name") String name, @Param("logLevel") String logLevel);

    /**
     * Find error logs for an agent
     */
    @Query("SELECT l FROM LogEntry l WHERE l.name = :name AND l.logLevel = 'ERROR' ORDER BY l.datetime DESC")
    List<LogEntry> findErrorLogsByName(@Param("name") String name);

    /**
     * Find recent logs across all agents
     */
    @Query("SELECT l FROM LogEntry l ORDER BY l.datetime DESC LIMIT :limit")
    List<LogEntry> findRecentLogs(@Param("limit") int limit);

    /**
     * Count logs by name
     */
    Long countByName(String name);

    /**
     * Count logs by level
     */
    Long countByLogLevel(String logLevel);

    /**
     * Delete old logs (older than specified date)
     */
    @Query("DELETE FROM LogEntry l WHERE l.datetime < :cutoffDate")
    void deleteLogsOlderThan(@Param("cutoffDate") LocalDateTime cutoffDate);

    /**
     * Find logs containing specific message text
     */
    @Query("SELECT l FROM LogEntry l WHERE l.message LIKE %:messageText% ORDER BY l.datetime DESC")
    List<LogEntry> findByMessageContaining(@Param("messageText") String messageText);
}
