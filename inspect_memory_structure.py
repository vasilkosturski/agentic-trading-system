#!/usr/bin/env python3
"""
Inspect the MCP Memory Server database structure
This shows what the schema would look like
"""

# MCP Memory (libsql) creates a simple key-value store with this structure:
example_structure = """
MCP Memory Server (libsql) Database Schema
============================================

Tables created by mcp-memory-libsql:
- memory table (key-value store)
  - key (TEXT, PRIMARY KEY): Unique identifier for the entry
  - value (TEXT): JSON-serialized value
  - timestamp (DATETIME): When the entry was created/updated
  - source (TEXT, optional): Source of the information
  - confidence (FLOAT, optional): Confidence level (0.0-1.0)

Example entries in agent memory:

1. Company Information:
   key: "company:AAPL"
   value: {
     "symbol": "AAPL",
     "name": "Apple Inc.",
     "sector": "Technology",
     "market_cap": "2.8T",
     "research_date": "2025-11-06",
     "analysis": "Strong innovation pipeline, recent AI announcements positive"
   }

2. Stock Research:
   key: "research:AAPL:2025-11-06"
   value: {
     "symbol": "AAPL",
     "sources": [
       "https://www.cnbc.com/apple",
       "https://www.reuters.com/technology"
     ],
     "sentiment": "bullish",
     "key_points": ["AI integration", "iPhone sales strong", "Services growth"]
   }

3. Market Conditions:
   key: "market:2025-11-06"
   value: {
     "date": "2025-11-06",
     "status": "OPEN",
     "indices": {
       "SPX": 5850.5,
       "NDX": 22400.2,
       "DJI": 44000.0
     },
     "volatility": "LOW"
   }

4. Trading Opportunities:
   key: "opportunity:MSFT:growth_stock"
   value: {
     "symbol": "MSFT",
     "type": "growth_stock",
     "thesis": "AI leadership in enterprise cloud",
     "entry_price": 400,
     "target_price": 450,
     "stop_loss": 380,
     "conviction": 0.85
   }

5. Historical Trades:
   key: "trade:2025-11-03"
   value: {
     "symbol": "TSLA",
     "type": "BUY",
     "quantity": 10,
     "price": 250,
     "outcome": "positive",
     "return_percent": 5.2
   }

Query Structure:
- GET key: Retrieves stored value
- SET key, value: Stores or updates value
- LIST: Lists all keys (with optional pattern matching)
- DELETE key: Removes entry
"""

print(example_structure)

# Also show what we can inspect
print("\n\nTo inspect actual memory databases, use SQLite CLI:")
print("=" * 60)
print("""
# Check if memory databases exist:
ls -lh agents/memory/*.db

# Connect to a memory database:
sqlite3 agents/memory/warren.db

# Once inside sqlite3, run:
.tables
.schema
SELECT * FROM memory LIMIT 10;
SELECT key, substr(value, 1, 100) FROM memory;

# Count entries by pattern:
SELECT 
  SUBSTR(key, 1, INSTR(key, ':') - 1) AS prefix,
  COUNT(*) as count
FROM memory
GROUP BY prefix;
""")

