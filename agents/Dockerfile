# Python agents Dockerfile - Development friendly
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for MCP servers
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management (used by MCP servers)
RUN pip install uv

# Install MCP server packages globally (avoids runtime npm/uvx installs that pollute stdout)
RUN npm install -g @modelcontextprotocol/server-brave-search
RUN pip install mcp-server-fetch

# Copy project metadata and install dependencies from pyproject.toml
# pyproject.toml is the single source of truth (W8: requirements.txt removed).
# Copy it BEFORE the pip install so Docker can cache the dependency layer
# independently of source-code changes.
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy agents source code
COPY . .

# No longer need mcp-servers directory - using direct function tools instead
# MCP dependencies for external services (Brave Search, Fetch) are installed globally above

# Default command - can be overridden in docker-compose
CMD ["python", "trading_system.py"]
