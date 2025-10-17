# Agentic Trading System Architecture

## Key Components
- **Backend**: Java Spring Boot (port 8080)
- **Frontend**: React TypeScript + Vite (port 5173)
- **Agents**: Python with OpenAI Agents SDK
- **Database**: PostgreSQL

## Trading Agents
1. **Warren** ($100k) - Value investing, 30% risk
2. **George** ($50k) - Momentum trading, 70% risk
3. **Ray** ($75k) - Risk parity, 50% risk
4. **Cathie** ($60k) - Growth innovation, 80% risk

## Key Constraints
- **10 position limit per agent** (enforced in `AccountService.java:113-136`)
- End-of-day market data from Polygon.io
- 60-minute price cache TTL
- Autonomous research via Brave Search MCP

## Important Files
- `agents/simple_trader.py` - Main trader agent class
- `agents/trading_tools.py` - Direct HTTP trading functions (buy_shares, sell_shares)
- `agents/market_tools.py` - Market data functions
- `backend/src/main/java/com/trading/service/AccountService.java` - Position limit enforcement

## Deployment
- Kubernetes on Hetzner K3s
- URL: https://agentic-trading.vkontech.com
- Deploy script: `deployment/k3s/deploy-to-k3s.sh`
