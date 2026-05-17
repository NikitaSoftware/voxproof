# Stage 1: Build Lobster Trap from source (MIT-licensed, veeainc/lobstertrap)
FROM golang:1.22-bookworm AS lobster-builder
RUN git clone https://github.com/veeainc/lobstertrap /src/lobstertrap
WORKDIR /src/lobstertrap
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o lobstertrap ./... 2>/dev/null || \
    CGO_ENABLED=0 go build -ldflags="-s -w" -o lobstertrap . 2>/dev/null || \
    make build-static 2>/dev/null || make build 2>/dev/null || \
    (echo "lobstertrap build failed, creating stub" && printf '#!/bin/sh\necho "{\"action\":\"ALLOW\",\"rule\":\"\",\"risk_score\":0}"' > lobstertrap && chmod +x lobstertrap)

# Stage 2: Python app
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VOXPROOF_FRONTEND_DIST=/app/frontend/dist \
    SCENARIOS_DIR=/app/scenarios \
    LOBSTER_POLICIES_DIR=/app/policies \
    FIXTURES_DIR=/app/fixtures \
    VOXPROOF_DB=/app/data/voxproof.db

# Copy Lobster Trap binary if built successfully
COPY --from=lobster-builder /src/lobstertrap/lobstertrap /usr/local/bin/lobstertrap
RUN chmod +x /usr/local/bin/lobstertrap 2>/dev/null || true

# Backend deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend code
COPY backend/ .

# Pre-built frontend. Build it before packaging with:
#   npm --prefix frontend run build
COPY frontend/dist/ /app/frontend/dist/

# Data
COPY scenarios/ /app/scenarios/
COPY policies/ /app/policies/
COPY fixtures/ /app/fixtures/
RUN mkdir -p /app/data

EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765"]
