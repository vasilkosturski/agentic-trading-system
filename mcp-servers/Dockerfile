# MCP servers Dockerfile - Development friendly
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Default command - run all MCP servers
CMD ["python", "-m", "accounts_server"]