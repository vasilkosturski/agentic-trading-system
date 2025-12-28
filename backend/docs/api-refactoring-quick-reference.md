# API Refactoring Quick Reference

## Endpoint Migration Map

### AccountController

| Old Endpoint (Tool Pattern) | New Endpoint (REST Pattern) | Method | Request Change |
|------------------------------|----------------------------|--------|----------------|
| `POST /api/accounts/tools/initialize_agent` | `POST /api/accounts` | POST | Body unchanged |
| `POST /api/accounts/tools/get_balance` | `GET /api/accounts/{agentId}/balance` | **GET** | agentId in URL, no body |
| `POST /api/accounts/tools/get_holdings` | `GET /api/accounts/{agentId}/holdings` | **GET** | agentId in URL, no body |
| `POST /api/accounts/tools/buy_shares` | `POST /api/accounts/{agentId}/trades` | POST | Add `"type": "BUY"` field, agentId in URL |
| `POST /api/accounts/tools/sell_shares` | `POST /api/accounts/{agentId}/trades` | POST | Add `"type": "SELL"` field, agentId in URL |
| `POST /api/accounts/tools/update_activity` | `PUT /api/accounts/{agentId}/activity` | **PUT** | agentId in URL, no body |

### MarketController (Paths unchanged, just remove ToolResponse)

| Endpoint | Response Change |
|----------|----------------|
| `GET /api/market/price/{symbol}` | Direct `PriceData` (not wrapped) |
| `GET /api/market/price/{symbol}/value` | Direct `Double` (not wrapped) |
| `GET /api/market/historical/{symbol}?days=30` | Direct `HistoricalPriceData` (not wrapped) |
| `GET /api/market/indicators/{symbol}` | Direct `MarketIndicatorsData` (not wrapped) |
| `POST /api/market/cache/clear` | Direct `String` message (not wrapped) |

### RunController (Paths unchanged, just remove ToolResponse)

| Endpoint | Response Change |
|----------|----------------|
| `POST /api/runs/start` | Direct `Long` runId (not wrapped) |
| `POST /api/runs/end` | Direct `String` message (not wrapped) |
| `POST /api/runs/error` | Direct `String` message (not wrapped) |
| `POST /api/runs/{runId}/tool-call` | Direct `Long` callId (not wrapped) |
| `POST /api/runs/{runId}/reasoning-step` | Direct `Long` stepId (not wrapped) |

### TradingController (Paths unchanged, just remove ToolResponse)

| Endpoint | Response Change |
|----------|----------------|
| `GET /api/trading/agents/status` | Direct `List<AgentStatusResponse>` (not wrapped) |
| `GET /api/trading/agent-trades?agentId=1` | Direct `List<AgentTradeResponse>` (not wrapped) |
| `POST /api/trading/run-cycle` | Direct `TriggerCycleResponse` (not wrapped) |

### AgentStatusController (Already returns 204, just cleanup error)

| Endpoint | Change |
|----------|--------|
| `POST /api/agents/status` | Error returns ProblemDetail instead of ToolResponse |

---

## Response Format Changes

### Success Responses

**Before** (ToolResponse wrapper):
```json
{
  "success": true,
  "data": {"balance": 95000.0},
  "error": null
}
```

**After** (Direct DTO):
```json
{"balance": 95000.0}
```

### Error Responses

**Before** (ToolResponse error):
```json
{
  "success": false,
  "data": null,
  "error": "Agent not found: Warren"
}
```

**After** (RFC 7807 ProblemDetail):
```json
{
  "type": "https://trading.example.com/errors/resource-not-found",
  "title": "Resource Not Found",
  "status": 404,
  "detail": "Agent not found: Warren",
  "instance": "/api/accounts/999/balance"
}
```

---

## HTTP Status Code Usage

| Status Code | Use Case | Example |
|-------------|----------|---------|
| 200 OK | Successful GET/PUT | Get balance, update activity |
| 201 Created | Successful POST creating resource | Create agent, execute trade |
| 204 No Content | Successful action, no response body | Update activity (alternative) |
| 400 Bad Request | Invalid input, validation error | Missing required field |
| 404 Not Found | Resource doesn't exist | Agent ID 999 not found |
| 409 Conflict | Business rule violation | Insufficient funds, position limit |
| 500 Internal Server Error | Unexpected server error | Database connection lost |

---

## New DTOs Required

### TradeRequest (unified for buy/sell)

```java
public class TradeRequest {
    @NotBlank
    private String symbol;

    @Positive
    private Integer quantity;

    @NotNull
    private TradeType type; // enum: BUY, SELL

    private Long runId;
}
```

### BalanceDto (explicit balance response)

```java
public class BalanceDto {
    private Double balance;

    public BalanceDto(Double balance) {
        this.balance = balance;
    }
}
```

---

## Python Agent Changes Summary

### trading_tools.py

```python
# BEFORE
async def get_balance(agent_id: int) -> float:
    result = await _call_backend_api("/tools/get_balance", {"agentId": agent_id})
    return float(result)

# AFTER
async def get_balance(agent_id: int) -> float:
    url = f"{BACKEND_URL}/{agent_id}/balance"
    response = await call_backend("GET", url)
    data = response.json()
    return float(data["balance"])
```

### Key Changes in Python
1. Change HTTP method: `POST` → `GET` for queries
2. Move agentId from body to URL path
3. Remove ToolResponse unwrapping: `result.get("data")` → `response.json()`
4. Errors handled via HTTP status codes (already done in http_client.py)

---

## Files to Modify (Checklist)

### Backend - Controllers (5 files)
- [ ] AccountController.java - Add new REST endpoints, deprecate /tools/*
- [ ] RunController.java - Remove ToolResponse wrapper
- [ ] MarketController.java - Remove ToolResponse wrapper
- [ ] TradingController.java - Remove ToolResponse wrapper
- [ ] AgentStatusController.java - Remove ToolResponse from error case

### Backend - Exception Handlers (3 files)
- [ ] AccountControllerAdvice.java - Return ProblemDetail
- [ ] RunControllerAdvice.java - Return ProblemDetail (if exists)
- [ ] GlobalExceptionHandler.java - Return ProblemDetail

### Backend - New Files (1 file)
- [ ] ProblemDetailFactory.java - Create utility for RFC 7807 responses

### Backend - Delete (1 file)
- [ ] ToolResponse.java - Delete after all usages removed

### Backend - Tests (2+ files)
- [ ] AccountControllerTest.java - Update assertions
- [ ] TradingControllerTriggerCycleTest.java - Update assertions
- [ ] Other controller tests - Update assertions

### Python Agents (2 files)
- [ ] trading_tools.py - Update API calls to REST endpoints
- [ ] market_tools.py - Remove ToolResponse unwrapping

### Documentation (1 file)
- [ ] CLAUDE.md or API docs - Document new REST conventions

---

## Testing Checklist

### Unit Tests
- [ ] AccountController: All 6 tool endpoints + new REST endpoints
- [ ] MarketController: Direct DTO responses
- [ ] TradingController: Direct DTO responses
- [ ] RunController: Direct simple types
- [ ] AgentStatusController: ProblemDetail on error
- [ ] ProblemDetailFactory: JSON serialization

### Integration Tests
- [ ] Python agents can call new endpoints
- [ ] Trades execute correctly
- [ ] Database records created properly
- [ ] Error responses parseable by Python

### Regression Tests
- [ ] All 4 agents work (Warren, George, Ray, Cathie)
- [ ] React dashboard displays correctly
- [ ] Manual trading cycle works
- [ ] WebSocket updates work

### Staging Deployment
- [ ] Backend deploys successfully
- [ ] Agents deploy successfully
- [ ] No errors in logs
- [ ] Manual smoke test: trigger cycle, check trades

### Production Deployment
- [ ] Get user approval after staging verification
- [ ] Deploy backend
- [ ] Deploy agents
- [ ] Monitor error rates
- [ ] Verify system functionality

---

## Common Pitfalls

1. **Forgetting to remove ToolResponse import** after changing method signature
   - Symptom: Compiler error "cannot find symbol"
   - Fix: Remove import at top of file

2. **Test assertions still expect ToolResponse format**
   - Symptom: Test fails with "$.success not found"
   - Fix: Change `.jsonPath("$.success", is(true))` to `.jsonPath("$.balance", is(100000.0))`

3. **Python agent expects ToolResponse format**
   - Symptom: KeyError 'data' or KeyError 'success'
   - Fix: Change `result.get("data")` to `response.json()`

4. **HTTP method mismatch in Python**
   - Symptom: 405 Method Not Allowed
   - Fix: Change POST to GET for query endpoints

5. **Missing agentId in URL path**
   - Symptom: 404 Not Found
   - Fix: Add agentId to URL: `f"{BACKEND_URL}/{agent_id}/balance"`

6. **Exception handler still returns ToolResponse**
   - Symptom: ProblemDetail expected but ToolResponse returned
   - Fix: Update exception handler to return ProblemDetail

---

## Rollback Commands

### Revert Backend Changes
```bash
# If in middle of refactoring
git reset --hard HEAD
git checkout main

# If already committed
git revert <commit-hash>
```

### Re-add Old Endpoints (Emergency)
```bash
# Copy old AccountController from git history
git show main:backend/src/main/java/com/trading/controller/AccountController.java > AccountController.java.old

# Manually copy old /tools/* methods back
# (Or use git cherry-pick for specific commits)
```

### Rollback Deployment
```bash
# Re-deploy previous Docker image
cd deployment/k3s
./deploy-to-k3s.sh -c backend -i <previous-image-tag>
./deploy-to-k3s.sh -c agents -i <previous-image-tag>
```

---

## Success Metrics

### Code Quality
- Zero `ToolResponse` references in codebase (grep check)
- All controllers return direct DTOs
- All errors are RFC 7807 compliant
- Test coverage maintained (>80%)

### Functionality
- All Python agent functions work
- React dashboard displays correctly
- No increase in error rates
- Response times unchanged

### Deployment
- Zero downtime deployment
- Staging verified before production
- Rollback plan tested
- Documentation updated

---

## Phase-by-Phase Summary

| Phase | Duration | Risk | Can Rollback? | Key Deliverable |
|-------|----------|------|---------------|-----------------|
| 1. Error Infrastructure | 2 hours | Low | Yes | ProblemDetailFactory |
| 2. Exception Handlers | 2 hours | Low | Yes | ProblemDetail responses |
| 3. Controller Refactor | 6 hours | Medium | Yes | Direct DTOs |
| 4. AccountController Paths | 4 hours | Medium | Yes | REST conventions |
| 5. Python Agents | 3 hours | High | Yes | New API calls |
| 6. Cleanup | 2 hours | Low | Yes | Delete ToolResponse |
| 7. Deploy | 2 hours | Medium | Yes | Production ready |

**Total**: ~21 hours (3 days with breaks/testing)

---

## Post-Refactoring Verification

Run this checklist after completion:

```bash
# 1. No ToolResponse references
grep -r "ToolResponse" backend/src/main/java/com/trading/
# Expected: No results (or only in git history)

# 2. All tests pass
cd backend && ./gradlew test
# Expected: BUILD SUCCESSFUL

# 3. Build succeeds
./gradlew clean build
# Expected: BUILD SUCCESSFUL

# 4. Python agents work locally
cd ../agents && python trading_system.py
# Expected: Agents initialize, execute trades

# 5. Deploy to staging
cd ../deployment/k3s && ./deploy-to-k3s.sh -e staging -c backend,agents
# Expected: Deployment successful

# 6. Staging smoke test
curl https://staging.trading.example.com/api/accounts/1/balance
# Expected: {"balance": 95000.0} (or similar)

# 7. Trigger manual cycle
curl -X POST https://staging.trading.example.com/api/trading/run-cycle
# Expected: 202 Accepted + TriggerCycleResponse
```
