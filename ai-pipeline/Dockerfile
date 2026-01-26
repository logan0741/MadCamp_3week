# MemeForty AI Pipeline Dockerfile
# Multi-stage build for optimized image size

# ===========================================
# Stage 1: Base with CUDA
# ===========================================
FROM nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04 AS base

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Create app directory
WORKDIR /app

# ===========================================
# Stage 2: Dependencies
# ===========================================
FROM base AS dependencies

# Install pip and upgrade
RUN python3 -m pip install --upgrade pip setuptools wheel

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional database drivers
RUN pip install --no-cache-dir \
    psycopg2-binary \
    asyncpg \
    sqlalchemy[asyncio]

# ===========================================
# Stage 3: Production
# ===========================================
FROM dependencies AS production

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /data/outputs /data/uploads /data/images /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Data directories
ENV OUTPUT_DIR=/data/outputs
ENV UPLOAD_DIR=/data/uploads

# Expose API port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Default command: start the API server
CMD ["python3", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
