# --- STAGE 1: The Builder ---
FROM python:3.12-slim AS builder

# 1. Install uv binary directly (no pip needed)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 2. Optimization settings for uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# 3. Copy only the "instructions" first
COPY pyproject.toml uv.lock ./

# 4. Create the virtualenv and install ONLY what's needed for production
# This uses the CPU-only index we set in pyproject.toml
RUN uv sync --frozen --no-dev --no-cache

# --- STAGE 2: The Final Runtime ---
FROM python:3.12-slim

WORKDIR /app

# 5. Copy ONLY the finished virtual environment from the builder
# This leaves behind the uv cache, uv tool, and build artifacts
COPY --from=builder /app/.venv /app/.venv

# 6. Copy your source code
COPY . .

# 7. Make sure the app uses the virtualenv we copied
ENV PATH="/app/.venv/bin:$PATH"

# 8. Start the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]