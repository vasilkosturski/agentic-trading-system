# 🏛️ Agentic Trading System

A sophisticated autonomous trading system featuring four AI agents inspired by legendary investors, built with MCP (Model Context Protocol) architecture and OpenAI GPT-4.

## 🎯 Overview

This system implements four distinct trading personalities as autonomous AI agents:

- **Warren** 📊 - Value investing (Warren Buffett style)
- **George** 🌍 - Contrarian macro trading (George Soros style)  
- **Ray** ⚖️ - Risk parity diversification (Ray Dalio style)
- **Cathie** 🚀 - Innovation growth investing (Cathie Wood style)

## 🏗️ Architecture

### Hybrid Java/Python MCP Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Agents     │    │   MCP Servers    │    │  Java Backend   │
│   (Python)      │◄──►│   (Python)       │◄──►│  (Spring Boot)  │
│                 │    │                  │    │                 │
│ • Warren        │    │ • accounts_server│    │ • AccountService│
│ • George        │    │ • market_server  │    │ • MarketService │
│ • Ray           │    │ • push_server    │    │ • Controllers   │
│ • Cathie        │    │                  │    │ • SQLite DB     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Project Structure

```
agentic-trading-system/
├── backend/                 # Java Spring Boot REST API
│   ├── src/main/java/com/trading/
│   │   ├── service/        # Business logic
│   │   ├── controller/     # REST endpoints
│   │   ├── entity/         # JPA entities
│   │   └── repository/     # Data access
│   └── build.gradle.kts    # Build configuration
├── mcp-servers/            # Python MCP Protocol Servers
│   ├── accounts_server.py  # Account management tools
│   ├── market_server.py    # Market data tools
│   └── push_server.py      # Notification tools
├── agents/                 # AI Trading Agents
│   ├── base_agent.py       # Abstract base agent
│   ├── warren_agent.py     # Value investor
│   ├── george_agent.py     # Contrarian trader
│   ├── ray_agent.py        # Risk parity trader
│   ├── cathie_agent.py     # Growth investor
│   ├── mcp_connector.py    # MCP tool connections
│   ├── agent_orchestrator.py # Multi-agent coordinator
│   └── trading_system.py   # Main system entry point
├── frontend/               # Future React/Vue UI
└── docs/                   # Documentation
```

## 🤖 Trading Agents

### Warren (Value Investor)
- **Philosophy**: Long-term value investing with margin of safety
- **Risk**: Conservative (2-5% position sizes)
- **Focus**: Undervalued stocks, strong fundamentals, dividend-paying companies
- **Approach**: Patient, disciplined, fundamentals over technicals

### George (Contrarian Macro)
- **Philosophy**: Contrarian thinking and reflexivity theory
- **Risk**: Aggressive (up to 15% position sizes)
- **Focus**: Market sentiment, macro trends, overreactions
- **Approach**: Bold when conviction is high, quick to reverse

### Ray (Risk Parity)
- **Philosophy**: Diversified risk-adjusted returns
- **Risk**: Moderate (3-5% risk-adjusted positions)
- **Focus**: Portfolio balance, volatility-based sizing
- **Approach**: Systematic, principle-based, risk-first

### Cathie (Growth Innovation)
- **Philosophy**: Disruptive innovation and exponential growth
- **Risk**: Aggressive (5-10% concentrated positions)
- **Focus**: Technology, innovation, transformative companies
- **Approach**: Long-term vision, high conviction, embrace volatility

## 🛠️ Technology Stack

### Backend (Java)
- **Spring Boot 3.2.0** - Web framework
- **SQLite** - Database with JSON storage
- **JPA/Hibernate** - ORM with custom SQLite dialect
- **Jackson** - JSON serialization
- **RestTemplate** - HTTP client for market data APIs

### MCP Servers (Python)
- **FastMCP** - MCP protocol implementation
- **aiohttp** - Async HTTP client
- **Alpha Vantage API** - Real market data
- **Yahoo Finance API** - Fallback market data

### AI Agents (Python)
- **OpenAI GPT-4** - Decision making engine
- **asyncio** - Async programming
- **MCP Protocol** - Tool communication

## 🚀 Getting Started

### Prerequisites
- Java 17+
- Python 3.8+
- OpenAI API key
- Alpha Vantage API key (optional)

### 1. Start the Java Backend

```bash
cd backend
./gradlew bootRun
```

The backend will start on `http://localhost:8080`

### 2. Install Python Dependencies

```bash
cd agents
pip install -r requirements.txt

cd ../mcp-servers  
pip install -r requirements.txt
```

### 3. Set Environment Variables

```bash
export OPENAI_API_KEY="your-openai-api-key"
export ALPHA_VANTAGE_API_KEY="your-alpha-vantage-key"  # Optional
```

### 4. Run the Trading System

```bash
cd agents
python trading_system.py
```

## 📊 Market Data Integration

### Real-Time Data Sources
- **Alpha Vantage** - Primary market data API
- **Yahoo Finance** - Fallback market data API
- **Mock Data** - Fallback when APIs unavailable

### Market Features
- Current stock prices with caching
- Historical price data (configurable periods)
- Technical indicators (SMA5, SMA20, volatility)
- Market status and trading hours
- Trend analysis and sentiment

### Supported Symbols
- **Tech**: AAPL, GOOGL, MSFT, NVDA, META
- **Growth**: TSLA, NFLX, AMZN
- **ETFs**: SPY, QQQ

## 🔧 MCP Tools Available

### Account Management
- `get_balance` - Get account cash and portfolio value
- `buy_shares` - Execute buy orders with validation
- `sell_shares` - Execute sell orders with validation
- `get_holdings` - Get current stock positions
- `change_strategy` - Update trading strategy

### Market Data
- `lookup_share_price` - Get current stock price
- `get_historical_prices` - Historical price data
- `get_market_indicators` - Technical indicators
- `get_market_status` - Market open/close status
- `analyze_stock_trend` - Comprehensive trend analysis
- `clear_price_cache` - Cache management

### Notifications
- `send_notification` - Push notifications for trades

## 🎮 Usage Examples

### Run Single Trading Cycle
```python
from agents.trading_system import TradingSystem

system = TradingSystem()
await system.run_single_cycle()
```

### Continuous Trading
```python
system = TradingSystem()
await system.run_continuous()  # Runs every 5 minutes
```

### Get System Status
```python
status = await system.get_system_status()
print(json.dumps(status, indent=2))
```

## 📈 Trading Logic

Each agent analyzes:
1. **Current portfolio** - Cash balance, holdings, total value
2. **Market data** - Price, technical indicators, trend analysis
3. **Risk factors** - Volatility, position sizing, diversification
4. **Personality rules** - Investment philosophy and constraints

Decision output:
```json
{
  "action": "buy|sell|hold",
  "quantity": 100,
  "reasoning": "Detailed explanation...",
  "confidence": 0.85
}
```

## 🔒 Risk Management

- **Position limits** - Max 15% per position (varies by agent)
- **Cash management** - Maintain minimum cash reserves
- **Volatility adjustment** - Size positions based on risk
- **Stop losses** - Quick exits when thesis breaks
- **Diversification** - Spread risk across symbols

## 🧪 Testing

### Test Agent Foundation
```bash
cd agents
python test_agent_foundation.py
```

### Test Java Backend
```bash
cd backend
./gradlew test
```

### Test MCP Servers
```bash
cd mcp-servers
python -m pytest
```

## 📊 Performance Monitoring

The system tracks:
- **Trade execution** - Buy/sell orders with timestamps
- **Portfolio performance** - P&L, returns, Sharpe ratio
- **Agent behavior** - Decision patterns, confidence levels
- **Risk metrics** - Volatility, drawdowns, correlation

## 🔮 Future Enhancements

- **Web UI** - React dashboard for monitoring
- **Backtesting** - Historical performance analysis
- **Paper trading** - Risk-free testing mode
- **Advanced indicators** - RSI, MACD, Bollinger Bands
- **Options trading** - Derivatives support
- **Multi-asset** - Bonds, commodities, crypto

## 📝 Configuration

### Application Settings (`backend/src/main/resources/application.yml`)
```yaml
market:
  alpha-vantage:
    api-key: ${ALPHA_VANTAGE_API_KEY:demo}
  cache:
    ttl-minutes: 5
  fallback-to-mock: true

openai:
  api-key: ${OPENAI_API_KEY:}
  model: gpt-4
  max-tokens: 2000
```

### Agent Configuration
Each agent can be customized:
- **Risk tolerance** - Conservative, moderate, aggressive
- **Position sizing** - Max percentage per trade
- **Temperature** - OpenAI creativity level
- **Trading symbols** - Stocks to analyze

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This is an educational project for learning AI and trading concepts. **NOT FINANCIAL ADVICE**. Do not use with real money without proper testing and risk management. Past performance does not guarantee future results.

## 🙏 Acknowledgments

- **MCP Protocol** - Model Context Protocol for tool integration
- **OpenAI** - GPT-4 for intelligent decision making
- **Spring Boot** - Robust Java backend framework
- **FastMCP** - Python MCP server implementation
- **Legendary Investors** - Warren Buffett, George Soros, Ray Dalio, Cathie Wood for inspiration

---

Built with ❤️ using MCP architecture and OpenAI GPT-4