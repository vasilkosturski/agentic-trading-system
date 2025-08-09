# PostgreSQL Database Setup

This directory contains the PostgreSQL configuration and setup files for the Agentic Trading System.

## Quick Start

### 1. Start PostgreSQL with Docker Compose

```bash
# From the project root directory
docker-compose -f docker-compose.postgresql.yml up -d
```

This will start:
- **PostgreSQL 15** on port `5432`

### 2. Configure Application

```bash
# Copy PostgreSQL environment configuration
cp .env.postgresql .env

# Start the Spring Boot application with PostgreSQL profile
cd backend
./gradlew bootRun --args='--spring.profiles.active=postgresql'
```

### 3. Verify Setup

- **Database**: Connect to `localhost:5432` with credentials:
  - Database: `agentic_trading`
  - Username: `trading_user`
  - Password: `trading_password`

## Configuration Details

### Database Credentials

| Component | Value |
|-----------|-------|
| Host | `localhost` |
| Port | `5432` |
| Database | `agentic_trading` |
| Username | `trading_user` |
| Password | `trading_password` |

### Environment Variables

The application supports these environment variables for PostgreSQL:

```bash
DB_HOST=localhost          # PostgreSQL host
DB_PORT=5432              # PostgreSQL port
DB_NAME=agentic_trading   # Database name
DB_USERNAME=trading_user  # Database username
DB_PASSWORD=trading_password # Database password
SPRING_PROFILES_ACTIVE=postgresql # Spring profile
```

### Connection Pool Settings

The application uses HikariCP with these optimized settings:
- **Maximum Pool Size**: 20 connections
- **Minimum Idle**: 5 connections
- **Connection Timeout**: 20 seconds
- **Idle Timeout**: 5 minutes
- **Leak Detection**: 60 seconds

## Database Schema

The application uses **Hibernate JPA** with `ddl-auto: update` to automatically create and update the database schema. The following schemas are created:

- `trading` - Core trading data (accounts, transactions, positions)
- `agents` - Agent-specific data (configurations, memory, performance)
- `analytics` - Analytics and reporting data

## Initialization Scripts

The `init/` directory contains SQL scripts that run when the PostgreSQL container starts:

- `01-init-database.sql` - Creates schemas, extensions, and permissions

## Development vs Production

### Development (Default)
- Uses SQLite for simplicity
- Profile: `sqlite` (default)
- File: `application.yml`

### Production/Testing
- Uses PostgreSQL for scalability
- Profile: `postgresql`
- File: `application-postgresql.yml`

## Migration from SQLite

To migrate existing SQLite data to PostgreSQL:

1. **Export SQLite data** (Phase 3.5 - Data Migration)
2. **Start PostgreSQL** with Docker Compose
3. **Switch application profile** to `postgresql`
4. **Import data** using migration scripts

## Troubleshooting

### Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose -f docker-compose.postgresql.yml ps

# Check PostgreSQL logs
docker-compose -f docker-compose.postgresql.yml logs postgres

# Test connection
psql -h localhost -p 5432 -U trading_user -d agentic_trading
```

### Reset Database

```bash
# Stop and remove containers with data
docker-compose -f docker-compose.postgresql.yml down -v

# Start fresh
docker-compose -f docker-compose.postgresql.yml up -d
```

### Performance Monitoring

```bash
# Connect to PostgreSQL
psql -h localhost -p 5432 -U trading_user -d agentic_trading

# Check active connections
SELECT * FROM pg_stat_activity;

# Check database size
SELECT pg_size_pretty(pg_database_size('agentic_trading'));

# Health check
SELECT health_check();
```

## Security Notes

⚠️ **Important**: The default credentials are for development only. In production:

1. Change all default passwords
2. Use environment variables for credentials
3. Enable SSL/TLS connections
4. Configure proper firewall rules
5. Regular security updates

## Next Steps

After completing Phase 3.1 (PostgreSQL Setup), proceed to:
- **Phase 3.2**: Database Schema Migration
- **Phase 3.3**: Update Python MCP Servers
- **Phase 3.4**: Java Backend Integration
- **Phase 3.5**: Data Migration and Testing