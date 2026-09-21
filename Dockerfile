# ====================================================================
# SongBuddy Production Container
# ====================================================================
FROM python:3.11-slim

LABEL maintainer="SongBuddy Contributors"
LABEL description="Ad-free in-memory audio streaming client and MCP server"

# 1. Install system runtime dependencies: FFmpeg, curl, ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 2. Create non-root security service account
RUN groupadd -g 10001 songbuddy && \
    useradd -u 10001 -g songbuddy -s /bin/bash -m songbuddy

WORKDIR /app

# 3. Cache Python dependency layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy application source code
COPY . .

# 5. Create downloads and storage directory with proper permissions
RUN mkdir -p /app/downloads && chown -R songbuddy:songbuddy /app

# 6. Set runtime environment
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    ENVIRONMENT=production \
    DOWNLOAD_DIR=/app/downloads

EXPOSE 8000

# 7. Native Container Health Check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 8. Run as non-root user
USER songbuddy

CMD ["python", "server.py"]
