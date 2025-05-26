FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY . .

# Install the package and dependencies
RUN pip install --no-cache-dir -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the MCP server
CMD ["python", "-m", "mcp_nixos"]
