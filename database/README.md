# PostgreSQL Database - Agentic Trading System

This directory contains PostgreSQL initialization scripts for the Agentic Trading System deployed on Kubernetes.

## 📁 Files

| File | Purpose | Description |
|------|---------|-------------|
| [`init/01-init-database.sql`](init/01-init-database.sql) | Schema Setup | Creates schemas, extensions, and permissions |
| [`init/02-create-schema.sql`](init/02-create-schema.sql) | Tables & Data | Complete table definitions with sample data |

## 🗄️ Database Schema

### Schemas
- **`trading`** - Core trading data (accounts, transactions, holdings)
- **`agents`** - Agent management and logging
- **`analytics`** - Performance metrics and analytics

### Key Tables

#### Agents Schema
- **`trading_agents`** - Agent definitions, status, and performance metrics
- **`agent_logs`** - Agent activity and decision logging

#### Trading Schema
- **`trading_accounts`** - Account balances and agent associations
- **`account_transactions`** - Complete trade history
- **`account_holdings`** - Current stock positions
- **`account_portfolio_snapshots`** - Historical portfolio values
- **`market_data`** - Market data cache

#### Analytics Schema
- **`performance_metrics`** - Agent performance calculations
- **`risk_metrics`** - Risk analysis and VaR calculations

## 🚀 Deployment

### Kubernetes Deployment
The database is automatically initialized when deployed via:

```bash
# Single command deployment
./deploy-to-k3s.sh
```

### Manual Initialization
If you need to run the scripts manually:

```bash
# Get PostgreSQL pod name
POSTGRES_POD=$(kubectl get pods -n agentic-trading -l app=postgres -o jsonpath='{.items[0].metadata.name}')

# Run initialization scripts
kubectl exec -n agentic-trading $POSTGRES_POD -- psql -U trading_user -d agentic_trading -f /tmp/01-init-database.sql
kubectl exec -n agentic-trading $POSTGRES_POD -- psql -U trading_user -d agentic_trading -f /tmp/02-create-schema.sql
```

## 📊 Sample Data

The system includes realistic sample data:

### Trading Agents
- **Warren** - Value investor (30% risk tolerance, weekly trading)
- **George** - Momentum trader (70% risk tolerance, daily trading)
- **Ray** - Risk parity trader (50% risk tolerance, monthly trading)
- **Cathie** - Growth investor (80% risk tolerance, weekly trading)

### Trading Accounts
- **Warren**: $100,000 initial balance
- **George**: $50,000 initial balance
- **Ray**: $75,000 initial balance
- **Cathie**: $60,000 initial balance

### Sample Transactions
- **5 Recent trades** across all agents
- **Realistic symbols**: AAPL, MSFT, TSLA, GOOGL, NVDA
- **Trade rationales**: AI-generated reasoning for each trade

### Portfolio History
- **7 days** of portfolio snapshots for each agent
- **Performance tracking** with daily values
- **Chart data** for frontend visualization

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

### Adding New Tables
1. Create migration SQL file
2. Apply via kubectl exec
3. Update JPA entities in backend
4. Test with sample data

### Performance Optimization
- **Indexes**: Optimized for common queries
- **Partitioning**: Consider for large transaction tables
- **Connection Pooling**: Configured in Spring Boot
- **Query Optimization**: Monitor slow queries

---

**Database Version**: PostgreSQL 15  
**Deployment**: Kubernetes StatefulSet  
**Storage**: Persistent Volume (5Gi)  
**Last Updated**: September 15, 2025