FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for psycopg/bcrypt builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/health" || exit 1

# Bind to the platform-provided $PORT when present (Render, Cloud Run, etc.),
# falling back to 8000 for local Docker runs. Shell form enables env expansion.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
