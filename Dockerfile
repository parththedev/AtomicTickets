FROM python:3.12-slim

#Install system deps for python
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* /app/
RUN uv sync --frozen --no-dev

#Install deps
RUN uv pip install --system -r pyproject.toml

# Copy the application code
COPY . /app

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]