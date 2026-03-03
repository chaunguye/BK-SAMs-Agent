# 1. Use a standard Python image
FROM python:3.12-slim

# 2. Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 4. Copy the dependency files to seperate the dependency installation from the code 
COPY pyproject.toml uv.lock ./

# 5. Install dependencies 
RUN uv sync --frozen --no-cache --no-dev

# 6. Copy the code
COPY . .

# 7. Run the app
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]