# Python agents Dockerfile - Development friendly
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for MCP servers from the Debian trixie (13) repo
# shipped by the python:3.11-slim base image. NOT pinned to exact patch versions:
# Debian removes the prior patch from the repo whenever a security update lands,
# so an exact pin (e.g. curl=8.14.1-2+deb13u3) breaks the build the moment that
# happens. Reproducibility is anchored by the base-image tag; app dependencies
# stay pinned in pyproject.toml.
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management (used by MCP servers).
# Pinned to the current stable release at the time of writing.
RUN pip install --no-cache-dir uv==0.5.11

# Install MCP server packages globally (avoids runtime npm/uvx installs that
# pollute stdout). Both packages pinned to their current stable releases.
RUN npm install -g @modelcontextprotocol/server-brave-search@0.6.2
RUN pip install --no-cache-dir mcp-server-fetch==2025.4.7

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
