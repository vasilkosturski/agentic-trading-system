# PostgreSQL Database - Agentic Trading System

This directory contains database documentation for the Agentic Trading System.

## 🔧 Schema Management

**Schema is managed by JPA auto-DDL** - all tables are automatically created from Java entities.

- **Source of truth**: Java entities in `backend/src/main/java/com/trading/entity/`
- **Auto-DDL mode**: `ddl-auto: update` (preserves data, adds new tables/columns)
- **No manual SQL scripts needed** - JPA handles everything

## 🗄️ Database Schema

### Schemas + Tables

| Schema | Tables |
| ------ | ------ |
| `agents` | `trading_agents`, `agent_logs` |
| `trading` | `trading_accounts`, `account_transactions`, `account_holdings`, `account_portfolio_snapshots` |
| `trading` | `trading_runs`, `research_phases`, `decision_phases`, `execution_phases` |

## 🚀 Deployment

### Normal Deployment (Preserves Data)
```bash
cd deployment/k3s
./deploy-to-k3s.sh
```
- JPA auto-updates schema (adds new tables/columns)
- All existing data preserved
- Safe for production

### Clean Deployment (Wipes Data)
```bash
cd deployment/k3s
./deploy-to-k3s.sh --clean --yes
```
- Drops all schemas and data
- JPA recreates everything from entities
- Use when switching to JPA-managed schema or testing fresh install

## 📊 Data Initialization

Agents and accounts are created automatically:

### Agent Auto-Registration
When agents start for the first time, they automatically:
1. Create their agent record in `agents.trading_agents`
2. Create their account in `trading.trading_accounts`
3. Initialize with $100,000 starting balance

### Trading Agents
- **Warren** - Value investor ($100k initial)
- **George** - Momentum trader ($100k initial)
- **Ray** - Risk parity trader ($100k initial)
- **Cathie** - Growth investor ($100k initial)

## 🔍 Database Access

### From Kubernetes Cluster
```bash
# Connect to database
kubectl exec -it statefulset/postgres -n agentic-trading -- psql -U trading_user -d agentic_trading

# Check tables
\dt agents.*
\dt trading.*
\dt analytics.*

# View sample data
SELECT * FROM agents.trading_agents;
SELECT * FROM trading.trading_accounts;
```

### Query Examples
```sql
-- Get all agents with their account balances
SELECT 
    a.name,
    a.is_active,
    a.risk_tolerance,
    ta.balance
FROM agents.trading_agents a
JOIN trading.trading_accounts ta ON a.id = ta.agent_id;

-- Get recent transactions
SELECT 
    ta.name as agent,
    t.symbol,
    t.transaction_type,
    t.quantity,
    t.price,
    t.timestamp
FROM trading.account_transactions t
JOIN trading.trading_accounts ta ON t.account_id = ta.id
ORDER BY t.timestamp DESC
LIMIT 10;

-- Get portfolio performance
SELECT 
    ta.name as agent,
    s.timestamp,
    s.total_value,
    s.daily_pnl
FROM trading.account_portfolio_snapshots s
JOIN trading.trading_accounts ta ON s.account_id = ta.id
ORDER BY s.timestamp DESC;
```

## 🔧 Maintenance

### Backup Database
```bash
# Create backup
kubectl exec statefulset/postgres -n agentic-trading -- pg_dump -U trading_user agentic_trading > backup.sql

# Restore backup
kubectl exec -i statefulset/postgres -n agentic-trading -- psql -U trading_user -d agentic_trading < backup.sql
```

### Monitor Performance
```bash
# Check database size
kubectl exec statefulset/postgres -n agentic-trading -- psql -U trading_user -d agentic_trading -c "SELECT pg_size_pretty(pg_database_size('agentic_trading'));"

# Check active connections
kubectl exec statefulset/postgres -n agentic-trading -- psql -U trading_user -d agentic_trading -c "SELECT count(*) FROM pg_stat_activity;"
```

## 🔐 Security

### Production Considerations
- **Credentials**: Change default passwords in production
- **SSL/TLS**: Enable encrypted connections
- **Network**: Restrict access to cluster internal traffic
- **Backups**: Implement regular backup strategy

### Current Security
- **Kubernetes Secrets**: Credentials stored securely
- **Network Isolation**: Database only accessible within cluster
- **User Permissions**: Limited to required schemas only

## 📋 Schema Evolution

### Adding New Tables/Columns
1. Create/modify Java entity in `backend/src/main/java/com/trading/entity/`
2. Deploy normally (`./deploy-to-k3s.sh`)
3. JPA automatically creates/updates schema
4. Done!

### Performance Optimization
- **Indexes**: Add via `@Index` annotation on entities
- **Connection Pooling**: Configured in Spring Boot
- **Query Optimization**: Monitor slow queries with `show-sql: true`

---

**Database Version**: PostgreSQL 15  
**Deployment**: Kubernetes StatefulSet  
**Storage**: Persistent Volume (5Gi)  
**Last Updated**: October 30, 2025