FROM python:3.13-slim

# System deps for newspaper4k (lxml/libxml2), matplotlib, Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libxml2-dev libxslt-dev \
    libjpeg-dev zlib1g-dev fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifest first (layer cache — only rebuilds when pyproject.toml changes)
COPY pyproject.toml .

# Install all deps into the system Python
RUN uv pip install --system --no-cache .

# Copy application code
COPY . .

ENV PORT=8080
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
