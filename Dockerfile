FROM python:3.11-slim

ENV PYTHONUTF8=1 PYTHONUNBUFFERED=1 ANUMAAN_LLM_PROVIDER=none
WORKDIR /app

COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

COPY . .

# Railway injects $PORT; Hugging Face Spaces expects 7860; default 8000 locally.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.server.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
