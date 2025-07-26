package com.trading.repository;

import com.trading.entity.LogEntry;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface LogRepository extends JpaRepository<LogEntry, Long> {
    
    @Query("SELECT l FROM LogEntry l WHERE l.name = :name ORDER BY l.datetime DESC")
    List<LogEntry> findByNameOrderByDatetimeDesc(@Param("name") String name);
    
    @Query(value = "SELECT * FROM logs WHERE name = :name ORDER BY datetime DESC LIMIT :limit", nativeQuery = true)
    List<LogEntry> findTopByNameOrderByDatetimeDesc(@Param("name") String name, @Param("limit") int limit);
}