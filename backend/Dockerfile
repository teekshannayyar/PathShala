# PathShala API. Build from backend/:
#   docker build -t pathshala-api backend
#   docker run --env-file backend/.env -p 8000:8000 pathshala-api
FROM python:3.11-slim

# Extra pip index for CPU-only torch wheels (much smaller than the default
# CUDA build). Pass --build-arg TORCH_INDEX_URL= to install from PyPI only.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
# Download all-MiniLM-L6-v2 into the image so the first request doesn't.
# Pass --build-arg PRELOAD_MODEL=false to skip (e.g. EMBEDDING_BACKEND=fake).
ARG PRELOAD_MODEL=true

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/hf-cache

WORKDIR /app

COPY requirements.txt .
RUN if [ -n "$TORCH_INDEX_URL" ]; then \
        pip install --no-cache-dir --extra-index-url "$TORCH_INDEX_URL" -r requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

RUN if [ "$PRELOAD_MODEL" = "true" ]; then \
        python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"; \
    fi

COPY . .

# Runs as root so it can write to a mounted volume (e.g. Render's disk at
# /var/data) whatever that volume's ownership is.
EXPOSE 8000

# Migrations run on every start (a no-op when up to date). X-Forwarded-For
# is trusted only from FORWARDED_ALLOW_IPS (default 127.0.0.1): with "*"
# uvicorn would take its left-most entry, which the client controls behind a
# proxy that appends to it. Per-IP rate limits use CLIENT_IP_HEADER instead
# when it's set (see app/core/rate_limit.py and render.yaml).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=\"${FORWARDED_ALLOW_IPS:-127.0.0.1}\""]
