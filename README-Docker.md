# Agentic Trading System - Docker Setup

## Quick Start

1. **Clone and setup environment:**
   ```bash
   git clone <repository-url>
   cd agentic-trading-system
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start the entire system:**
   ```bash
   docker-compose up -d
   ```

3. **Access the services:**
   - **Frontend**: http://localhost:5173
   - **Backend API**: http://localhost:8080
   - **PostgreSQL**: localhost:5432

## Architecture

```
┌─────────────────────────────────────────┐
│           AGENTS CONTAINER              │
│  ┌─────────────┐    ┌─────────────────┐ │
│  │   Agents    │    │  MCP Servers    │ │
│  │ (Warren,    │◄──►│ (accounts,      │ │
│  │  George,    │    │  market, push)  │ │
│  │  Ray,       │    │                 │ │
│  │  Cathie)    │    │                 │ │
│  └─────────────┘    └─────────────────┘ │
└─────────────────────────────────────────┘
                           │ HTTP
                           ▼
┌─────────────────────────────────────────┐
│        JAVA BACKEND CONTAINER           │
│         (Port 8080)                     │
└─────────────────────────────────────────┘
                           │ JDBC
                           ▼
┌─────────────────────────────────────────┐
│       POSTGRESQL CONTAINER              │
│         (Port 5432)                     │
└─────────────────────────────────────────┘
                           ▲
                           │ HTTP
┌─────────────────────────────────────────┐
│       REACT FRONTEND CONTAINER          │
│         (Port 5173)                     │
└─────────────────────────────────────────┘
```

## Services

### 1. PostgreSQL Database
- **Container**: `agentic-trading-postgres`
- **Port**: 5432
- **Database**: `agentic_trading`
- **User**: `trading_user`
- **Data**: Persisted in `postgres_data` volume

### 2. Java Backend API
- **Container**: `agentic-trading-backend`
- **Port**: 8080
- **Health Check**: `/actuator/health`
- **Profile**: `postgresql`

### 3. Python Agents
- **Container**: `agentic-trading-agents`
- **No exposed ports** (autonomous scripts)
- **Includes**: Warren, George, Ray, Cathie agents + MCP servers
- **Memory**: Persisted in `agent_memory` volume
- **Logs**: Persisted in `agent_logs` volume

### 4. React Frontend
- **Container**: `agentic-trading-frontend`
- **Port**: 5173
- **Hot Reload**: Enabled for development

## Environment Variables

Required in `.env` file:

```bash
# Market Data API (Polygon.io)
POLYGON_API_KEY=your_polygon_api_key_here

# Web Search API (Brave Search)
BRAVE_API_KEY=your_brave_api_key_here

# Push Notifications (Pushover)
PUSHOVER_TOKEN=your_pushover_token_here
PUSHOVER_USER=your_pushover_user_key_here
```

## Commands

### Start all services
```bash
docker-compose up -d
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f agents
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Stop all services
```bash
docker-compose down
```

### Rebuild and restart
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Access containers
```bash
# Backend container
docker exec -it agentic-trading-backend bash

# Agents container
docker exec -it agentic-trading-agents bash

# PostgreSQL container
docker exec -it agentic-trading-postgres psql -U trading_user -d agentic_trading
```

## Development

### Hot Reload
- **Frontend**: Automatic hot reload enabled
- **Backend**: Automatic restart on code changes
- **Agents**: Manual restart required (`docker-compose restart agents`)

### Database Access
```bash
# Connect to PostgreSQL
docker exec -it agentic-trading-postgres psql -U trading_user -d agentic_trading

# View tables
\dt

# View agent accounts
SELECT * FROM trading_accounts;
```

### Troubleshooting

#### Check service health
```bash
docker-compose ps
```

#### View service logs
```bash
docker-compose logs backend
docker-compose logs agents
```

#### Reset database
```bash
docker-compose down -v  # WARNING: Deletes all data
docker-compose up -d
```

#### Rebuild specific service
```bash
docker-compose build backend
docker-compose up -d backend
```

## Production Deployment

For production, modify `docker-compose.yml`:

1. Remove volume mounts for source code
2. Use production-optimized Dockerfiles
3. Add proper secrets management
4. Configure reverse proxy (nginx)
5. Set up SSL certificates
6. Configure monitoring and logging

## API Endpoints

Once running, the backend provides:

- **Health**: http://localhost:8080/actuator/health
- **Accounts**: http://localhost:8080/api/accounts
- **Trading**: http://localhost:8080/api/trading
- **Market**: http://localhost:8080/api/market

## Next Steps

1. Configure your API keys in `.env`
2. Start the system with `docker-compose up -d`
3. Access the frontend at http://localhost:5173
4. Monitor agent activity in the logs
5. View trading data in the PostgreSQL database