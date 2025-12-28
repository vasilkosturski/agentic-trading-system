# API Refactoring Architecture

## System Architecture (Current vs Target)

### Current Architecture (Tool-Specific Pattern)

```
┌─────────────────┐
│  Python Agent   │
│   (Warren)      │
└────────┬────────┘
         │
         │ POST /api/accounts/tools/get_balance
         │ Body: {"agentId": 1}
         │
         ▼
┌─────────────────────────────────────────────────┐
│         Spring Boot Backend                      │
│  ┌──────────────────────────────────────────┐   │
│  │   AccountController                      │   │
│  │                                          │   │
│  │  @PostMapping("/tools/get_balance")     │   │
│  │  ToolResponse<Double> getBalance() {    │   │
│  │    double balance = service.getBalance()│   │
│  │    return ToolResponse.success(balance) │   │
│  │  }                                       │   │
│  └──────────────┬───────────────────────────┘   │
│                 │                                │
│                 │ Exception?                     │
│                 ▼                                │
│  ┌──────────────────────────────────────────┐   │
│  │   AccountControllerAdvice                │   │
│  │                                          │   │
│  │  @ExceptionHandler(ResourceNotFound)    │   │
│  │  ToolResponse<Object> handle() {        │   │
│  │    return ToolResponse.error(msg)       │   │
│  │  }                                       │   │
│  └──────────────┬───────────────────────────┘   │
│                 │                                │
└─────────────────┼────────────────────────────────┘
                  │
                  ▼
         ┌────────────────────┐
         │   Response         │
         │  {                 │
         │   "success": true, │
         │   "data": 95000.0, │
         │   "error": null    │
         │  }                 │
         │  Status: 200       │
         └────────────────────┘

PROBLEMS:
❌ POST used for queries (not idempotent)
❌ Success indicated in JSON body (client checks both status AND body)
❌ Tool-specific path (/tools/*)
❌ Redundant wrapper (ToolResponse adds no value)
❌ Not generic REST (only works for AI tool pattern)
```

### Target Architecture (REST Pattern)

```
┌─────────────────┐
│  Python Agent   │
│   (Warren)      │
└────────┬────────┘
         │
         │ GET /api/accounts/1/balance
         │ No body (agentId in URL)
         │
         ▼
┌─────────────────────────────────────────────────┐
│         Spring Boot Backend                      │
│  ┌──────────────────────────────────────────┐   │
│  │   AccountController                      │   │
│  │                                          │   │
│  │  @GetMapping("/{agentId}/balance")      │   │
│  │  BalanceDto getBalance(@PathVariable    │   │
│  │      Long agentId) {                    │   │
│  │    double bal = service.getBalance(...)  │   │
│  │    return new BalanceDto(bal)           │   │
│  │  }                                       │   │
│  └──────────────┬───────────────────────────┘   │
│                 │                                │
│                 │ Exception?                     │
│                 ▼                                │
│  ┌──────────────────────────────────────────┐   │
│  │   AccountControllerAdvice                │   │
│  │                                          │   │
│  │  @ExceptionHandler(ResourceNotFound)    │   │
│  │  ProblemDetail handle() {               │   │
│  │    return ProblemDetailFactory          │   │
│  │      .resourceNotFound(...)             │   │
│  │  }                                       │   │
│  └──────────────┬───────────────────────────┘   │
│                 │                                │
└─────────────────┼────────────────────────────────┘
                  │
                  ▼
         ┌────────────────────┐
         │   Response         │
         │  {"balance": 95000}│
         │  Status: 200 OK    │
         └────────────────────┘

BENEFITS:
✅ GET used for queries (idempotent, cacheable)
✅ Status code tells the story (200 = success, no body check needed)
✅ REST-ful path (/accounts/{id}/balance)
✅ Direct DTO response (no unnecessary wrapper)
✅ Generic REST (works with any HTTP client)
```

---

## Error Flow Comparison

### Current Error Flow (Tool Pattern)

```
1. Client Request
   POST /api/accounts/tools/get_balance
   Body: {"agentId": 999}

2. Service Layer
   accountService.getBalance("Unknown")
   → throws ResourceNotFoundException("Agent not found")

3. Exception Handler (AccountControllerAdvice)
   @ExceptionHandler(ResourceNotFoundException.class)
   → return ResponseEntity.status(404)
        .body(ToolResponse.error("Agent not found"))

4. Response
   Status: 404 Not Found
   Body: {
     "success": false,
     "data": null,
     "error": "Agent not found"
   }

5. Python Client
   result = response.json()
   if not result.get("success"):     ← Must check JSON body
       raise Exception(result["error"])
```

### Target Error Flow (REST Pattern)

```
1. Client Request
   GET /api/accounts/999/balance

2. Service Layer
   accountService.getBalance("Unknown")
   → throws ResourceNotFoundException("Agent not found")

3. Exception Handler (AccountControllerAdvice)
   @ExceptionHandler(ResourceNotFoundException.class)
   → return ResponseEntity.status(404)
        .body(ProblemDetailFactory.resourceNotFound(...))

4. Response
   Status: 404 Not Found
   Body: {
     "type": "https://trading.example.com/errors/resource-not-found",
     "title": "Resource Not Found",
     "status": 404,
     "detail": "Agent not found",
     "instance": "/api/accounts/999/balance"
   }

5. Python Client
   # http_client already raises BackendAPIError on 4xx/5xx
   # No need to check JSON body - status code is enough
   try:
       balance = await get_balance(999)
   except BackendAPIError as e:
       # Error already logged, contains status code and detail
       raise Exception(str(e))
```

---

## Request Flow Comparison (Buy Shares)

### Current Flow (Tool Pattern)

```
┌────────────────┐
│ Python Agent   │
│                │
│ buy_shares(    │
│   agent_id=1,  │
│   symbol="AAPL"│
│   quantity=10  │
│ )              │
└────────┬───────┘
         │
         │ POST /api/accounts/tools/buy_shares
         │ Body: {
         │   "agentId": 1,
         │   "symbol": "AAPL",
         │   "quantity": 10,
         │   "runId": 42
         │ }
         ▼
┌─────────────────────────────────────┐
│  AccountController                  │
│                                     │
│  @PostMapping("/tools/buy_shares")  │
│  ToolResponse<TradeResult>          │
│  buyShares(BuySharesRequest) {      │
│    ...                              │
│    return ToolResponse.success(     │
│      tradeResult                    │
│    )                                │
│  }                                  │
└─────────────────┬───────────────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  Response          │
         │  Status: 201       │
         │  Body: {           │
         │   "success": true, │
         │   "data": {        │
         │     "transactionId": 42,
         │     "symbol": "AAPL",
         │     "quantity": 10,
         │     "price": 150.0
         │   },               │
         │   "error": null    │
         │  }                 │
         └────────────────────┘
```

### Target Flow (REST Pattern)

```
┌────────────────┐
│ Python Agent   │
│                │
│ buy_shares(    │
│   agent_id=1,  │
│   symbol="AAPL"│
│   quantity=10  │
│ )              │
└────────┬───────┘
         │
         │ POST /api/accounts/1/trades
         │ Body: {
         │   "symbol": "AAPL",
         │   "quantity": 10,
         │   "type": "BUY",
         │   "runId": 42
         │ }
         ▼
┌─────────────────────────────────────┐
│  AccountController                  │
│                                     │
│  @PostMapping("/{agentId}/trades")  │
│  TradeResult                        │
│  executeTrade(                      │
│    @PathVariable Long agentId,      │
│    TradeRequest request             │
│  ) {                                │
│    ...                              │
│    return tradeResult               │
│  }                                  │
└─────────────────┬───────────────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  Response          │
         │  Status: 201       │
         │  Body: {           │
         │   "transactionId": 42,
         │   "symbol": "AAPL",
         │   "quantity": 10,
         │   "price": 150.0   │
         │  }                 │
         └────────────────────┘
```

---

## Layer Responsibilities

### Current State (Mixed Concerns)

```
┌────────────────────────────────────────────────┐
│  Controller Layer                              │
│  - Receives requests                           │
│  - Wraps responses in ToolResponse ❌           │
│  - Handles some exceptions ❌                   │
└────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────┐
│  Service Layer                                 │
│  - Business logic                              │
│  - Throws domain exceptions ✅                  │
│  - No HTTP concerns ✅                          │
└────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────┐
│  ControllerAdvice                              │
│  - Catches exceptions                          │
│  - Wraps in ToolResponse ❌                     │
│  - Returns HTTP status ✅                       │
└────────────────────────────────────────────────┘

ISSUES:
- Controller and ControllerAdvice both wrap responses
- ToolResponse adds no value, just ceremony
- Mixed tool-specific and REST patterns
```

### Target State (Clean Separation)

```
┌────────────────────────────────────────────────┐
│  Controller Layer                              │
│  - Receives requests                           │
│  - Returns DTOs directly ✅                     │
│  - No exception handling ✅                     │
└────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────┐
│  Service Layer                                 │
│  - Business logic                              │
│  - Throws domain exceptions ✅                  │
│  - No HTTP concerns ✅                          │
└────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────┐
│  ControllerAdvice                              │
│  - Catches exceptions                          │
│  - Returns ProblemDetail ✅                     │
│  - Sets HTTP status ✅                          │
└────────────────────────────────────────────────┘

BENEFITS:
- Single responsibility per layer
- Standard REST patterns throughout
- Easy to understand and maintain
```

---

## HTTP Method Usage

### Current State

| Endpoint | Method | Correct? | Issue |
|----------|--------|----------|-------|
| Get balance | POST | ❌ | Should be GET (query, not mutation) |
| Get holdings | POST | ❌ | Should be GET (query, not mutation) |
| Buy shares | POST | ✅ | Correct (creates resource) |
| Sell shares | POST | ✅ | Correct (creates resource) |
| Initialize agent | POST | ✅ | Correct (creates resource) |
| Update activity | POST | ❌ | Should be PUT (updates resource) |

### Target State

| Endpoint | Method | Semantics |
|----------|--------|-----------|
| Get balance | GET | Idempotent, cacheable, no body |
| Get holdings | GET | Idempotent, cacheable, no body |
| Buy shares | POST | Creates trade resource |
| Sell shares | POST | Creates trade resource |
| Initialize agent | POST | Creates account resource |
| Update activity | PUT | Updates last activity timestamp |

---

## Path Structure

### Current State (Mixed)

```
AccountController:
  ✅ /api/accounts/resources/accounts/{agentId}  (REST-ful)
  ✅ /api/accounts/portfolio/{agentId}/history   (REST-ful)
  ✅ /api/accounts/trades/recent                 (REST-ful)
  ✅ /api/accounts/trades/{tradeId}              (REST-ful)
  ❌ /api/accounts/tools/initialize_agent        (Tool-specific)
  ❌ /api/accounts/tools/get_balance             (Tool-specific)
  ❌ /api/accounts/tools/get_holdings            (Tool-specific)
  ❌ /api/accounts/tools/buy_shares              (Tool-specific)
  ❌ /api/accounts/tools/sell_shares             (Tool-specific)
  ❌ /api/accounts/tools/update_activity         (Tool-specific)

MarketController:
  ✅ /api/market/price/{symbol}                  (REST-ful)
  ✅ /api/market/historical/{symbol}             (REST-ful)
  ✅ /api/market/indicators/{symbol}             (REST-ful)

RunController:
  ✅ /api/runs/start                             (REST-ful)
  ✅ /api/runs/end                               (REST-ful)
  ✅ /api/runs/{id}                              (REST-ful)
```

### Target State (Consistent)

```
AccountController:
  ✅ /api/accounts                               (POST - create)
  ✅ /api/accounts/{agentId}/balance             (GET - query)
  ✅ /api/accounts/{agentId}/holdings            (GET - query)
  ✅ /api/accounts/{agentId}/trades              (POST - create)
  ✅ /api/accounts/{agentId}/activity            (PUT - update)
  ✅ /api/accounts/resources/accounts/{agentId}  (GET - report)
  ✅ /api/accounts/portfolio/{agentId}/history   (GET - history)
  ✅ /api/accounts/trades/recent                 (GET - list)
  ✅ /api/accounts/trades/{tradeId}              (GET - detail)

MarketController:
  ✅ /api/market/price/{symbol}                  (GET)
  ✅ /api/market/historical/{symbol}             (GET)
  ✅ /api/market/indicators/{symbol}             (GET)

RunController:
  ✅ /api/runs/start                             (POST)
  ✅ /api/runs/end                               (POST)
  ✅ /api/runs/{id}                              (GET)
```

**Pattern**: `/api/{resource}/{id}/{sub-resource}` or `/api/{resource}/{action}`

---

## Response Payload Size Comparison

### Example: Get Balance

**Current**:
```json
{
  "success": true,
  "data": 95000.0,
  "error": null
}
```
**Size**: 61 bytes

**Target**:
```json
{"balance": 95000.0}
```
**Size**: 20 bytes

**Savings**: 67% reduction (41 bytes saved)

### Example: Error Response

**Current**:
```json
{
  "success": false,
  "data": null,
  "error": "Agent not found: Warren"
}
```
**Size**: 74 bytes

**Target**:
```json
{
  "type": "https://trading.example.com/errors/resource-not-found",
  "title": "Resource Not Found",
  "status": 404,
  "detail": "Agent not found: Warren",
  "instance": "/api/accounts/999/balance"
}
```
**Size**: 213 bytes

**Cost**: 188% increase (139 bytes added)

**Trade-off**: Error responses larger but more structured and informative (RFC 7807 standard). Errors are rare, so overall bandwidth savings from success responses outweigh this.

---

## Standards Compliance

### Current State

| Standard | Compliant? | Notes |
|----------|-----------|-------|
| HTTP 1.1 Methods | ❌ Partial | POST used for queries |
| REST | ❌ Partial | Mixed patterns |
| RFC 7807 (Problem Details) | ❌ No | Custom error format |
| OpenAPI 3.0 | ⚠️ Partial | Can be documented but non-standard |
| HTTP Status Codes | ✅ Yes | Correct codes used |

### Target State

| Standard | Compliant? | Notes |
|----------|-----------|-------|
| HTTP 1.1 Methods | ✅ Yes | Correct methods for operations |
| REST | ✅ Yes | Resource-based, standard patterns |
| RFC 7807 (Problem Details) | ✅ Yes | Structured error responses |
| OpenAPI 3.0 | ✅ Yes | Standard DTOs, easy to document |
| HTTP Status Codes | ✅ Yes | Correct codes used |

---

## Migration Strategy

### Phase-by-Phase Changes

```
Phase 1: Error Infrastructure
├─ Add ProblemDetailFactory
├─ Enable Spring ProblemDetail support
└─ Test error response format

Phase 2: Exception Handlers
├─ AccountControllerAdvice → ProblemDetail
├─ RunControllerAdvice → ProblemDetail
└─ GlobalExceptionHandler → ProblemDetail

Phase 3: Controller Refactor (Remove ToolResponse)
├─ AgentStatusController
├─ MarketController
├─ TradingController
├─ RunController
└─ AccountController (partial)

Phase 4: AccountController Paths
├─ Add new REST endpoints
├─ Keep old /tools/* endpoints (deprecated)
└─ Both work simultaneously

Phase 5: Python Agents
├─ Update trading_tools.py
├─ Update market_tools.py
├─ Test locally
└─ Python agents call new endpoints

Phase 6: Cleanup
├─ Remove old /tools/* endpoints
├─ Delete ToolResponse.java
└─ Remove deprecated request DTOs

Phase 7: Deploy
├─ Deploy to staging
├─ Verify functionality
├─ Deploy to production
└─ Monitor
```

### Backwards Compatibility Window

```
Phase 4: Both old and new endpoints work
Phase 5: Python agents updated to use new endpoints
Phase 6: Old endpoints removed

Window: ~1-2 days where both old and new endpoints work
```

---

## Architectural Principles Applied

1. **Single Responsibility** - Controllers handle HTTP, Services handle business logic, ControllerAdvice handles exceptions

2. **Open/Closed** - New DTOs can be added without changing existing ones

3. **Liskov Substitution** - All controllers follow same pattern (return DTOs, throw domain exceptions)

4. **Interface Segregation** - Clean DTOs with only necessary fields

5. **Dependency Inversion** - Controllers depend on Service abstractions, not implementations

6. **DRY (Don't Repeat Yourself)** - ProblemDetailFactory eliminates duplication in error handling

7. **KISS (Keep It Simple)** - Remove unnecessary ToolResponse wrapper

8. **YAGNI (You Aren't Gonna Need It)** - Remove tool-specific patterns, just use standard REST

---

## Conclusion

This refactoring transforms a tool-specific API into a generic, standards-compliant REST API that:

✅ Follows HTTP/REST best practices
✅ Uses standard error formats (RFC 7807)
✅ Reduces payload size for success responses
✅ Improves developer experience (no wrapper unwrapping)
✅ Makes API callable by any HTTP client
✅ Maintains all existing functionality
✅ Can be rolled back if needed

**Ready for implementation** - See `api-refactoring-plan.md` for detailed steps.
