FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
    fastapi==0.135.3 \
    uvicorn[standard]==0.43.0 \
    sentence-transformers==5.3.0 \
    python-json-logger==3.2.1 \
    torch==2.11.0 --extra-index-url https://download.pytorch.org/whl/cpu

COPY app.py /app/app.py
COPY logging_config.py /app/logging_config.py

ENV PORT=8001
ENV PYTHONUNBUFFERED=1

EXPOSE 8001

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
