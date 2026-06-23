FROM python:3.11-slim

WORKDIR /app

# Install system deps (for uvicorn[standard] which uses uvloop + httptools)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy only what the backend needs
COPY pyproject.toml ./
COPY deg/ ./deg/
COPY agents/ ./agents/
COPY dijizu_agent_new/ ./dijizu_agent_new/
COPY apps/__init__.py ./apps/__init__.py
COPY apps/api/ ./apps/api/
COPY data/ ./data/

# Install Python dependencies (no dev extras)
RUN pip install --no-cache-dir -e .

# Expose default port (Railway overrides via $PORT env var)
EXPOSE 8080

# Use shell form so ${PORT:-8080} expands at runtime
CMD uvicorn apps.api.gateway:app --host 0.0.0.0 --port ${PORT:-8080}
