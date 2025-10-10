package com.trading.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.time.Instant;

@Entity
@Table(name = "agent_logs", schema = "agents")
@Getter
@Setter
@NoArgsConstructor
public class LogEntry {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "agent_name", nullable = false)
    private String name;

    @Column(name = "log_datetime", nullable = false)
    private Instant datetime = Instant.now();

    @Column(name = "log_type", nullable = false)
    private String type;

    @Column(name = "log_message", columnDefinition = "TEXT")
    private String message;

    @Column(name = "log_level")
    private String logLevel = "INFO"; // DEBUG, INFO, WARN, ERROR

    @Column(name = "session_id")
    private String sessionId;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();
    
    // Constructor with parameters
    public LogEntry(String name, String type, String message) {
        this.name = name;
        this.type = type;
        this.message = message;
    }
    
    public LogEntry(String name, String type, String message, String logLevel) {
        this.name = name;
        this.type = type;
        this.message = message;
        this.logLevel = logLevel;
    }
    
    // Business methods
    public boolean isError() {
        return "ERROR".equalsIgnoreCase(logLevel);
    }
    
    public boolean isWarning() {
        return "WARN".equalsIgnoreCase(logLevel);
    }
    
    public boolean isInfo() {
        return "INFO".equalsIgnoreCase(logLevel);
    }
    
    public boolean isDebug() {
        return "DEBUG".equalsIgnoreCase(logLevel);
    }
}