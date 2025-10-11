# syntax=docker/dockerfile:1
# SeaRei by SeaTechOne LLC
# Enterprise AI Safety Evaluation Platform

# ---------- Builder ----------
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for building wheels (optional but helpful)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
# Build dependency wheels into /wheels
RUN pip install --upgrade pip && pip wheel -w /wheels -r requirements.txt


# ---------- Runtime ----------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Create non-root user
RUN useradd -m -u 10001 appuser

# Install prebuilt wheels, then copy app code
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY . /app

# Ensure artifact dirs exist and are writable
RUN mkdir -p /app/report /app/dist && chown -R appuser:appuser /app

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -sf http://localhost:8001/healthz || exit 1

USER appuser

# Default: REST API via uvicorn, configurable workers
CMD ["sh", "-c", "uvicorn service.api:app --host 0.0.0.0 --port ${PORT:-8001} --workers ${WORKERS:-4}"]
