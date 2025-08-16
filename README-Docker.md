# Agentic Trading System - Docker Setup Guide

## Overview

The Agentic Trading System runs as a complete Docker-based application with 4 containers:

- **PostgreSQL Database** - Data persistence and storage
- **Java Spring Boot Backend** - REST APIs and business logic  
- **React Frontend** - Modern web dashboard
- **Python Agents** - 4 autonomous trading agents with MCP servers

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available for containers
- Ports 5432, 8080, and 5173 available

### 1. Environment Setup

Copy the environment template and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Required for agents to work
OPENAI_API_KEY=your_openai_api_key_here

# Optional - will use mock data if not provided
POLYGON_API_KEY=your_polygon_api_key_here
BRAVE_API_KEY=your_brave_api_key_here

# Optional - for push notifications
PUSHOVER_TOKEN=your_pushover_token_here
PUSHOVER_USER=your_pushover_user_key_here
```

### 2. Start the System

Launch all containers with a single command:

```bash
docker-compose up -d
```

This will:
- Start PostgreSQL database with initialization scripts
- Build and start the Java Spring Boot backend
- Build and start the React frontend
- Build and start the Python agents container

### 3. Verify System Status

Check that all containers are running:

```bash
docker-compose ps
```

Expected output:
```
NAME                       STATUS                    PORTS
agentic-trading-agents     Up X seconds              
agentic-trading-backend    Up X seconds (healthy)   0.0.0.0:8080->8080/tcp
agentic-trading-frontend   Up X seconds             0.0.0.0:5173->5173/tcp
agentic-trading-postgres   Up X hours (healthy)     0.0.0.0:5432->5432/tcp
```

### 4. Access the Application

- **Frontend Dashboard**: http://localhost:5173
- **Backend API**: http://localhost:8080
- **API Health Check**: http://localhost:8080/actuator/health
- **PostgreSQL Database**: localhost:5432 (username: `trading_user`, password: `trading_password`)

## Container Details

### PostgreSQL Database
- **Image**: postgres:15-alpine
- **Port**: 5432
- **Database**: agentic_trading
- **Initialization**: Automatic schema creation with sample data
- **Schemas**: trading, agents, analytics

### Spring Boot Backend
- **Build**: Java 17 with Gradle
- **Port**: 8080
- **Profile**: postgresql (configured automatically)
- **Health Check**: `/actuator/health` endpoint
- **Features**: REST APIs, JPA entities, PostgreSQL integration

### React Frontend
- **Build**: Node 18 with Vite
- **Port**: 5173
- **Features**: Modern dashboard, real-time data, API integration
- **Development**: Hot-reload enabled

### Python Agents
- **Build**: Python 3.11 with MCP servers
- **Agents**: Warren, George, Ray, Cathie (4 autonomous traders)
- **Features**: MCP server integration, persistent memory, trading logic
- **Dependencies**: OpenAI API, market data APIs, push notifications

## Development Workflow

### View Logs

```bash
# All containers
docker-compose logs -f

# Specific container
docker-compose logs -f backend
docker-compose logs -f agents
docker-compose logs -f frontend
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Rebuild Containers

```bash
# Rebuild all containers
docker-compose build --no-cache

# Rebuild specific container
docker-compose build --no-cache backend
```

### Stop System

```bash
# Stop all containers
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

## Troubleshooting

### Backend Won't Start
- Check PostgreSQL is healthy: `docker-compose ps`
- View backend logs: `docker-compose logs backend`
- Verify database connection in logs

### Agents Not Working
- Ensure OPENAI_API_KEY is set in `.env`
- Check agents logs: `docker-compose logs agents`
- Verify backend is healthy and accessible

### Frontend Not Loading
- Check if port 5173 is available
- View frontend logs: `docker-compose logs frontend`
- Verify backend API is accessible at localhost:8080

### Database Issues
- Check PostgreSQL logs: `docker-compose logs postgres`
- Verify initialization scripts ran successfully
- Connect directly: `psql -h localhost -U trading_user -d agentic_trading`

## Production Considerations

### Security
- Change default database passwords
- Use secrets management for API keys
- Enable HTTPS/TLS
- Configure firewall rules

### Performance
- Increase container memory limits
- Configure PostgreSQL connection pooling
- Enable backend caching
- Use production-optimized frontend build

### Monitoring
- Add health check endpoints
- Configure log aggregation
- Set up container monitoring
- Enable database monitoring

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React         │    │   Spring Boot   │    │   PostgreSQL    │
│   Frontend      │◄──►│   Backend       │◄──►│   Database      │
│   (Port 5173)   │    │   (Port 8080)   │    │   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ▲
                                │ HTTP API
                                ▼
                       ┌─────────────────┐
                       │   Python        │
                       │   Agents        │
                       │   (4 Traders)   │
                       └─────────────────┘
```

## Next Steps

1. **Configure API Keys**: Add your actual API keys to `.env`
2. **Access Dashboard**: Open http://localhost:5173 to view the trading dashboard
3. **Monitor Agents**: Check logs to see autonomous trading activity
4. **Customize Settings**: Modify agent parameters and trading strategies
5. **Scale System**: Add more agents or enhance with additional features

For more information, see the main [Implementation Plan](docs/IMPLEMENTATION_PLAN.md).