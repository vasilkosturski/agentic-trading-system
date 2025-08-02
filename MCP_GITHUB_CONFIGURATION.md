# GitHub MCP Server Configuration for Read Operations

## Overview

This document provides the configuration setup for adding GitHub MCP server with read-only operations to the existing MCP infrastructure.

## Current MCP Setup Analysis

Based on the analysis of the current project structure:

- **MCP Configuration Pattern**: The project uses parameter-based configuration as seen in [`mcp_params.py`](agents/6_mcp/mcp_params.py)
- **Server Definition**: MCP servers are defined with `command`, `args`, and `env` parameters
- **Environment Variables**: Authentication is handled through environment variables
- **GitHub MCP Server**: Already available in the system as shown in the connected servers list

## GitHub MCP Server Configuration

### 1. MCP Settings File (`mcp_settings.json`)

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "-e",
        "GITHUB_READ_ONLY=true",
        "ghcr.io/github/github-mcp-server"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}",
        "GITHUB_READ_ONLY": "true",
        "GITHUB_TOOLSETS": "read_only"
      }
    }
  }
}
```

### 2. Python Configuration Integration

Add to [`mcp_params.py`](agents/6_mcp/mcp_params.py):

```python
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# GitHub MCP Server Configuration for Read Operations
github_mcp_params = {
    "command": "docker",
    "args": [
        "run", "-i", "--rm",
        "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
        "-e", "GITHUB_READ_ONLY=true",
        "ghcr.io/github/github-mcp-server"
    ],
    "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        "GITHUB_READ_ONLY": "true",
        "GITHUB_TOOLSETS": "read_only"
    }
}

# Extended researcher MCP server params with GitHub
def researcher_mcp_server_params_with_github(name: str):
    base_params = researcher_mcp_server_params(name)
    return base_params + [github_mcp_params]
```

### 3. Environment Variables Setup

Create or update `.env` file:

```bash
# GitHub MCP Server Configuration
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
GITHUB_READ_ONLY=true
GITHUB_TOOLSETS=read_only
```

### 4. Alternative Stdio Configuration

For direct stdio communication (without Docker):

```python
github_mcp_stdio = {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        "GITHUB_READ_ONLY": "true"
    }
}
```

## Read-Only Operations Configuration

### Supported Read Operations

The GitHub MCP server with read-only configuration supports:

1. **Repository Operations**:
   - List repositories
   - Get repository information
   - Read file contents
   - Browse directory structure
   - Get commit history

2. **Issue Operations**:
   - List issues
   - Get issue details
   - Read issue comments
   - Search issues

3. **Pull Request Operations**:
   - List pull requests
   - Get pull request details
   - Read pull request comments
   - Get pull request files
   - Get pull request reviews

4. **Search Operations**:
   - Search repositories
   - Search code
   - Search issues and pull requests
   - Search users

### Restricted Operations

With read-only configuration, the following operations are disabled:
- Creating/updating/deleting repositories
- Creating/updating/deleting issues
- Creating/updating/deleting pull requests
- Pushing code changes
- Managing repository settings

## Implementation Steps

### Step 1: Environment Setup
1. Obtain GitHub Personal Access Token with read permissions
2. Set environment variables in `.env` file
3. Ensure Docker is available (for Docker-based setup)

### Step 2: Configuration Integration
1. Create `mcp_settings.json` in project root
2. Update [`mcp_params.py`](agents/6_mcp/mcp_params.py) with GitHub configuration
3. Test the configuration with a simple MCP client

### Step 3: Usage Integration
Update existing code to use GitHub MCP server:

```python
from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio

async def create_github_agent():
    github_params = github_mcp_params
    
    async with MCPServerStdio(params=github_params, client_session_timeout_seconds=60) as github_server:
        agent = Agent(
            name="github_reader",
            instructions="You can read GitHub repositories, issues, and pull requests.",
            model="gpt-4o-mini",
            mcp_servers=[github_server]
        )
        
        return agent
```

## Security Considerations

1. **Token Permissions**: Use minimal required permissions for the GitHub token
2. **Environment Variables**: Store sensitive tokens in environment variables, not in code
3. **Read-Only Mode**: Explicitly configure read-only mode to prevent accidental modifications
4. **Token Rotation**: Regularly rotate GitHub Personal Access Tokens

## Testing the Configuration

### Basic Test Script

```python
import asyncio
from agents.mcp import MCPServerStdio

async def test_github_mcp():
    params = github_mcp_params
    
    async with MCPServerStdio(params=params, client_session_timeout_seconds=60) as server:
        tools = await server.list_tools()
        print("Available GitHub tools:", [tool.name for tool in tools])
        
        # Test a read operation
        result = await server.call_tool("list_repositories", {"owner": "github"})
        print("Test result:", result)

if __name__ == "__main__":
    asyncio.run(test_github_mcp())
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify GitHub token is valid and has required permissions
   - Check environment variable is properly set

2. **Docker Issues**:
   - Ensure Docker is running
   - Verify Docker image is accessible
   - Check network connectivity

3. **MCP Connection Issues**:
   - Increase timeout values if needed
   - Check server logs for detailed error messages
   - Verify MCP server version compatibility

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration with Existing Workflows

### For Researchers
Add GitHub MCP server to researcher workflows:

```python
def researcher_with_github_mcp_server_params(name: str):
    return [
        {"command": "uvx", "args": ["mcp-server-fetch"]},
        {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": brave_env,
        },
        {
            "command": "npx",
            "args": ["-y", "mcp-memory-libsql"],
            "env": {"LIBSQL_URL": f"file:./memory/{name}.db"},
        },
        github_mcp_params  # Add GitHub MCP server
    ]
```

### For Traders
If needed for trading workflows, add to trader configurations:

```python
trader_with_github_mcp_server_params = [
    {"command": "uv", "args": ["run", "accounts_server.py"]},
    {"command": "uv", "args": ["run", "push_server.py"]},
    market_mcp,
    github_mcp_params  # Add GitHub MCP server for reading market-related repositories
]
```

## Documentation and Examples

### Example Usage Scenarios

1. **Repository Analysis**:
   ```python
   # Analyze a repository structure
   result = await agent.run("Analyze the structure of the microsoft/vscode repository")
   ```

2. **Issue Research**:
   ```python
   # Research issues in a project
   result = await agent.run("Find recent issues related to performance in the react repository")
   ```

3. **Code Search**:
   ```python
   # Search for code patterns
   result = await agent.run("Search for examples of async/await usage in TypeScript repositories")
   ```

## Maintenance and Updates

### Regular Tasks
1. Monitor GitHub API rate limits
2. Update GitHub Personal Access Token before expiration
3. Review and update read permissions as needed
4. Update MCP server version when new releases are available

### Version Compatibility
- Ensure GitHub MCP server version is compatible with the MCP protocol version used in the project
- Test configuration after any major updates to the MCP infrastructure

## Conclusion

This configuration provides a secure, read-only integration with GitHub through the MCP protocol, enabling agents to access GitHub data while maintaining security boundaries. The configuration is designed to integrate seamlessly with the existing MCP infrastructure in the project.