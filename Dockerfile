# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

# ---- Environment ----
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# ---- System deps (Debian-based; no musl-dev) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      python3-dev \
      libpq-dev \
      curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Poetry ----
# (Pin if you want: pip install "poetry==1.8.3")
RUN pip install --no-cache-dir poetry

# ---- Only deps first (cache-friendly) ----
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-interaction --no-ansi

# ---- Copy the rest of the source ----
COPY . .

# ---- Copy example env to actual env ----
RUN cp -n .env.example .env

# ---- Non-root user (safer) ----
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Optional but nice for clarity with compose exposing 8000
EXPOSE 8000

# No CMD here — docker-compose will run:
#   poetry run python -m alembic upgrade head && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
