# Multi-stage build for minimal final image
FROM python:3.13-alpine3.22 AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev

# Set working directory
WORKDIR /build

# Copy project files
COPY pyproject.toml README.md ./
COPY mcp_nixos/ ./mcp_nixos/

# Build wheel
RUN pip wheel --no-cache-dir --wheel-dir /wheels .

# Final stage
FROM python:3.13-alpine3.22

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install runtime dependencies
RUN apk add --no-cache libffi

# Create non-root user
RUN adduser -D -h /app mcp

# Set working directory
WORKDIR /app

# Copy wheels from builder
COPY --from=builder /wheels /wheels

# Install the package
RUN pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

# Switch to non-root user
USER mcp

# Run the MCP server
ENTRYPOINT ["python", "-m", "mcp_nixos.server"]