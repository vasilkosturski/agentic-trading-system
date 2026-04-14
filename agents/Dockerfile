# Python agents Dockerfile - Development friendly
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Optionally trust extra CA
COPY extra-ca.pe[m] /tmp/

# Install system dependencies for MCP servers + optionally trust extra CA
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    curl \
    ca-certificates \
    && if [ -f /tmp/extra-ca.pem ]; then \
         cp /tmp/extra-ca.pem /usr/local/share/ca-certificates/extra-ca.crt && \
         update-ca-certificates && \
         rm /tmp/extra-ca.pem; \
       fi \
    && rm -rf /var/lib/apt/lists/*

# Point Python SSL to system CA bundle (includes extra CA if present)
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Install uv for Python package management (used by MCP servers)
RUN pip install uv

# Install MCP server packages globally (avoids runtime npm/uvx installs that pollute stdout)
RUN npm install -g @modelcontextprotocol/server-brave-search mcp-memory-libsql
RUN pip install mcp-server-fetch

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agents source code
COPY . .

# No longer need mcp-servers directory - using direct function tools instead
# MCP dependencies for external services (Brave Search, Memory, Fetch) are installed globally above

# Default command - can be overridden in docker-compose
CMD ["python", "trading_system.py"]