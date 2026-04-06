FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi==0.135.3 \
    uvicorn[standard]==0.43.0 \
    sentence-transformers==5.3.0 \
    torch==2.11.0 --extra-index-url https://download.pytorch.org/whl/cpu

# Copy application code
COPY app.py /app/app.py

# Set environment variables
ENV MODEL_NAME=BAAI/bge-small-en-v1.5
ENV PORT=8001
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8001

# Run the application
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
