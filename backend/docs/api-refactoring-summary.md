# API Refactoring Summary

## Problem Statement

The trading system API currently uses patterns that couple it to AI tool usage:
- All endpoints wrap responses in `ToolResponse<T>` with `success` boolean field
- Success/failure indicated in JSON body instead of HTTP status codes
- Some endpoints use `/tools` prefix (AccountController)
- Not callable by generic HTTP clients without understanding tool conventions

## Solution

Transform API to follow standard REST conventions:
1. **Remove ToolResponse wrapper** - Controllers return DTOs directly
2. **Use HTTP status codes** - 200/201/204 for success, 400/404/409/500 for errors
3. **Adopt RFC 7807 ProblemDetail** - Structured error responses
4. **REST-ful paths** - Replace `/tools/*` with resource-based paths
5. **Proper HTTP methods** - GET for queries, POST for creates, PUT for updates

## Scope

**5 Controllers** affected:
- AccountController (6 tool endpoints + path changes) - **Most work here**
- RunController (5 tool endpoints, paths OK)
- MarketController (6 tool endpoints, paths OK)
- TradingController (2 tool endpoints, paths OK)
- AgentStatusController (1 tool endpoint, mostly done)

**3 Exception Handlers** to update:
- AccountControllerAdvice
- RunControllerAdvice (if exists)
- GlobalExceptionHandler

**2 Python Files** to update:
- trading_tools.py (calls AccountController)
- market_tools.py (calls MarketController)

**~20 Endpoints** total to refactor

## Key Changes

### Endpoint Path Examples

```
OLD: POST /api/accounts/tools/get_balance
     Body: {"agentId": 1}
     Response: {"success": true, "data": 95000.0, "error": null}

NEW: GET /api/accounts/1/balance
     Response: {"balance": 95000.0}
     Status: 200 OK
```

### Error Response Examples

```
OLD: {"success": false, "data": null, "error": "Agent not found"}
     Status: 404 (but client has to check both status AND success field)

NEW: {
       "type": "https://trading.example.com/errors/resource-not-found",
       "title": "Resource Not Found",
       "status": 404,
       "detail": "Agent not found: Warren",
       "instance": "/api/accounts/999/balance"
     }
     Status: 404 (client can trust status code alone)
```

## Timeline

**Estimated**: 3-4 days (21 hours work)

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1. Error Infrastructure | 2h | ProblemDetailFactory |
| 2. Exception Handlers | 2h | ProblemDetail responses |
| 3. Controller Refactor | 6h | Direct DTOs |
| 4. AccountController Paths | 4h | REST conventions |
| 5. Python Agents | 3h | New API calls |
| 6. Cleanup | 2h | Delete ToolResponse |
| 7. Deploy | 2h | Staging + Production |

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Python agents break | Test locally before deploying, keep old endpoints temporarily |
| Tests fail during refactor | Update tests incrementally per phase |
| Production errors | Deploy to staging first, thorough testing |
| Frontend breaks | Test React UI in staging, most endpoints used by Python only |

## Benefits

1. **Generic REST API** - Callable by any HTTP client
2. **Standard conventions** - Follows HTTP/REST best practices
3. **Better tooling** - Standard tools work (curl, Postman, browsers)
4. **Clearer errors** - RFC 7807 provides structure
5. **Easier debugging** - Status codes tell the story
6. **Future-proof** - Not tied to AI tool patterns

## Breaking Changes

### For Python Agents (Fixed in Phase 5)
- HTTP methods change: `POST` → `GET` for queries
- Request body changes: agentId moves to URL path
- Response unwrapping: `result.get("data")` → `response.json()`
- Error handling: Already handled via status codes

### For External Clients (if any)
- None - this is internal API between backend and Python agents
- React frontend uses different endpoints (already REST-ful)

## Rollback Plan

**Before Phase 5** (Python agents updated):
- Simply revert git commits
- No impact, Python agents still use old endpoints

**After Phase 5** (Python agents updated):
- Re-add old `/tools/*` endpoints (copy from git)
- Revert Python agent changes
- ~30 minutes to restore

**Production Issues**:
- Rollback Docker images to previous version
- ~10 minutes, ~5 minutes downtime

## Success Criteria

### Code
- [ ] Zero `ToolResponse` references in codebase
- [ ] All controllers return DTOs directly
- [ ] All errors return ProblemDetail
- [ ] AccountController paths follow REST conventions
- [ ] All tests pass

### Function
- [ ] Python agents execute trades successfully
- [ ] React dashboard works correctly
- [ ] Manual trading cycle works
- [ ] No increase in error rates
- [ ] No performance degradation

### Deployment
- [ ] Staging deployment successful
- [ ] Production deployment successful
- [ ] Monitoring shows healthy system

## Next Steps

1. **Review** this plan with stakeholders
2. **Create branch**: `refactor/api-rest-conventions`
3. **Implement** phases 1-7 sequentially
4. **Test** each phase before proceeding
5. **Deploy to staging** after Phase 6
6. **Get approval** from user
7. **Deploy to production** only after staging verified

## Decision Points

### Before Starting
- [ ] User approves the refactoring plan
- [ ] Timeline acceptable (3-4 days)
- [ ] Understand rollback procedures

### Before Phase 5 (Python Agents)
- [ ] All backend changes tested and working
- [ ] Tests all pass
- [ ] Decision: Update Python agents now or later?

### Before Phase 7 (Production Deploy)
- [ ] Staging thoroughly tested
- [ ] No errors in staging logs
- [ ] User approves production deployment

## Documentation

**Created**:
- `/backend/docs/api-refactoring-plan.md` - Detailed implementation plan
- `/backend/docs/api-refactoring-quick-reference.md` - Endpoint migration map
- `/backend/docs/api-refactoring-summary.md` - This document

**To Update**:
- CLAUDE.md - Document new REST conventions
- OpenAPI/Swagger docs (if exists)
- README.md (if API documented there)

## Hand-off to @agent-code

This plan is ready for implementation. Suggested approach:

1. **Read** `/backend/docs/api-refactoring-plan.md` for detailed steps
2. **Reference** `/backend/docs/api-refactoring-quick-reference.md` for quick lookups
3. **Implement** one phase at a time
4. **Commit** after each phase with descriptive messages
5. **Test** after each phase before proceeding
6. **Ask** if any step is unclear

**Recommended commit messages**:
```
Phase 1: Add ProblemDetailFactory for RFC 7807 error responses
Phase 2: Update exception handlers to return ProblemDetail
Phase 3: Remove ToolResponse from MarketController
Phase 3: Remove ToolResponse from TradingController
Phase 3: Remove ToolResponse from RunController
Phase 3: Remove ToolResponse from AgentStatusController
Phase 4: Add REST endpoints to AccountController
Phase 4: Deprecate /tools/* endpoints in AccountController
Phase 5: Update Python agents to call new REST endpoints
Phase 6: Remove deprecated /tools/* endpoints
Phase 6: Delete ToolResponse class
Phase 7: Update API documentation
```

## Contact

For questions about this refactoring:
- **Architectural decisions**: @architect agent
- **Implementation questions**: @agent-code
- **Deployment issues**: Follow deployment docs
- **Python agent issues**: Check trading_tools.py/market_tools.py

---

**Status**: Ready for implementation
**Created**: 2025-12-26
**Next Action**: Review with user, then hand to @agent-code
