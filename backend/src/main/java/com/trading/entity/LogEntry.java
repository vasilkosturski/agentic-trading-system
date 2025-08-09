package com.trading.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "agent_logs", schema = "agents")
public class LogEntry {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "agent_name", nullable = false)
    private String name;
    
    @Column(name = "log_datetime", nullable = false)
    private LocalDateTime datetime = LocalDateTime.now();
    
    @Column(name = "log_type", nullable = false)
    private String type;
    
    @Column(name = "log_message", columnDefinition = "TEXT")
    private String message;
    
    @Column(name = "log_level")
    private String logLevel = "INFO"; // DEBUG, INFO, WARN, ERROR
    
    @Column(name = "session_id")
    private String sessionId;
    
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();
    
    // Constructors
    public LogEntry() {}
    
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
    
    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public LocalDateTime getDatetime() { return datetime; }
    public void setDatetime(LocalDateTime datetime) { this.datetime = datetime; }
    
    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
    
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    
    public String getLogLevel() { return logLevel; }
    public void setLogLevel(String logLevel) { this.logLevel = logLevel; }
    
    public String getSessionId() { return sessionId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }
    
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}