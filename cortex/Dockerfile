FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libmagic-dev \
    poppler-utils \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml README.md ./

# Configure Poetry to not create virtual env (we're in container)
RUN poetry config virtualenvs.create false

# Copy application code
COPY app/ ./app/
COPY workers/ ./workers/

# Install dependencies (without dev dependencies for production)
RUN poetry install --without dev --no-interaction --no-ansi

# Create storage directories
RUN mkdir -p /app/storage/lancedb /app/storage/graphrag

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
