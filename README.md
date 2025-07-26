# Agentic Trading System

A full-stack autonomous AI trading system with proper separation of concerns.

## 🏗️ Project Structure (Organized by Purpose)

```
agentic-trading-system/
├── backend/                    # Java Spring Boot REST API
│   ├── src/main/java/         # Java source code
│   ├── build.gradle.kts       # Backend build configuration
│   └── gradlew               # Gradle wrapper
├── frontend/                   # React/Vue/Angular UI (Future)
│   └── (Coming soon)
├── mcp-servers/               # Python MCP Protocol Servers
│   ├── accounts_server.py     # Account operations MCP tools
│   ├── market_server.py       # Market data MCP tools
│   ├── push_server.py         # Notification MCP tools
│   ├── mcp_params.py          # MCP server configuration
│   └── requirements.txt       # Python dependencies
├── agents/                    # AI Trading Agents (Future)
│   └── (Warren, George, Ray, Cathie traders)
└── docs/                      # Documentation
    └── README.md              # Detailed technical documentation
```

## 🎯 Architecture Overview

**Hybrid Full-Stack Architecture:**
```
Frontend UI <--REST--> Java Backend <--HTTP--> Python MCP Servers <--stdio--> AI Agents
```

### Components:

1. **Backend** (`/backend/`) - Java Spring Boot
   - REST APIs for frontend and MCP servers
   - Business logic and database operations
   - SQLite with JSON-based account storage

2. **MCP Servers** (`/mcp-servers/`) - Python FastMCP
   - Proper MCP protocol implementation
   - Tools for AI agents (accounts, market, notifications)
   - Calls backend REST APIs for data operations

3. **Frontend** (`/frontend/`) - Modern Web UI (Future)
   - Trading dashboard and portfolio management
   - Real-time market data visualization
   - Account management interface

4. **Agents** (`/agents/`) - AI Trading Agents (Future)
   - Warren (Value investing)
   - George (Momentum trading)  
   - Ray (Systematic approach)
   - Cathie (Innovation focus)

## 🚀 Quick Start

### Backend (Java Spring Boot)
```bash
cd backend
./gradlew bootRun
# Backend runs on http://localhost:8080
```

### MCP Servers (Python)
```bash
cd mcp-servers
pip install -r requirements.txt
python accounts_server.py    # Terminal 1
python market_server.py      # Terminal 2  
python push_server.py        # Terminal 3
```

### Frontend (Coming Soon)
```bash
cd frontend
npm install && npm start
# Frontend will run on http://localhost:3000
```

## 📋 Available APIs

### Backend REST APIs
- **Accounts**: `http://localhost:8080/api/accounts/*`
- **Market**: `http://localhost:8080/api/market/*`

### MCP Tools (for AI Agents)
- **Accounts**: get_balance, get_holdings, buy_shares, sell_shares, change_strategy
- **Market**: lookup_share_price
- **Push**: push notifications

## 🔧 Development Status

- ✅ **Backend**: Java Spring Boot with REST APIs
- ✅ **MCP Servers**: Python FastMCP with proper protocol
- ✅ **Database**: SQLite with JSON account storage
- ✅ **Architecture**: Proper separation by purpose
- 🚧 **Service Layer**: Account operations (in progress)
- 📋 **Frontend**: React dashboard (planned)
- 📋 **AI Agents**: Four autonomous traders (planned)

## 📚 Documentation

See [`docs/README.md`](docs/README.md) for detailed technical documentation, API specifications, and development guides.

## 🎯 Next Steps

1. Complete AccountService implementation
2. Add real market data integration
3. Build React frontend dashboard
4. Implement AI trading agents
5. Add comprehensive monitoring and logging

---

**Architecture Philosophy**: Organized by purpose, not technology. Each component has a clear responsibility and communicates through well-defined interfaces.