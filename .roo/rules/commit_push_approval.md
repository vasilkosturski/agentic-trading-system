# Commit and Push Approval Rule

## Rule Configuration

This rule requires explicit user approval before any git commit or push operations to prevent unintended changes from being committed to the repository.

## Scope

This rule applies to all git operations that modify the repository state:
- `git commit` (any variant)
- `git push` (any variant)
- Combined operations like `git add -A && git commit && git push`

## Implementation

```yaml
commit_push_approval:
  triggers:
    - pattern: "git.*commit"
      description: "Any git commit operation"
    - pattern: "git.*push"
      description: "Any git push operation"
    - pattern: "execute_command.*commit"
      description: "Execute command containing commit"
    - pattern: "execute_command.*push"
      description: "Execute command containing push"
  priority: critical
  auto_block: true
```

## Workflow

### Before Any Commit/Push Operation:
1. **STOP** - Do not execute the git command
2. **ASK** - Request explicit user approval using `ask_followup_question`
3. **SHOW** - Display what changes will be committed/pushed
4. **WAIT** - Wait for user confirmation before proceeding

### Required Approval Process:
```markdown
I need to commit and push changes to the repository. 

**Pending Changes:**
- [List of modified files]
- [Brief description of changes]

**Commit Message:**
[Proposed commit message]

May I proceed with committing and pushing these changes?
```

### User Response Options:
- "Yes, commit and push the changes"
- "Yes, but modify the commit message: [new message]"
- "No, don't commit these changes"
- "Show me the detailed changes first"

## Exception Handling

### Emergency Exceptions:
Only bypass this rule if:
- User explicitly states "skip approval for this session"
- Critical system recovery operations explicitly requested
- User provides blanket approval for a specific task

### Documentation Requirement:
Even with exceptions, always inform the user:
- What files are being committed
- What the commit message will be
- That the changes are being pushed to the repository

## Implementation Notes

- This rule takes **CRITICAL PRIORITY** over task completion urgency
- Apply consistently across all modes and contexts
- When in doubt, always ask for approval
- Better to ask unnecessarily than to commit without permission
- Remember that repository changes are permanent and affect the entire project

## Usage Examples

### ❌ WRONG - Direct commit without approval:
```bash
git add -A && git commit -m "Fix bugs" && git push origin main
```

### ✅ CORRECT - Request approval first:
```markdown
I need to commit the following changes:
- Fixed PostgreSQL repository issues
- Updated entity relationships
- Resolved compilation errors

Proposed commit message: "Fix PostgreSQL integration issues"

May I proceed with committing and pushing these changes?
```

## Integration with Other Rules

This rule works in conjunction with:
- Write permission rules (files must be approved for writing first)
- Meta file organization (ensures proper file placement before commit)
- Code review processes (changes should be reviewed before commit)

## Rationale

Repository commits are permanent operations that affect:
- Project history and version control
- Other developers working on the project
- Deployment and CI/CD processes
- Code review and collaboration workflows

User approval ensures:
- Intentional changes only
- Proper commit messages
- Review of what's being committed
- Control over repository state