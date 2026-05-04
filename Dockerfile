# --- STAGE 1: Builder ---
FROM python:3.14-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Prioritize CPU index
ENV UV_INDEX_URL="https://download.pytorch.org/whl/cpu" \
    UV_EXTRA_INDEX_URL="https://pypi.org/simple" \
    UV_INDEX_STRATEGY=unsafe-best-match \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

# Sync dependencies (creates /app/.venv)
RUN uv sync --no-dev --no-cache

# --- STAGE 2: Runtime ---
FROM python:3.14-slim

# Combine all system dependencies into one layer
# Added libsm6 and libxext6 which are standard for OpenCV/Docling
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libxcb1 \
    libx11-6 \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY . .

# Set Environment Variables
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
# Ensure Python doesn't buffer logs (better for Cloud logging like Railway/Logfire)
ENV PYTHONUNBUFFERED=1

# Expose the port (informative)
EXPOSE 8080

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]