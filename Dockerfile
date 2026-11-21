# Stage 1: Build React + Vite Frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json ./
RUN npm install --no-audit

COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python Backend Runtime
FROM python:3.13-slim

ENV PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1 \
    ANUMAAN_LLM_PROVIDER=none \
    ANUMAAN_VAR_DIR=/app/var

WORKDIR /app

COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

COPY . .
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.server.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
