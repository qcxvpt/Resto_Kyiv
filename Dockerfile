# ── Stage 1: Build & test ────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install dependencies first (Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir pytest pytest-cov

# Copy source
COPY . .

# Run tests (build fails if any test fails)
RUN python -m pytest tests/ -v --tb=short

# ── Stage 2: Production image ─────────────────────────────────────────────────
FROM python:3.12-slim AS production

LABEL maintainer="RestoKyiv"
LABEL description="Restaurant guide for Kyiv — Flask web application"

WORKDIR /app

# Non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Dependencies only (no dev/test tools)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir gunicorn

# Application source
COPY --chown=appuser:appgroup . .

# Create instance directory for SQLite DB
RUN mkdir -p instance && chown appuser:appgroup instance

USER appuser

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/stats')" || exit 1

# Use Gunicorn in production; 4 workers for a small VPS
CMD ["gunicorn", "--workers=4", "--bind=0.0.0.0:5000", "--access-logfile=-", "--error-logfile=-", "app:app"]
