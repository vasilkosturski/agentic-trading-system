# MCP Protocol Communication Guide

## Overview

**JSON-RPC 2.0** is an **industry standard** protocol (not MCP-specific) defined in [RFC 7159](https://tools.ietf.org/html/rfc7159). MCP (Model Context Protocol) uses JSON-RPC 2.0 as its underlying communication protocol for structured message exchange between clients and servers.

## JSON-RPC 2.0 Industry Standard

### Official Specification
- **Standard**: JSON-RPC 2.0 Specification
- **URL**: https://www.jsonrpc.org/specification
- **Status**: Industry standard used by many protocols and systems
- **Purpose**: Stateless, light-weight remote procedure call (RPC) protocol

### JSON-RPC 2.0 Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "JSON-RPC 2.0",
  "oneOf": [
    {
      "title": "Request",
      "type": "object",
      "required": ["jsonrpc", "method"],
      "properties": {
        "jsonrpc": {
          "type": "string",
          "enum": ["2.0"]
        },
        "method": {
          "type": "string"
        },
        "params": {
          "oneOf": [
            {"type": "array"},
            {"type": "object"}
          ]
        },
        "id": {
          "oneOf": [
            {"type": "string"},
            {"type": "number"},
            {"type": "null"}
          ]
        }
      }
    },
    {
      "title": "Response",
      "type": "object",
      "required": ["jsonrpc", "id"],
      "properties": {
        "jsonrpc": {
          "type": "string",
          "enum": ["2.0"]
        },
        "result": {},
        "error": {
          "type": "object",
          "required": ["code", "message"],
          "properties": {
            "code": {"type": "integer"},
            "message": {"type": "string"},
            "data": {}
          }
        },
        "id": {
          "oneOf": [
            {"type": "string"},
            {"type": "number"},
            {"type": "null"}
          ]
        }
      },
      "oneOf": [
        {"required": ["result"]},
        {"required": ["error"]}
      ]
    }
  ]
}
```

## MCP-Specific Usage of JSON-RPC 2.0

MCP defines specific **methods** and **message structures** on top of the JSON-RPC 2.0 foundation.

### MCP Protocol Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MCP Protocol Messages",
  "definitions": {
    "mcpRequest": {
      "type": "object",
      "required": ["jsonrpc", "method", "id"],
      "properties": {
        "jsonrpc": {"const": "2.0"},
        "method": {
          "enum": [
            "initialize",
            "tools/list",
            "tools/call",
            "resources/list",
            "resources/read",
            "prompts/list",
            "prompts/get"
          ]
        },
        "params": {"type": "object"},
        "id": {"type": ["string", "number"]}
      }
    },
    "mcpResponse": {
      "type": "object",
      "required": ["jsonrpc", "id"],
      "properties": {
        "jsonrpc": {"const": "2.0"},
        "id": {"type": ["string", "number"]},
        "result": {"type": "object"},
        "error": {
          "type": "object",
          "required": ["code", "message"],
          "properties": {
            "code": {"type": "integer"},
            "message": {"type": "string"},
            "data": {}
          }
        }
      },
      "oneOf": [
        {"required": ["result"]},
        {"required": ["error"]}
      ]
    }
  }
}
```

## Real MCP Server Communication Examples

### 1. Initialize Connection

**Request** (Client → Server):
```json
{
  "jsonrpc": "2.0",
  "id": "init-1",
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {},
      "resources": {}
    },
    "clientInfo": {
      "name": "trading-agent",
      "version": "1.0.0"
    }
  }
}
```

**Response** (Server → Client):
```json
{
  "jsonrpc": "2.0",
  "id": "init-1",
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {
        "listChanged": true
      },
      "resources": {
        "subscribe": true,
        "listChanged": true
      }
    },
    "serverInfo": {
      "name": "accounts_server",
      "version": "1.0.0"
    }
  }
}
```

### 2. List Available Tools

**Request** (Client → Server):
```json
{
  "jsonrpc": "2.0",
  "id": "tools-list-1",
  "method": "tools/list",
  "params": {}
}
```

**Response** (Server → Client):
```json
{
  "jsonrpc": "2.0",
  "id": "tools-list-1",
  "result": {
    "tools": [
      {
        "name": "get_balance",
        "description": "Get the cash balance of the given account name",
        "inputSchema": {
          "type": "object",
          "properties": {
            "name": {
              "type": "string",
              "description": "The name of the account holder"
            }
          },
          "required": ["name"]
        }
      },
      {
        "name": "buy_shares",
        "description": "Buy shares of a stock",
        "inputSchema": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "symbol": {"type": "string"},
            "quantity": {"type": "integer"},
            "rationale": {"type": "string"}
          },
          "required": ["name", "symbol", "quantity", "rationale"]
        }
      }
    ]
  }
}

### Tool Definition Structure (MCP-Specific)

**YES, this structure is MCP-specific**. The tool definition format is defined by the MCP protocol specification:

```json
{
  "name": "tool_name",           // MCP: Tool identifier
  "description": "...",          // MCP: Human-readable description
  "inputSchema": {               // MCP: JSON Schema for input validation
    "type": "object",            // JSON Schema: Standard schema format
    "properties": { ... },       // JSON Schema: Property definitions
    "required": [ ... ]          // JSON Schema: Required fields
  }
}
```

**What's MCP-specific:**
- `name` field for tool identification
- `description` field for tool documentation  
- `inputSchema` field containing JSON Schema for input validation
- The overall structure and field names

**What's industry standard:**
- The `inputSchema` content uses **JSON Schema** (industry standard)
- JSON Schema format: `type`, `properties`, `required`, etc.

**Comparison with other protocols:**

## Important: No Standard API Schemas

**There is NO standardized schema for specific MCP APIs like "get market data"**. Each MCP server defines its own tools and schemas based on its domain.

### What MCP Standardizes:
- **Protocol structure**: How to communicate (JSON-RPC 2.0)
- **Core methods**: `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`
- **Message format**: Request/response structure
- **Tool definition format**: How to describe tools (`name`, `description`, `inputSchema`)

### What MCP Does NOT Standardize:
- **Specific tool names**: `get_balance`, `buy_shares`, `get_market_data` are custom
- **Tool parameters**: Each server defines its own input/output schemas
- **Business logic**: How tools actually work is server-specific
- **Data formats**: Response content is server-defined

### Examples of Server-Specific Schemas:

#### Trading MCP Server (Custom):
```json
{

## MCP Response Content Types

**Important**: MCP responses can contain both **structured data** and **text content** depending on the implementation.

### Our Project's Response Format:

**Our agentic-trading-system uses direct structured data responses** (not wrapped in content arrays):

#### 1. Simple Data Types (numbers, strings):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-1",
  "result": 50000.00
}
```

#### 2. Complex Structured Data (objects, arrays):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-2",
  "result": {
    "AAPL": 100,
    "MSFT": 50,
    "GOOGL": 25
  }
}
```

#### 3. Rich Structured Data with Metadata:
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-3",
  "result": {
    "symbol": "AAPL",
    "current_price": 150.25,
    "price_change": 5.75,
    "price_change_percent": 3.98,
    "trend": "BULLISH",
    "data_quality": {
      "price_data_tier": "REAL_TIME",
      "warnings": null
    }
  }
}
```

### Alternative MCP Content Array Format:

Some MCP implementations use content arrays for mixed content types:

#### Text Content (for LLM consumption):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-x",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Successfully purchased 100 shares of AAPL"
      }
    ]
  }
}
```

#### Structured Data in Content Array:
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-x",
  "result": {
    "content": [
      {
        "type": "application/json",
        "data": {
          "transaction_id": "txn-12345",
          "total_cost": 15025.00
        }
      }
    ]
  }
}
```

### When to Use Each Type:

#### Text Content:
- **Purpose**: For LLM to understand and communicate to users
- **Use cases**: Status messages, explanations, summaries
- **Processing**: LLM reads text and incorporates into response

#### Structured Data:
- **Purpose**: For programmatic processing and integration
- **Use cases**: API responses, data exchange, further processing
- **Processing**: Application code can parse and use the data

#### Mixed Content:
- **Purpose**: Both programmatic use AND LLM understanding
- **Use cases**: Complex operations needing both data and explanation
- **Processing**: App uses structured data, LLM uses text description

### Content Type Schema:

```json
{
  "content": {
    "type": "array",
    "items": {
      "oneOf": [
        {
          "type": "object",
          "properties": {
            "type": {"const": "text"},
            "text": {"type": "string"}
          },
          "required": ["type", "text"]
        },
        {
          "type": "object", 
          "properties": {
            "type": {"const": "application/json"},
            "data": {"type": "object"}
          },
          "required": ["type", "data"]
        },
        {
          "type": "object",
          "properties": {
            "type": {"const": "image"},
            "data": {"type": "string"},
            "mimeType": {"type": "string"}
          },
          "required": ["type", "data", "mimeType"]
        }
      ]
    }
  }
}
```

### LLM Processing Flow:

1. **MCP Server** returns structured response with content array
2. **MCP Client** receives the response
3. **LLM** processes the content:
   - **Text content**: Directly incorporates into response
   - **Structured data**: Analyzes and converts to natural language
   - **Mixed content**: Uses both as appropriate
4. **User** receives natural language response from LLM

### Example Flow:

```
1. User: "Buy 100 shares of AAPL for Warren"

2. LLM → MCP Server: 
   tools/call buy_shares {"name": "Warren", "symbol": "AAPL", "quantity": 100, "rationale": "..."}

3. MCP Server → LLM:
   {
     "content": [
       {
         "type": "application/json",
         "data": {"transaction_id": "txn-123", "total_cost": 15025.00, "remaining_balance": 34975.00}
       },
       {
         "type": "text", 
         "text": "Successfully purchased 100 shares of AAPL for $15,025.00"
       }
     ]
   }

4. LLM → User: 
   "I've successfully purchased 100 shares of AAPL for Warren at $150.25 per share. 
   The total cost was $15,025.00 and Warren's remaining balance is $34,975.00."
```

So yes, you're correct - MCP is a **structured API** that can return both structured data AND text content, with the LLM processing both types to produce natural language responses to users.
  "name": "get_balance",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"}
    },
    "required": ["name"]
  }
}
```

#### Weather MCP Server (Custom):
```json
{
  "name": "get_weather",
  "inputSchema": {
    "type": "object", 
    "properties": {
      "location": {"type": "string"},
      "units": {"type": "string", "enum": ["celsius", "fahrenheit"]}
    },
    "required": ["location"]
  }
}
```

#### File System MCP Server (Custom):
```json
{
  "name": "read_file",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": {"type": "string"},
      "encoding": {"type": "string", "default": "utf-8"}
    },
    "required": ["path"]
  }
}
```

### Why No Standard APIs?

1. **Domain Flexibility**: MCP servers can be for any domain (trading, weather, files, databases, etc.)
2. **Custom Business Logic**: Each server has unique requirements and capabilities
3. **Protocol vs Implementation**: MCP defines HOW to communicate, not WHAT to communicate
4. **Extensibility**: Allows innovation and custom solutions without protocol changes

### Discovery Mechanism:

Since there are no standard APIs, MCP provides a **discovery mechanism**:

1. **Client calls `tools/list`** to discover available tools
2. **Server responds with tool definitions** including schemas
3. **Client can dynamically adapt** to any server's capabilities
4. **No prior knowledge needed** about server-specific APIs

This is similar to:
- **OpenAPI/Swagger**: Describes REST APIs but doesn't standardize specific endpoints
- **GraphQL**: Provides introspection but doesn't standardize specific queries
- **gRPC**: Defines service structure but not specific service implementations
- **OpenAPI/Swagger**: Uses different structure (`operationId`, `parameters`, `requestBody`)
- **GraphQL**: Uses different syntax (`type`, `Query`, `Mutation`)
- **gRPC**: Uses Protocol Buffers (`.proto` files)
- **JSON-RPC without MCP**: No standardized tool discovery mechanism
```

### 3. Call a Tool (get_balance)

**Request** (Client → Server):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-1",
  "method": "tools/call",
  "params": {
    "name": "get_balance",
    "arguments": {
      "name": "Warren"
    }
  }
}
```

**Response** (Server → Client):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-1",
  "result": 50000.00
}
```

### 4. Call a Tool (get_holdings)

**Request** (Client → Server):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-2",
  "method": "tools/call",
  "params": {
    "name": "get_holdings",
    "arguments": {
      "name": "Warren"
    }
  }
}
```

**Response** (Server → Client):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-2",
  "result": {
    "AAPL": 100,
    "MSFT": 50,
    "GOOGL": 25
  }
}
```

### 5. Call a Tool (get_price_with_metadata)

**Request** (Client → Server):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-3",
  "method": "tools/call",
  "params": {
    "name": "get_price_with_metadata",
    "arguments": {
      "symbol": "AAPL"
    }
  }
}
```

**Response** (Server → Client):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-3",
  "result": {
    "price": 150.25,
    "data_tier": "REAL_TIME",
    "timestamp": "2024-01-01T10:30:00Z",
    "data_source": "POLYGON",
    "data_age_minutes": 2
  }
}
```

### 6. Call a Tool (analyze_stock_trend)

**Request** (Client → Server):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-4",
  "method": "tools/call",
  "params": {
    "name": "analyze_stock_trend",
    "arguments": {
      "symbol": "AAPL",
      "days": 20
    }
  }
}
```

**Response** (Server → Client):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-4",
  "result": {
    "symbol": "AAPL",
    "current_price": 150.25,
    "price_change": 5.75,
    "price_change_percent": 3.98,
    "trend": "BULLISH",
    "sma5": 148.50,
    "sma20": 145.30,
    "volatility": 0.25,
    "analysis_period_days": 20,
    "data_quality": {
      "price_data_tier": "REAL_TIME",
      "price_data_age_minutes": 2,
      "historical_data_tier": "DELAYED",
      "indicators_data_tier": "DELAYED",
      "warnings": null
    }
  }
}
```

### 7. Call a Tool (buy_shares)

**Request** (Client → Server):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-5",
  "method": "tools/call",
  "params": {
    "name": "buy_shares",
    "arguments": {
      "name": "Warren",
      "symbol": "AAPL",
      "quantity": 100,
      "rationale": "Strong quarterly earnings and positive market sentiment"
    }
  }
}
```

**Response** (Server → Client):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-5",
  "result": "Successfully purchased 100 shares of AAPL for Warren at $150.25 per share. Total cost: $15,025.00. Remaining balance: $34,975.00"
}
```

### 8. Error Response Example

**Request** (Client → Server):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-6",
  "method": "tools/call",
  "params": {
    "name": "get_balance",
    "arguments": {
      "name": "NonExistentUser"
    }
  }
}
```

**Error Response** (Server → Client):
```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-6",
  "error": {
    "code": -32004,
    "message": "Tool execution failed",
    "data": {
      "details": "Failed to get balance for NonExistentUser: Account 'NonExistentUser' not found",
      "type": "AccountNotFoundError"
    }
  }
}
```

### 9. List Resources

**Request** (Client → Server):
```json
{
  "jsonrpc": "2.0",
  "id": "resources-list-1",
  "method": "resources/list",
  "params": {}
}
```

**Response** (Server → Client):
```json
{
  "jsonrpc": "2.0",
  "id": "resources-list-1",
  "result": {
    "resources": [
      {
        "uri": "accounts://accounts_server/warren",
        "name": "Warren's Account Report",
        "description": "Detailed account information for Warren",
        "mimeType": "text/plain"
      },
      {
        "uri": "accounts://strategy/warren",
        "name": "Warren's Investment Strategy",
        "description": "Current investment strategy for Warren",
        "mimeType": "text/plain"
      }
    ]
  }
}
```

### 10. Read Resource

**Request** (Client → Server):
```json
{
  "jsonrpc": "2.0",
  "id": "resource-read-1",
  "method": "resources/read",
  "params": {
    "uri": "accounts://accounts_server/warren"
  }
}
```

**Response** (Server → Client):
```json
{
  "jsonrpc": "2.0",
  "id": "resource-read-1",
  "result": {
    "contents": [
      {
        "uri": "accounts://accounts_server/warren",
        "mimeType": "text/plain",
        "text": "Account: Warren Buffett\nBalance: $50,000.00\nHoldings:\n- AAPL: 100 shares\n- BRK.B: 50 shares\nTotal Portfolio Value: $65,000.00\nP&L: +$15,000.00 (+30%)"
      }
    ]
  }
}
```

## MCP Standard Error Codes

MCP follows JSON-RPC 2.0 error codes with some extensions:

```json
{
  "standardErrorCodes": {
    "-32700": "Parse error - Invalid JSON was received",
    "-32600": "Invalid Request - The JSON sent is not a valid Request object",
    "-32601": "Method not found - The method does not exist / is not available",
    "-32602": "Invalid params - Invalid method parameter(s)",
    "-32603": "Internal error - Internal JSON-RPC error",
    "-32000 to -32099": "Server error - Reserved for implementation-defined server-errors"
  },
  "mcpSpecificErrors": {
    "-32001": "Tool not found",
    "-32002": "Resource not found", 
    "-32003": "Resource access denied",
    "-32004": "Tool execution failed",
    "-32005": "Invalid tool arguments"
  }
}
```

## Transport Layer Differences

### Current (stdio):
```
Agent Process ←→ stdin/stdout ←→ MCP Server Process
```

### Target (HTTP):
```
Agent Process ←→ HTTP POST ←→ Remote MCP Server
```

**HTTP Headers**:
```
POST /tools/call HTTP/1.1
Host: accounts-mcp:8001
Content-Type: application/json
Content-Length: 156

{JSON-RPC message body}
```

## Streaming Support for Remote HTTP

For streaming responses (like real-time market data), MCP can use:

### Chunked Transfer Encoding:
```
HTTP/1.1 200 OK
Content-Type: application/json
Transfer-Encoding: chunked

{chunk-size}\r\n
{"jsonrpc":"2.0","id":"stream-1","result":{"type":"partial","data":{"symbol":"AAPL"}}}\r\n
{chunk-size}\r\n
{"jsonrpc":"2.0","id":"stream-1","result":{"type":"partial","data":{"price":150.25}}}\r\n
{chunk-size}\r\n
{"jsonrpc":"2.0","id":"stream-1","result":{"type":"final","data":{"timestamp":"2024-01-01T10:30:00Z"}}}\r\n
0\r\n
\r\n
```

## Summary

1. **JSON-RPC 2.0**: Industry standard protocol (not MCP-specific)
2. **MCP Protocol**: Defines specific methods and message structures on top of JSON-RPC 2.0
3. **Communication**: Structured request/response with proper error handling
4. **Transport**: Currently stdio, target is HTTP with streaming support
5. **Schema**: Well-defined schemas for both JSON-RPC 2.0 and MCP-specific extensions

This provides a robust, standardized communication protocol that's language-agnostic and widely supported across different systems and platforms.