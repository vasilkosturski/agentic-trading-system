# Python agents Dockerfile - Development friendly
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Cache-bust the cert-injection layers based on cert content. The build script
# computes SHA256 of ~/zscaler-ca.pem and passes it as --build-arg
# EXTRA_CA_FINGERPRINT=<sha> (or "none" when no cert is present). Declaring the
# ARG IMMEDIATELY before the COPY/import steps means any change to the cert
# content invalidates the cache for those steps and they re-run.
ARG EXTRA_CA_FINGERPRINT=none

# Optionally trust extra CA
COPY extra-ca.pe[m] /tmp/

# Install system dependencies for MCP servers + optionally trust extra CA
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    curl \
    ca-certificates \
    && if [ -s /tmp/extra-ca.pem ]; then \
         cp /tmp/extra-ca.pem /usr/local/share/ca-certificates/extra-ca.crt && \
         update-ca-certificates && \
         test -L /etc/ssl/certs/extra-ca.pem && \
         echo "extra-ca successfully imported into system trust store (fingerprint=${EXTRA_CA_FINGERPRINT})" && \
         rm /tmp/extra-ca.pem; \
       elif [ "${EXTRA_CA_FINGERPRINT}" != "none" ]; then \
         echo "FATAL: EXTRA_CA_FINGERPRINT=${EXTRA_CA_FINGERPRINT} but /tmp/extra-ca.pem is non-empty/missing in build context" >&2; \
         exit 1; \
       else \
         rm -f /tmp/extra-ca.pem; \
       fi \
    && rm -rf /var/lib/apt/lists/*

# Point Python SSL to system CA bundle (includes extra CA if present)
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

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
