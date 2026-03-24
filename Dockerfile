# Stage 1: Build frontend static export
FROM node:20-slim AS frontend-builder

WORKDIR /app/ui
COPY ui/package*.json ./
RUN npm ci
COPY ui/ ./

ENV NEXT_PUBLIC_API_URL=
ENV NEXT_BUILD_MODE=export
RUN npm run build

# Stage 2: Build Python dependencies
FROM python:3.12-slim AS backend-builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    pkg-config \
    cmake \
    libcairo2-dev \
    libpango1.0-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Runtime image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=backend-builder /opt/venv /opt/venv

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copy backend code
COPY --chown=appuser:appuser . .

# Copy frontend static export
COPY --from=frontend-builder --chown=appuser:appuser /app/ui/out /app/static

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD sh -c "python -m ix.db.init_db && uvicorn ix.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-keep-alive 120 --limit-concurrency 200"
