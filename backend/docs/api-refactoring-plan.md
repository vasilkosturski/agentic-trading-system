# API Refactoring Plan: Remove Tool Patterns & Adopt REST Conventions

## Executive Summary

**Goal**: Transform the trading system API from tool-specific patterns to generic REST conventions, making it callable by any HTTP client (not just AI tools).

**Scope**: 5 controllers, 3 exception handlers, ~20 endpoints, Python agent integration, comprehensive test suite

**Timeline**: 3-4 days for implementation + testing + deployment

---

## Current State Analysis

### Tool-Specific Patterns Identified

1. **ToolResponse Wrapper** (in all tool endpoints)
   - Returns `{"success": boolean, "data": T, "error": string}`
   - Success indicated in JSON body instead of HTTP status codes
   - Used by: AccountController, RunController, AgentStatusController, MarketController, TradingController

2. **Tool-Prefixed Paths** (in AccountController only)
   - `/api/accounts/tools/get_balance` → Should be `/api/accounts/{agentId}/balance`
   - `/api/accounts/tools/get_holdings` → Should be `/api/accounts/{agentId}/holdings`
   - `/api/accounts/tools/buy_shares` → Should be `/api/accounts/{agentId}/trades` (POST)
   - `/api/accounts/tools/sell_shares` → Should be `/api/accounts/{agentId}/trades` (POST with type)
   - `/api/accounts/tools/initialize_agent` → Should be `/api/accounts` (POST)
   - `/api/accounts/tools/update_activity` → Should be `/api/accounts/{agentId}/activity` (PUT)

3. **ToolResponse in Exception Handlers**
   - AccountControllerAdvice, RunControllerAdvice, GlobalExceptionHandler all return ToolResponse
   - Should return RFC 7807 ProblemDetail instead

### Files Requiring Changes

**Controllers** (5 files):
- `/backend/src/main/java/com/trading/controller/AccountController.java` - 6 tool endpoints + paths
- `/backend/src/main/java/com/trading/controller/RunController.java` - 5 tool endpoints
- `/backend/src/main/java/com/trading/controller/AgentStatusController.java` - 1 tool endpoint
- `/backend/src/main/java/com/trading/controller/MarketController.java` - 6 tool endpoints (but paths OK)
- `/backend/src/main/java/com/trading/controller/TradingController.java` - 2 tool endpoints

**Exception Handlers** (3 files):
- `/backend/src/main/java/com/trading/controller/advice/AccountControllerAdvice.java`
- `/backend/src/main/java/com/trading/controller/advice/RunControllerAdvice.java`
- `/backend/src/main/java/com/trading/exception/GlobalExceptionHandler.java`

**Python Agents** (2 files):
- `/agents/trading_tools.py` - Calls AccountController endpoints
- `/agents/market_tools.py` - Calls MarketController endpoints

**Tests** (2+ files):
- `/backend/src/test/java/com/trading/controller/AccountControllerTest.java`
- `/backend/src/test/java/com/trading/controller/TradingControllerTriggerCycleTest.java`
- Other controller tests (need to identify)

**DTOs** (1 file to DELETE):
- `/backend/src/main/java/com/trading/dto/response/ToolResponse.java`

---

## Target State Design

### REST Endpoint Conventions

#### AccountController - Full Redesign

**Current → Target Mapping:**

```
POST /api/accounts/tools/initialize_agent
  Body: {"name": "Warren", "initialBalance": 100000}
→ POST /api/accounts
  Body: {"name": "Warren", "initialBalance": 100000}
  Response: 201 Created + AccountDto

POST /api/accounts/tools/get_balance
  Body: {"agentId": 1}
→ GET /api/accounts/{agentId}/balance
  Response: 200 OK + {"balance": 95000.0}

POST /api/accounts/tools/get_holdings
  Body: {"agentId": 1}
→ GET /api/accounts/{agentId}/holdings
  Response: 200 OK + [{"symbol": "AAPL", "quantity": 10, ...}]

POST /api/accounts/tools/buy_shares
  Body: {"agentId": 1, "symbol": "AAPL", "quantity": 10, "runId": 42}
→ POST /api/accounts/{agentId}/trades
  Body: {"symbol": "AAPL", "quantity": 10, "type": "BUY", "runId": 42}
  Response: 201 Created + TradeResult

POST /api/accounts/tools/sell_shares
  Body: {"agentId": 1, "symbol": "AAPL", "quantity": 5, "runId": 42}
→ POST /api/accounts/{agentId}/trades
  Body: {"symbol": "AAPL", "quantity": 5, "type": "SELL", "runId": 42}
  Response: 201 Created + TradeResult

POST /api/accounts/tools/update_activity
  Body: {"agentId": 1}
→ PUT /api/accounts/{agentId}/activity
  Response: 204 No Content
```

#### RunController - Remove ToolResponse Only

Paths are already reasonable (`/api/runs/*`), just remove ToolResponse:

```
POST /api/runs/start → Returns Long (runId) directly with 201
POST /api/runs/end → Returns String message directly with 200
POST /api/runs/error → Returns String message directly with 200
POST /api/runs/{runId}/tool-call → Returns Long (callId) directly with 201
POST /api/runs/{runId}/reasoning-step → Returns Long (stepId) directly with 201
```

#### MarketController - Remove ToolResponse Only

Paths are already REST-ful (`/api/market/*`), just remove ToolResponse:

```
GET /api/market/price/{symbol} → Returns PriceData directly with 200
GET /api/market/historical/{symbol}?days=30 → Returns HistoricalPriceData with 200
GET /api/market/indicators/{symbol} → Returns MarketIndicatorsData with 200
POST /api/market/cache/clear → Returns String message with 200
```

#### TradingController - Remove ToolResponse Only

```
GET /api/trading/agents/status → Returns List<AgentStatusResponse> with 200
GET /api/trading/agent-trades?agentId=1 → Returns List<AgentTradeResponse> with 200
POST /api/trading/run-cycle → Returns TriggerCycleResponse with 202 Accepted
```

#### AgentStatusController - Remove ToolResponse Only

```
POST /api/agents/status → Returns 204 No Content (success) or 500 (error)
```

### Error Response Format (RFC 7807)

**Current** (ToolResponse error):
```json
{
  "success": false,
  "data": null,
  "error": "Agent not found: Warren"
}
```

**Target** (ProblemDetail):
```json
{
  "type": "https://trading.example.com/errors/resource-not-found",
  "title": "Resource Not Found",
  "status": 404,
  "detail": "Agent not found: Warren",
  "instance": "/api/accounts/999"
}
```

### Exception Handler Mapping

| Exception | HTTP Status | ProblemDetail Type |
|-----------|-------------|-------------------|
| ResourceNotFoundException | 404 Not Found | resource-not-found |
| BusinessRuleException | 409 Conflict | business-rule-violation |
| IllegalArgumentException | 400 Bad Request | invalid-request |
| MethodArgumentNotValidException | 400 Bad Request | validation-error |
| Exception (generic) | 500 Internal Server Error | internal-error |

---

## Implementation Phases

### Phase 1: Create New Error Infrastructure (Day 1, ~2 hours)

**Goal**: Set up ProblemDetail support without breaking existing code

**Steps**:

1. **Create ProblemDetailFactory utility class**
   - Location: `/backend/src/main/java/com/trading/exception/ProblemDetailFactory.java`
   - Methods:
     ```java
     public class ProblemDetailFactory {
         public static ProblemDetail resourceNotFound(String detail, String instance) {...}
         public static ProblemDetail businessRuleViolation(String detail, String instance) {...}
         public static ProblemDetail invalidRequest(String detail, String instance) {...}
         public static ProblemDetail validationError(String detail, String instance, Map<String, String> errors) {...}
         public static ProblemDetail internalError(String detail, String instance) {...}
     }
     ```

2. **Update application.properties**
   - Add: `spring.mvc.problemdetails.enabled=true`

3. **Test ProblemDetailFactory**
   - Create: `/backend/src/test/java/com/trading/exception/ProblemDetailFactoryTest.java`
   - Verify JSON serialization matches RFC 7807

**Validation**: Run tests, ensure no existing code breaks

---

### Phase 2: Update Exception Handlers (Day 1, ~2 hours)

**Goal**: Make exception handlers return ProblemDetail while ToolResponse still exists

**Steps**:

1. **Update AccountControllerAdvice**
   - Change return type: `ResponseEntity<ToolResponse<Object>>` → `ResponseEntity<ProblemDetail>`
   - Replace `ToolResponse.error(...)` with `ProblemDetailFactory.resourceNotFound(...)`
   - Example:
     ```java
     @ExceptionHandler(ResourceNotFoundException.class)
     public ResponseEntity<ProblemDetail> handleResourceNotFound(ResourceNotFoundException ex, HttpServletRequest request) {
         ProblemDetail problem = ProblemDetailFactory.resourceNotFound(ex.getMessage(), request.getRequestURI());
         return ResponseEntity.status(404).body(problem);
     }
     ```

2. **Update RunControllerAdvice** (if exists, didn't see it in files)
   - Same pattern as AccountControllerAdvice

3. **Update GlobalExceptionHandler**
   - Same pattern for all exception handlers
   - Add HttpServletRequest parameter to get URI for `instance` field

4. **Update controller tests**
   - Change assertions from `.jsonPath("$.success", is(false))` to `.jsonPath("$.status", is(404))`
   - Update expected error format to ProblemDetail

**Validation**: Run `./gradlew test` - some tests will fail (expected), but no compile errors

---

### Phase 3: Update Controllers - Remove ToolResponse (Day 1-2, ~6 hours)

**Goal**: Remove ToolResponse from controller methods, return DTOs directly

**Order of changes** (least breaking → most breaking):

#### 3.1 AgentStatusController (Simplest - already returns 204)
- Change method signature: `ResponseEntity<ToolResponse<String>>` → `ResponseEntity<Void>`
- Remove ToolResponse wrapper from error case
- Update test

#### 3.2 MarketController (No path changes, just wrapper removal)
- 6 endpoints to update
- Example:
  ```java
  // Before
  @GetMapping("/price/{symbol}")
  public ResponseEntity<ToolResponse<PriceData>> getSharePrice(@PathVariable String symbol) {
      return ResponseEntity.ok(ToolResponse.success(priceData));
  }

  // After
  @GetMapping("/price/{symbol}")
  public ResponseEntity<PriceData> getSharePrice(@PathVariable String symbol) {
      return ResponseEntity.ok(priceData);
  }
  ```
- Remove try-catch blocks (let exception handlers deal with errors)
- Update tests

#### 3.3 TradingController (2 endpoints)
- Update `/agents/status` and `/agent-trades` to remove ToolResponse
- Keep `/run-cycle` special error handling but return ProblemDetail
- Update tests

#### 3.4 RunController (5 endpoints)
- Remove ToolResponse wrapper
- Return simple types directly (Long, String)
- Update tests

#### 3.5 AccountController (Most complex - 6 tool endpoints + path changes)
- **First**: Remove ToolResponse from existing endpoints (don't change paths yet)
- **Then**: Refactor paths in next phase

**Validation**: Run `./gradlew test` after each controller, fix tests incrementally

---

### Phase 4: Refactor AccountController Paths (Day 2, ~4 hours)

**Goal**: Replace `/tools/*` paths with proper REST conventions

**Steps**:

1. **Add new REST endpoints** (don't remove old ones yet)
   ```java
   // New REST endpoint
   @GetMapping("/{agentId}/balance")
   public ResponseEntity<BalanceDto> getBalance(@PathVariable Long agentId) {...}

   // Old tool endpoint (keep for backwards compatibility)
   @PostMapping("/tools/get_balance")
   @Deprecated
   public ResponseEntity<BalanceDto> getBalanceTool(@RequestBody GetBalanceRequest request) {
       return getBalance(request.getAgentId());
   }
   ```

2. **Implement for all 6 endpoints**:
   - `GET /{agentId}/balance` (replaces `/tools/get_balance`)
   - `GET /{agentId}/holdings` (replaces `/tools/get_holdings`)
   - `POST /{agentId}/trades` (replaces `/tools/buy_shares` + `/tools/sell_shares`)
   - `PUT /{agentId}/activity` (replaces `/tools/update_activity`)
   - `POST /` (replaces `/tools/initialize_agent`)

3. **Create new TradeRequest DTO** for unified trades endpoint:
   ```java
   public class TradeRequest {
       @NotBlank private String symbol;
       @Positive private Integer quantity;
       @NotNull private TradeType type; // enum: BUY, SELL
       private Long runId;
   }
   ```

4. **Update tests** to use new paths
   - Add tests for new REST endpoints
   - Mark old tests as deprecated

**Validation**: Both old and new endpoints work, tests pass

---

### Phase 5: Update Python Agents (Day 2-3, ~3 hours)

**Goal**: Make Python agents call new REST endpoints

**Strategy**: Update HTTP calls without changing function signatures

**Steps**:

1. **Update trading_tools.py**:
   ```python
   # Before
   async def get_balance(agent_id: int) -> float:
       result = await _call_backend_api("/tools/get_balance", {"agentId": agent_id})
       return float(result)

   # After
   async def get_balance(agent_id: int) -> float:
       url = f"{BACKEND_URL}/{agent_id}/balance"
       response = await call_backend("GET", url)
       data = response.json()  # Direct response, no .data field
       return float(data["balance"])
   ```

2. **Update all trading tool functions**:
   - `get_balance()` - Change to GET `/{agentId}/balance`
   - `get_holdings()` - Change to GET `/{agentId}/holdings`
   - `buy_shares()` - Change to POST `/{agentId}/trades` with `{"type": "BUY", ...}`
   - `sell_shares()` - Change to POST `/{agentId}/trades` with `{"type": "SELL", ...}`
   - `initialize_agent()` - Change to POST `/` with agent data

3. **Update market_tools.py**:
   - Remove ToolResponse unwrapping: `result.get("data")` → `response.json()`
   - Handle errors via HTTP status codes instead of `success` field

4. **Update error handling**:
   ```python
   # Before
   result = response.json()
   if result.get("success"):
       return result.get("data")
   else:
       raise Exception(result.get("error"))

   # After
   # Errors come as 4xx/5xx status codes (already handled by call_backend)
   return response.json()
   ```

5. **Test Python agents locally**:
   - Run `python trading_system.py` against local backend
   - Verify all trading operations work

**Validation**: Python agents work with new API, no ToolResponse dependency

---

### Phase 6: Remove Deprecated Code (Day 3, ~2 hours)

**Goal**: Clean up old code after Python agents updated

**Steps**:

1. **Remove old `/tools/*` endpoints** from AccountController
   - Delete 6 deprecated methods
   - Delete old request DTOs if not used elsewhere

2. **Delete ToolResponse class**
   - `/backend/src/main/java/com/trading/dto/response/ToolResponse.java`

3. **Remove ToolResponse imports** from all files
   - Controllers, exception handlers, tests

4. **Clean up tests**
   - Remove deprecated test cases
   - Verify all tests pass

**Validation**: `./gradlew clean build` passes, no compiler warnings

---

### Phase 7: Documentation & Deployment (Day 3-4, ~2 hours)

**Goal**: Update API documentation and deploy to staging

**Steps**:

1. **Update OpenAPI documentation** (if exists)
   - Add new endpoints
   - Document ProblemDetail error format
   - Add examples

2. **Update CLAUDE.md or API docs**
   - Document new REST conventions
   - Add migration guide for any external clients

3. **Deploy to staging**
   - Backend: `cd deployment/k3s && ./deploy-to-k3s.sh -e staging -c backend`
   - Agents: `./deploy-to-k3s.sh -e staging -c agents`

4. **Verify staging**
   - Test all endpoints via React UI
   - Check logs for errors
   - Test manual trading cycle

5. **Deploy to production** (only after staging verified)
   - `./deploy-to-k3s.sh -c backend`
   - `./deploy-to-k3s.sh -c agents`

**Validation**: Production system works as before, API is REST-compliant

---

## Testing Strategy

### Unit Tests

**Phase 2-3**: Update as controllers change
- AccountControllerTest - Update all assertions to expect direct DTOs
- MarketControllerTest - Remove ToolResponse expectations
- TradingControllerTest - Update to ProblemDetail error format
- RunControllerTest - Update to direct return types

**Assertion Changes**:
```java
// Before
mockMvc.perform(post("/api/accounts/tools/get_balance")...)
    .andExpect(jsonPath("$.success", is(true)))
    .andExpect(jsonPath("$.data", is(100000.0)));

// After
mockMvc.perform(get("/api/accounts/1/balance"))
    .andExpect(status().isOk())
    .andExpect(jsonPath("$.balance", is(100000.0)));
```

### Integration Tests

**Phase 5**: Test Python agent integration
- Start local backend: `./gradlew bootRun`
- Run Python agents: `python trading_system.py`
- Verify trades execute correctly
- Check database for correct data

### Regression Tests

**Phase 7**: Full system test in staging
- Test all 4 agents (Warren, George, Ray, Cathie)
- Verify manual trading cycle
- Check React dashboard displays correctly
- Verify WebSocket updates work

---

## Rollback Plan

### If Issues Found in Phase 1-4 (Backend only)
- **Action**: Revert git commits
- **Impact**: None (Python agents still work with old endpoints)
- **Time**: < 5 minutes

### If Issues Found in Phase 5 (Python agents updated)
- **Action**:
  1. Keep new REST endpoints
  2. Re-add old `/tools/*` endpoints (copy from git history)
  3. Revert Python agent changes
- **Impact**: Temporary dual endpoints until fix deployed
- **Time**: ~30 minutes

### If Issues Found in Production (Phase 7)
- **Action**:
  1. Rollback backend deployment: Redeploy previous Docker image
  2. Rollback agents deployment: Redeploy previous Docker image
- **Impact**: ~5 minutes downtime during rollback
- **Time**: ~10 minutes

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Tests break during refactor | High | Medium | Update tests incrementally per phase |
| Python agents can't parse new responses | Medium | High | Test locally before deploying, keep old endpoints temporarily |
| Production errors after deployment | Low | High | Deploy to staging first, thorough testing |
| Forgot to update some controller | Low | Medium | Code review checklist, grep for ToolResponse |
| Frontend breaks due to API changes | Medium | Medium | Most endpoints used by Python only; test React UI in staging |

---

## Dependencies & Prerequisites

### Development Environment
- Java 17 (for backend changes)
- Python 3.11 (for agent testing)
- Docker + docker-compose (for local testing)
- PostgreSQL (running locally or in Docker)

### Code Review Checklist
- [ ] All ToolResponse imports removed
- [ ] All exception handlers return ProblemDetail
- [ ] All controller methods return DTOs directly
- [ ] HTTP status codes used correctly (200, 201, 204, 400, 404, 409, 500)
- [ ] Python agents updated to call new endpoints
- [ ] All tests pass (`./gradlew test`)
- [ ] OpenAPI docs updated (if applicable)
- [ ] Staging deployment successful
- [ ] Production deployment successful

---

## Example: Before & After (Complete Flow)

### AccountController - Buy Shares Endpoint

**Before**:
```java
// Controller
@PostMapping("/tools/buy_shares")
public ResponseEntity<ToolResponse<TradeResult>> buyShares(@Valid @RequestBody BuySharesRequest request) {
    String name = agentIdentityService.requireAgentName(request.getAgentId());
    TradeResult result = accountService.buyShares(name, request.getSymbol(), request.getQuantity(), request.getRunId());
    return ResponseEntity.status(201).body(ToolResponse.success(result));
}

// Exception Handler (AccountControllerAdvice)
@ExceptionHandler(BusinessRuleException.class)
public ResponseEntity<ToolResponse<Object>> handleBusinessRule(BusinessRuleException ex) {
    return ResponseEntity.status(409).body(ToolResponse.error(ex.getMessage()));
}

// Python Agent (trading_tools.py)
async def buy_shares(agent_id: int, symbol: str, quantity: int, runId: int) -> str:
    result = await _call_backend_api("/tools/buy_shares", {
        "agentId": agent_id, "symbol": symbol, "quantity": quantity, "runId": runId
    })
    return str(result)

// Success Response (201)
{
  "success": true,
  "data": {
    "transactionId": 42,
    "symbol": "AAPL",
    "quantity": 10,
    "price": 150.0,
    "message": "Bought 10 shares of AAPL at $150.00"
  },
  "error": null
}

// Error Response (409)
{
  "success": false,
  "data": null,
  "error": "Insufficient funds: Need $1500.00, have $1000.00"
}
```

**After**:
```java
// Controller
@PostMapping("/{agentId}/trades")
public ResponseEntity<TradeResult> executeTrade(
    @PathVariable Long agentId,
    @Valid @RequestBody TradeRequest request
) {
    String name = agentIdentityService.requireAgentName(agentId);
    TradeResult result;
    if (request.getType() == TradeType.BUY) {
        result = accountService.buyShares(name, request.getSymbol(), request.getQuantity(), request.getRunId());
    } else {
        result = accountService.sellShares(name, request.getSymbol(), request.getQuantity(), request.getRunId());
    }
    return ResponseEntity.status(201).body(result);
}

// Exception Handler (AccountControllerAdvice)
@ExceptionHandler(BusinessRuleException.class)
public ResponseEntity<ProblemDetail> handleBusinessRule(BusinessRuleException ex, HttpServletRequest request) {
    ProblemDetail problem = ProblemDetailFactory.businessRuleViolation(ex.getMessage(), request.getRequestURI());
    return ResponseEntity.status(409).body(problem);
}

// Python Agent (trading_tools.py)
async def buy_shares(agent_id: int, symbol: str, quantity: int, runId: int) -> str:
    url = f"{BACKEND_URL}/{agent_id}/trades"
    response = await call_backend("POST", url, json_data={
        "symbol": symbol, "quantity": quantity, "type": "BUY", "runId": runId
    })
    result = response.json()  # Direct JSON, no .data wrapper
    return result["message"]

// Success Response (201)
{
  "transactionId": 42,
  "symbol": "AAPL",
  "quantity": 10,
  "price": 150.0,
  "message": "Bought 10 shares of AAPL at $150.00"
}

// Error Response (409)
{
  "type": "https://trading.example.com/errors/business-rule-violation",
  "title": "Business Rule Violation",
  "status": 409,
  "detail": "Insufficient funds: Need $1500.00, have $1000.00",
  "instance": "/api/accounts/1/trades"
}
```

**Key Changes**:
1. ✅ Path: `/tools/buy_shares` → `/{agentId}/trades`
2. ✅ Method: POST with agentId in URL, not body
3. ✅ Request: Unified TradeRequest with `type` field (BUY/SELL)
4. ✅ Response: Direct TradeResult, no ToolResponse wrapper
5. ✅ Status: Still 201 Created for success
6. ✅ Error: ProblemDetail instead of ToolResponse.error()
7. ✅ Python: GET/POST to REST path, unwrap direct JSON

---

## Success Criteria

### Technical Criteria
- [ ] Zero references to ToolResponse in codebase
- [ ] All controllers return DTOs directly
- [ ] All errors return ProblemDetail (RFC 7807)
- [ ] HTTP status codes used correctly
- [ ] AccountController paths follow REST conventions
- [ ] All unit tests pass
- [ ] All integration tests pass

### Functional Criteria
- [ ] Python agents execute trades successfully
- [ ] React dashboard displays data correctly
- [ ] Manual trading cycle works
- [ ] All 4 agents (Warren, George, Ray, Cathie) function properly
- [ ] WebSocket updates work
- [ ] Error messages are clear and actionable

### Operational Criteria
- [ ] Staging deployment successful
- [ ] Production deployment successful
- [ ] No increase in error rates
- [ ] No performance degradation
- [ ] Rollback plan tested and documented

---

## Next Steps

1. **Review this plan** with team/user
2. **Create implementation branch**: `git checkout -b refactor/api-rest-conventions`
3. **Start Phase 1**: Create ProblemDetailFactory
4. **Proceed sequentially** through phases 2-7
5. **Deploy to staging first** - mandatory!
6. **Deploy to production** only after user approval

**Estimated Timeline**: 3-4 days (can be faster if focused)

**Recommended Assignment**: Hand to @agent-code for implementation, one phase at a time
