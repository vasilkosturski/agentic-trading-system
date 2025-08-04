# COMMIT 1: Enhanced Database Foundation - Detailed Technical Specifications

## Current State Analysis

### What We Have (Good Foundation)
- **Trader Entity**: Well-structured with balance tracking, strategy field, and relationships
- **Transaction Entity**: Has rationale field (`reason`), proper relationships, and transaction types
- **Holding Entity**: Sophisticated with average price calculation and P&L tracking
- **PostgreSQL Setup**: Production-ready database configuration
- **JPA Relationships**: Properly configured with lazy loading and cascading

### What Needs Enhancement
- **Missing Agent-Specific Features**: No agent decision logging or activity tracking
- **Limited Portfolio Analytics**: No time-series portfolio value tracking
- **No Market Data Caching**: Missing infrastructure for real-time price management
- **Database Migration Strategy**: Currently using `ddl-auto: update` (not production-ready)

---

## Code Cleanup Strategy

### 1. Database Configuration Modernization
**Current Issue**: Using `ddl-auto: update` and PostgreSQL for development
**Solution**: Switch to Flyway migrations + SQLite for development, PostgreSQL for production

```yaml
# New application.yml structure
spring:
  profiles:
    active: development
  
---
spring:
  config:
    activate:
      on-profile: development
  datasource:
    url: jdbc:sqlite:./data/trading.db
    driver-class-name: org.sqlite.JDBC
  jpa:
    hibernate:
      ddl-auto: validate
    database-platform: org.hibernate.community.dialect.SQLiteDialect

---
spring:
  config:
    activate:
      on-profile: production
  datasource:
    url: jdbc:postgresql://localhost:5432/trading_db
    username: ${DB_USERNAME:trading_user}
    password: ${DB_PASSWORD:trading_pass}
    driver-class-name: org.postgresql.Driver
  jpa:
    hibernate:
      ddl-auto: validate
    database-platform: org.hibernate.dialect.PostgreSQLDialect
```

### 2. Entity Refactoring Strategy
**Keep**: Current entities are well-designed, we'll enhance rather than replace
**Enhance**: Add new entities for MCP-specific functionality
**Rename**: `Trader` → `Account` (aligns with MCP reference architecture)

---

## New Database Schema Additions

### 1. Enhanced Account Entity (Renamed from Trader)
```sql
-- Rename existing table and enhance
ALTER TABLE traders RENAME TO accounts;
ALTER TABLE accounts ADD COLUMN strategy_details TEXT; -- JSON field for complex strategies
ALTER TABLE accounts ADD COLUMN last_activity_at TIMESTAMP;
ALTER TABLE accounts ADD COLUMN agent_type VARCHAR(20) DEFAULT 'AUTONOMOUS'; -- AUTONOMOUS, MANUAL, RESEARCH
```

### 2. Portfolio Value Time Series
```sql
CREATE TABLE portfolio_value_history (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    portfolio_value DECIMAL(15,2) NOT NULL,
    cash_balance DECIMAL(15,2) NOT NULL,
    holdings_value DECIMAL(15,2) NOT NULL,
    total_pnl DECIMAL(15,2),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_account_timestamp (account_id, timestamp),
    INDEX idx_timestamp (timestamp)
);
```

### 3. Agent Decision Logs
```sql
CREATE TABLE agent_logs (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    log_type VARCHAR(20) NOT NULL, -- 'trace', 'agent', 'function', 'generation', 'response', 'account'
    message TEXT NOT NULL,
    context_data JSON, -- Store additional context like market conditions, reasoning
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_account_type_timestamp (account_id, log_type, timestamp),
    INDEX idx_timestamp (timestamp)
);
```

### 4. Market Data Cache
```sql
CREATE TABLE market_data_cache (
    symbol VARCHAR(10) PRIMARY KEY,
    current_price DECIMAL(10,4) NOT NULL,
    previous_close DECIMAL(10,4),
    price_change DECIMAL(10,4),
    price_change_percent DECIMAL(6,3),
    volume BIGINT,
    market_cap BIGINT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(20) DEFAULT 'POLYGON', -- POLYGON, MOCK, MANUAL
    
    INDEX idx_last_updated (last_updated),
    INDEX idx_source (source)
);
```

### 5. Enhanced Transaction Tracking
```sql
-- Add columns to existing transactions table
ALTER TABLE transactions ADD COLUMN agent_decision_id BIGINT REFERENCES agent_logs(id);
ALTER TABLE transactions ADD COLUMN market_price_at_time DECIMAL(10,4);
ALTER TABLE transactions ADD COLUMN spread_applied DECIMAL(6,4) DEFAULT 0.002;
ALTER TABLE transactions ADD COLUMN execution_context JSON; -- Store market conditions, news, etc.
```

---

## New Entity Classes

### 1. Account Entity (Enhanced Trader)
```java
@Entity
@Table(name = "accounts")
public class Account {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(nullable = false, unique = true, length = 50)
    private String name;
    
    @Column(nullable = false, length = 100)
    private String strategy;
    
    @Column(name = "strategy_details", columnDefinition = "TEXT")
    private String strategyDetails; // JSON string for complex strategy config
    
    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal balance;
    
    @Column(name = "initial_balance", nullable = false, precision = 15, scale = 2)
    private BigDecimal initialBalance = new BigDecimal("10000.00");
    
    @Enumerated(EnumType.STRING)
    @Column(name = "agent_type", nullable = false)
    private AgentType agentType = AgentType.AUTONOMOUS;
    
    @Column(name = "last_activity_at")
    private LocalDateTime lastActivityAt;
    
    // Relationships
    @OneToMany(mappedBy = "account", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Transaction> transactions = new ArrayList<>();
    
    @OneToMany(mappedBy = "account", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Holding> holdings = new ArrayList<>();
    
    @OneToMany(mappedBy = "account", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<PortfolioValueHistory> portfolioHistory = new ArrayList<>();
    
    @OneToMany(mappedBy = "account", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<AgentLog> agentLogs = new ArrayList<>();
    
    // Business methods
    public void recordActivity() {
        this.lastActivityAt = LocalDateTime.now();
    }
    
    public enum AgentType {
        AUTONOMOUS, MANUAL, RESEARCH
    }
}
```

### 2. PortfolioValueHistory Entity
```java
@Entity
@Table(name = "portfolio_value_history")
public class PortfolioValueHistory {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "account_id", nullable = false)
    private Account account;
    
    @Column(name = "portfolio_value", nullable = false, precision = 15, scale = 2)
    private BigDecimal portfolioValue;
    
    @Column(name = "cash_balance", nullable = false, precision = 15, scale = 2)
    private BigDecimal cashBalance;
    
    @Column(name = "holdings_value", nullable = false, precision = 15, scale = 2)
    private BigDecimal holdingsValue;
    
    @Column(name = "total_pnl", precision = 15, scale = 2)
    private BigDecimal totalPnl;
    
    @Column(nullable = false)
    private LocalDateTime timestamp;
    
    @PrePersist
    public void prePersist() {
        if (timestamp == null) {
            timestamp = LocalDateTime.now();
        }
    }
}
```

### 3. AgentLog Entity
```java
@Entity
@Table(name = "agent_logs")
public class AgentLog {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "account_id", nullable = false)
    private Account account;
    
    @Enumerated(EnumType.STRING)
    @Column(name = "log_type", nullable = false)
    private LogType logType;
    
    @Column(nullable = false, columnDefinition = "TEXT")
    private String message;
    
    @Column(name = "context_data", columnDefinition = "TEXT")
    private String contextData; // JSON string
    
    @Column(nullable = false)
    private LocalDateTime timestamp;
    
    public enum LogType {
        TRACE, AGENT, FUNCTION, GENERATION, RESPONSE, ACCOUNT
    }
}
```

### 4. MarketDataCache Entity
```java
@Entity
@Table(name = "market_data_cache")
public class MarketDataCache {
    @Id
    @Column(length = 10)
    private String symbol;
    
    @Column(name = "current_price", nullable = false, precision = 10, scale = 4)
    private BigDecimal currentPrice;
    
    @Column(name = "previous_close", precision = 10, scale = 4)
    private BigDecimal previousClose;
    
    @Column(name = "price_change", precision = 10, scale = 4)
    private BigDecimal priceChange;
    
    @Column(name = "price_change_percent", precision = 6, scale = 3)
    private BigDecimal priceChangePercent;
    
    private Long volume;
    
    @Column(name = "market_cap")
    private Long marketCap;
    
    @Column(name = "last_updated", nullable = false)
    private LocalDateTime lastUpdated;
    
    @Enumerated(EnumType.STRING)
    private DataSource source = DataSource.POLYGON;
    
    public enum DataSource {
        POLYGON, MOCK, MANUAL
    }
}
```

---

## Migration Strategy

### 1. Flyway Migration Files
```sql
-- V1__Initial_Schema.sql (baseline from current state)
-- V2__Rename_Traders_To_Accounts.sql
-- V3__Add_Portfolio_Value_History.sql
-- V4__Add_Agent_Logs.sql
-- V5__Add_Market_Data_Cache.sql
-- V6__Enhance_Transactions.sql
```

### 2. Data Migration Plan
1. **Backup existing data** before any schema changes
2. **Rename traders to accounts** with data preservation
3. **Seed initial portfolio history** from current trader balances
4. **Create default agent logs** for existing transactions
5. **Initialize market data cache** with current stock prices

---

## Repository Enhancements

### New Repository Interfaces
```java
@Repository
public interface AccountRepository extends JpaRepository<Account, Long> {
    Optional<Account> findByName(String name);
    List<Account> findByAgentType(Account.AgentType agentType);
    List<Account> findByIsActiveTrue();
}

@Repository
public interface PortfolioValueHistoryRepository extends JpaRepository<PortfolioValueHistory, Long> {
    List<PortfolioValueHistory> findByAccountOrderByTimestampDesc(Account account);
    List<PortfolioValueHistory> findByAccountAndTimestampBetween(Account account, LocalDateTime start, LocalDateTime end);
}

@Repository
public interface AgentLogRepository extends JpaRepository<AgentLog, Long> {
    List<AgentLog> findByAccountAndLogTypeOrderByTimestampDesc(Account account, AgentLog.LogType logType);
    List<AgentLog> findByAccountOrderByTimestampDesc(Account account, Pageable pageable);
}

@Repository
public interface MarketDataCacheRepository extends JpaRepository<MarketDataCache, String> {
    List<MarketDataCache> findByLastUpdatedBefore(LocalDateTime cutoff);
    List<MarketDataCache> findBySource(MarketDataCache.DataSource source);
}
```

---

## Configuration Updates

### 1. Build Dependencies (build.gradle.kts)
```kotlin
dependencies {
    // Database
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.flywaydb:flyway-core")
    
    // SQLite for development
    runtimeOnly("org.xerial:sqlite-jdbc")
    implementation("org.hibernate.orm:hibernate-community-dialects")
    
    // PostgreSQL for production
    runtimeOnly("org.postgresql:postgresql")
    
    // JSON processing
    implementation("com.fasterxml.jackson.core:jackson-databind")
}
```

### 2. Application Properties Structure
```yaml
# application.yml
spring:
  application:
    name: agentic-trading-system
  profiles:
    active: ${SPRING_PROFILES_ACTIVE:development}
  flyway:
    enabled: true
    locations: classpath:db/migration
    baseline-on-migrate: true

# Logging configuration
logging:
  level:
    com.trading: INFO
    org.flywaydb: INFO
  pattern:
    console: "%d{yyyy-MM-dd HH:mm:ss} - %msg%n"
```

---

## Success Criteria for COMMIT 1

### Functional Requirements
- [ ] All existing data preserved during migration
- [ ] New entities created with proper relationships
- [ ] Flyway migrations execute successfully
- [ ] SQLite works for development, PostgreSQL for production
- [ ] All repository methods functional
- [ ] Portfolio value history tracking operational

### Technical Requirements
- [ ] Zero data loss during migration
- [ ] Database constraints properly enforced
- [ ] Indexes created for performance
- [ ] JSON fields properly handled
- [ ] Enum types correctly mapped
- [ ] Audit fields (created_at, updated_at) working

### Testing Requirements
- [ ] Unit tests for all new entities
- [ ] Integration tests for repositories
- [ ] Migration tests with sample data
- [ ] Performance tests for time-series queries
- [ ] Cross-database compatibility tests

---

## Estimated Timeline: 4-6 hours
- **Schema Design & Migration Scripts**: 2 hours
- **Entity Classes & Repositories**: 2 hours  
- **Configuration & Testing**: 1-2 hours
- **Data Migration & Validation**: 1 hour

This foundation will support all subsequent commits by providing the robust data model needed for autonomous AI trading with full audit trails and performance tracking.