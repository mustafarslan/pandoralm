FROM python:3.11-slim-bookworm

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Install dependencies via uv
# We need mcp, starlette for the web server, and uvicorn to run it
# httpx is useful for making requests if needed, but starlette is the core
RUN uv pip install --system "mcp[sse]" starlette uvicorn httpx

# Copy the bridge application
COPY main.py .

# Expose port
EXPOSE 8080

# Environment variables that should be set at runtime:
# MCP_COMMAND: The command to run (e.g. "uvx", "npx")
# MCP_ARGS: Arguments for the command (e.g. "mcp-server-git")

# Entrypoint runs the bridge
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
