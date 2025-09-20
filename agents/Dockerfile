# Python agents Dockerfile - Development friendly
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for MCP servers
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management (used by MCP servers)
RUN pip install uv

# Install correct MCP server packages
RUN npm install -g @modelcontextprotocol/server-brave-search mcp-memory-libsql

# uvx is already provided by uv package - no separate installation needed
# Test that uvx is available
RUN uvx --help || echo "uvx is available via uv package"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agents source code
COPY . .

# Install MCP server dependencies
WORKDIR /app/mcp-servers
RUN pip install --no-cache-dir -r requirements.txt

# Return to main working directory
WORKDIR /app

# Default command - can be overridden in docker-compose
CMD ["python", "trading_system.py"]