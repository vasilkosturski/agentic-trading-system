# Agentic Trading System - Hybrid Java/Python MCP Architecture

## Architecture Overview

This project implements a **hybrid architecture** that combines:
- **Java Spring Boot** backend for business logic, database operations, and REST APIs
- **Python MCP servers** that provide tools to AI agents via the Model Context Protocol

## Architecture Components

### Java Spring Boot Backend (`src/main/java/`)
- **Controllers**: REST API endpoints that MCP servers call
  - `AccountsController` - Account management operations
  - `MarketController` - Market data operations
- **Services**: Business logic layer
  - `AccountService` - Account operations and trading logic
  - `MarketService` - Market data and pricing
- **Entities**: JPA entities for database persistence
- **Repositories**: Data access layer with SQLite + JSON storage

### Python MCP Servers (Root directory)
- **`accounts_server.py`** - MCP tools for account operations (get_balance, buy_shares, sell_shares, etc.)
- **`market_server.py`** - MCP tools for market data (lookup_share_price)
- **`push_server.py`** - MCP tools for notifications
- **`mcp_params.py`** - Configuration for MCP server parameters

## How It Works

1. **AI Agents** connect to Python MCP servers via stdio transport
2. **Python MCP servers** expose tools using `@mcp.tool()` decorators
3. **MCP tools** make HTTP calls to Java Spring Boot REST APIs
4. **Java backend** handles business logic, database operations, and returns responses
5. **MCP servers** return results to AI agents

```
AI Agent <--stdio--> Python MCP Server <--HTTP--> Java Spring Boot <--JPA--> SQLite DB
```

## Key Features

- **Proper MCP Protocol**: Uses official Python MCP SDK with FastMCP
- **Scalable Backend**: Java Spring Boot with proper service/repository layers
- **Database Persistence**: SQLite with JSON-based account storage
- **Market Data**: Mock market data service (easily replaceable with real APIs)
- **Push Notifications**: Pushover integration for trade notifications
- **Error Handling**: Comprehensive error handling across both layers

## Getting Started

### Prerequisites
- Java 17+
- Python 3.8+
- Gradle

### Setup

1. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

2. **Start Java Spring Boot backend**:
```bash
./gradlew bootRun
```

3. **Test MCP servers** (in separate terminals):
```bash
python accounts_server.py
python market_server.py  
python push_server.py
```

### Configuration

Create a `.env` file for environment variables:
```
PUSHOVER_USER=your_pushover_user
PUSHOVER_TOKEN=your_pushover_token
BRAVE_API_KEY=your_brave_api_key
```

## API Endpoints

### Accounts API (`/api/accounts`)
- `POST /tools/get_balance` - Get account balance
- `POST /tools/get_holdings` - Get account holdings
- `POST /tools/buy_shares` - Buy shares
- `POST /tools/sell_shares` - Sell shares
- `POST /tools/change_strategy` - Change investment strategy
- `GET /resources/accounts/{name}` - Get account report
- `GET /resources/strategy/{name}` - Get account strategy

### Market API (`/api/market`)
- `GET /price/{symbol}` - Get current stock price

## MCP Tools Available

### Accounts Server
- `get_balance(name)` - Get cash balance
- `get_holdings(name)` - Get stock holdings
- `buy_shares(name, symbol, quantity, rationale)` - Buy shares
- `sell_shares(name, symbol, quantity, rationale)` - Sell shares
- `change_strategy(name, strategy)` - Change investment strategy

### Market Server
- `lookup_share_price(symbol)` - Get current stock price

### Push Server
- `push(message)` - Send push notification

## Next Steps

1. Complete AccountService implementation
2. Add real market data integration (Polygon.io, Alpha Vantage, etc.)
3. Implement OpenAI agent foundation
4. Create the four autonomous traders (Warren, George, Ray, Cathie)
5. Add comprehensive logging and monitoring

## Benefits of This Architecture

- **Best of Both Worlds**: Java's enterprise capabilities + Python's MCP ecosystem
- **Maintainable**: Clear separation between business logic and MCP protocol
- **Scalable**: Java backend can handle high-throughput operations
- **Standards Compliant**: Uses official MCP protocol and tools
- **Flexible**: Easy to add new MCP tools or modify business logic independently