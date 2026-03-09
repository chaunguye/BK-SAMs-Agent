# --- STAGE 1: Builder ---
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Pprioritize the small CPU index for EVERYTHING.
# CPU repo the PRIMARY and PyPI the SECONDARY.
ENV UV_INDEX_URL="https://download.pytorch.org/whl/cpu" \
    UV_EXTRA_INDEX_URL="https://pypi.org/simple" \
    UV_INDEX_STRATEGY=unsafe-best-match \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

# CRITICAL: We do NOT use --frozen here. 
# We want uv to ignore the 'gpu' lock and create a new 'cpu' plan.
RUN uv sync --no-dev --no-cache

# --- STAGE 2: The Final Runtime (The Dining Room) ---
# We start with a fresh, tiny image. No uv, no compilers, no junk.
FROM python:3.14-slim

# 6. Install 'libgomp1'. 
# This is a C++ library required by Torch and Sentence-Transformers to 
# perform math on a CPU. Without this, your app will crash with a "shared library not found" error.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

# 7. Copy the "Good" Environment from the Builder.
# We copy the entire .venv folder which now contains the Linux-compatible, 
# CPU-only Python and libraries.
COPY --from=builder /app/.venv /app/.venv

# 8. Copy your application source code.
# Since we have a .dockerignore, this won't copy your Windows .venv.


# 9. Set Environment Variables for the Runtime.
# - VIRTUAL_ENV: Tells Python to use the libraries in our .venv folder.
# - PATH: Prioritizes our .venv/bin so 'python' refers to our local version.
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# 10. The Command to Start.
# We use the absolute path to the .venv python to be 100% safe.
# We run on 0.0.0.0 so the container can talk to the outside world (Railway).
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]