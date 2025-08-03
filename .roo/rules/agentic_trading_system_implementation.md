# Agentic Trading System Implementation Rule

## Rule Configuration

This rule ensures that all implementations in the `agentic-trading-system` project are guided by the implementation plan and maintain consistency with the source project `agents/6_mcp`.

## Core Principles

### 1. Implementation Plan Adherence
All implementations in the `agentic-trading-system` project MUST be dictated by the [`agentic-trading-system/docs/IMPLEMENTATION_PLAN.md`](agentic-trading-system/docs/IMPLEMENTATION_PLAN.md).

**Requirements:**
- Follow the 5-phase implementation plan structure
- Respect the phase dependencies and sequencing
- Update implementation plan status markers when completing tasks
- Reference specific phase and task numbers in implementation work

### 2. Source Project Compatibility
When replicating existing functionality, implementations MUST match the source project [`agents/6_mcp`](agents/6_mcp) exactly.

**Requirements:**
- **Core Functionality**: Replicate behavior identically from source project
- **MCP Server Configuration**: Use identical MCP server parameters and setup
- **Agent Instructions**: Match source project agent prompts and instructions exactly
- **Tool Integration**: Implement same tool patterns and usage
- **Memory System**: Follow exact LibSQL memory/knowledge graph implementation
- **Trading Logic**: Maintain identical autonomous trading behavior

### 3. Enhancement Strategy
The project follows a **"Replicate Core + Extend"** approach:

**REPLICATED Components** (Must Match Source):
- ✅ 4 Autonomous Trading Agents (Warren, George, Ray, Cathie)
- ✅ Researcher Agent with web search and memory capabilities
- 🔄 Memory/Knowledge Graph System (LibSQL)
- 🔄 Push Notification System (Pushover integration)
- 🔄 Market Hours Integration
- 🔄 Trading Floor Orchestration

**ENHANCED Components** (New Capabilities):
- 🚀 Java Spring Boot Backend APIs
- 🚀 React Frontend Dashboard
- 🚀 Real-time Data Feeds
- 🚀 Advanced Analytics and Risk Management
- 🚀 Compliance and Audit Trail
- 🚀 Backtesting Platform

## Implementation Rules

### Rule 1: Phase-Based Development
```yaml
implementation_approach:
  triggers:
    - pattern: "implement|create|add|build"
      condition: "working_on_agentic_trading_system"
      description: "Any implementation work in the trading system"
  requirements:
    - reference_implementation_plan: true
    - identify_current_phase: true
    - check_phase_dependencies: true
    - update_completion_status: true
  priority: high
```

**Before any implementation:**
1. **Reference Implementation Plan**: Check current phase and task status
2. **Identify Dependencies**: Ensure prerequisite phases/tasks are complete
3. **Follow Task Sequence**: Implement in the order specified in the plan
4. **Update Status**: Mark tasks as completed with ✅ when finished

### Rule 2: Source Project Comparison
```yaml
source_comparison:
  triggers:
    - pattern: "replicate|implement.*core|match.*source"
      condition: "functionality_exists_in_source"
      description: "Implementing functionality that exists in source project"
  requirements:
    - analyze_source_implementation: true
    - match_behavior_exactly: true
    - use_identical_patterns: true
    - maintain_compatibility: true
  priority: critical
```

**For replicated functionality:**
1. **Analyze Source**: Study the exact implementation in `agents/6_mcp`
2. **Match Exactly**: Replicate behavior, configuration, and patterns identically
3. **Verify Compatibility**: Ensure the implementation works the same way
4. **Document Differences**: If any changes are needed, document and justify them

### Rule 3: Enhancement Integration
```yaml
enhancement_integration:
  triggers:
    - pattern: "enhance|extend|add.*new"
      condition: "new_functionality_not_in_source"
      description: "Adding new capabilities beyond source project"
  requirements:
    - preserve_core_behavior: true
    - maintain_source_compatibility: true
    - follow_hybrid_architecture: true
    - document_enhancements: true
  priority: high
```

**For new enhancements:**
1. **Preserve Core**: Never break existing replicated functionality
2. **Hybrid Architecture**: Integrate with Java backend and React frontend
3. **Maintain Compatibility**: Ensure core agents still work identically
4. **Document Changes**: Clearly mark what's new vs. replicated

## File Organization Rules

### Core Agent Files (Must Match Source)
```
agentic-trading-system/agents/
├── mcp_params.py           # MUST match agents/6_mcp/mcp_params.py
├── researcher.py           # MUST match agents/6_mcp/templates.py researcher pattern
├── warren_agent.py         # MUST match agents/6_mcp/traders.py + reset.py Warren
├── george_agent.py         # MUST match agents/6_mcp/traders.py + reset.py George
├── ray_agent.py           # MUST match agents/6_mcp/traders.py + reset.py Ray
├── cathie_agent.py        # MUST match agents/6_mcp/traders.py + reset.py Cathie
└── trading_system.py      # MUST match agents/6_mcp/trading_floor.py behavior
```

### Enhancement Files (New Capabilities)
```
agentic-trading-system/
├── backend/               # NEW: Java Spring Boot APIs
├── frontend/              # NEW: React Dashboard
├── mcp-servers/          # ENHANCED: Python MCP servers with Java integration
└── docs/                 # ENHANCED: Implementation plan and documentation
```

## Validation Checklist

### Before Implementation
- [ ] Current phase identified from implementation plan
- [ ] Prerequisites completed and verified
- [ ] Source project behavior analyzed (if replicating)
- [ ] Enhancement approach defined (if extending)

### During Implementation
- [ ] Following exact source patterns (for replicated functionality)
- [ ] Maintaining core behavior compatibility (for enhancements)
- [ ] Testing against source project behavior
- [ ] Documenting implementation decisions

### After Implementation
- [ ] Implementation plan status updated
- [ ] Functionality verified against source project
- [ ] Integration tested with existing components
- [ ] Documentation updated

## Error Prevention

### Common Mistakes to Avoid
1. **Deviating from Source**: Changing core agent behavior without justification
2. **Skipping Phases**: Implementing out of sequence without completing dependencies
3. **Breaking Compatibility**: Enhancements that break existing functionality
4. **Ignoring Plan**: Implementing without referencing the implementation plan

### Quality Gates
1. **Phase Gate**: Cannot proceed to next phase without completing current phase
2. **Source Gate**: Replicated functionality must match source behavior exactly
3. **Integration Gate**: Enhancements must not break core functionality
4. **Documentation Gate**: All changes must be documented in implementation plan

## Usage Examples

### ✅ Correct Implementation Approach
```markdown
## Implementing Phase 2.2: Push Notification MCP Server

### Source Analysis
- Analyzed agents/6_mcp/push_server.py (lines 22-27)
- Identified Pushover integration pattern
- Noted exact tool signature and behavior

### Implementation
- Replicated push_server.py exactly from source
- Added to trader_mcp_server_params following source pattern
- Updated agent instructions to match source templates.py

### Enhancement
- Integrated with Java backend for notification history
- Added React frontend notification management
- Maintained core Pushover functionality unchanged

### Status Update
- [x] 2.2 Add push notification MCP server for trade alerts
```

### ❌ Incorrect Implementation Approach
```markdown
## Adding Custom Notification System

### Implementation
- Created new notification system with different API
- Changed agent instructions to use new system
- Skipped source project analysis

### Issues
- Breaks compatibility with source project
- No reference to implementation plan
- Changes core behavior without justification
```

## Integration with Existing Rules

This rule works in conjunction with:
- **Write Permission Rule**: Applies after write permission is granted
- **Meta File Organization Rule**: Organizes implementation documentation
- **Context7 Rule**: Uses for library documentation when needed

## Priority and Enforcement

**Priority**: **CRITICAL** - This rule takes precedence over other implementation preferences

**Enforcement**: Apply this rule to ALL work in the `agentic-trading-system` project

**Scope**: 
- All file creation and modification in `agentic-trading-system/`
- All implementation planning and design decisions
- All testing and validation activities
- All documentation updates

## Success Metrics

### Phase Completion
- All tasks in current phase completed before moving to next phase
- Implementation plan status accurately reflects current state
- Dependencies properly managed and validated

### Source Compatibility
- Replicated functionality behaves identically to source project
- Core agent behavior unchanged from source patterns
- MCP server integration matches source exactly

### Enhancement Quality
- New features integrate seamlessly with core functionality
- Hybrid architecture maintained (Python agents + Java backend + React frontend)
- Documentation clearly distinguishes replicated vs. enhanced components

This rule ensures the `agentic-trading-system` project maintains the proven autonomous trading capabilities from the source project while systematically adding enterprise-grade enhancements according to the structured implementation plan.