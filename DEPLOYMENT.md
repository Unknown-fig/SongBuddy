# 🚀 SongBuddy Production Deployment Guide

This document provides complete instructions for deploying SongBuddy in a hardened, containerized, production environment with TLS/HTTPS, automated health checks, reverse proxy routing, and structured logging.

---

## 📋 Production Architecture Overview

```text
       Internet Traffic (Clients / Browsers / AI Agents)
                            │
                      HTTPS (Port 443)
                            ▼
     ┌─────────────────────────────────────────────────┐
     │              Nginx Reverse Proxy                │
     │  - TLSv1.2 / TLSv1.3 Termination (Let's Encrypt) │
     │  - Rate Limiting Zone (15 req/s with burst)     │
     │  - Gzip Compression for static assets           │
     │  - HTTP 206 Partial Content Range Proxy         │
     │  - Defense-in-depth Security Response Headers   │
     └──────────────────────┬──────────────────────────┘
                            │
               HTTP (Internal Docker Network)
                            ▼
     ┌─────────────────────────────────────────────────┐
     │            SongBuddy Application                │
     │  - Python 3.11-slim Container (Non-root user)   │
     │  - Advanced Multi-Tier Rate Limiter & Ban Guard │
     │  - Argon2 Password Hashing & JWT Auth           │
     │  - In-Memory Stream Buffer (0 Disk Overhead)    │
     │  - Built-in Healthcheck (/api/health)           │
     └─────────────────────────────────────────────────┘
```

---

## 🛠 Option 1: Docker Compose with Nginx (Recommended)

This is the standard, zero-downtime deployment method.

### 1. Prerequisites

- Linux Server (Ubuntu 22.04 LTS / Debian 12 / RHEL 9 recommended)
- [Docker](https://docs.docker.com/engine/install/) (v24+) & [Docker Compose](https://docs.docker.com/compose/install/) (v2.20+)
- Domain Name pointed to your server's public IP (A/AAAA records)

### 2. Clone and Configure

```bash
git clone https://github.com/<your-username>/SongBuddy.git
cd SongBuddy

# Generate a strong 32-character secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Create production .env file
cp .env.example .env
```

Edit `.env` to set production values:

```ini
ENVIRONMENT=production
SECRET_KEY="<YOUR_GENERATED_SECRET_KEY>"
HOST=0.0.0.0
PORT=8000
REQUIRE_AUTH=false
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 3. Launch Services

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Verify containers are healthy:

```bash
docker compose -f docker-compose.prod.yml ps
```

---

## 🔒 Option 2: Native Linux Host Deployment with Systemd

For bare-metal or single-VM deployments without Docker.

### 1. Install System Dependencies

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv ffmpeg curl
```

### 2. Create Service User & Virtualenv

```bash
sudo useradd -r -s /bin/false -d /opt/songbuddy songbuddy
sudo mkdir -p /opt/songbuddy /opt/songbuddy/downloads
sudo chown -R songbuddy:songbuddy /opt/songbuddy

cd /opt/songbuddy
sudo -u songbuddy python3 -m venv venv
sudo -u songbuddy /opt/songbuddy/venv/bin/pip install -r requirements.txt
```

### 3. Install Systemd Service Unit

Create `/etc/systemd/system/songbuddy.service`:

```ini
[Unit]
Description=SongBuddy Streaming Audio Service
After=network.target

[Service]
Type=simple
User=songbuddy
Group=songbuddy
WorkingDirectory=/opt/songbuddy
EnvironmentFile=/opt/songbuddy/.env
ExecStart=/opt/songbuddy/venv/bin/python server.py
Restart=always
RestartSec=5s
LimitNOFILE=65535

# Security sandbox
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now songbuddy
sudo systemctl status songbuddy
```

---

## 📜 SSL / TLS Certificate Setup with Let's Encrypt

To obtain a free, auto-renewing SSL certificate with Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Certbot automatically handles certificate generation and sets up renewal cron timers.

---

## 📊 Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Set to `production` for production mode. |
| `SECRET_KEY` | *(auto-generated)* | Cryptographic key for JWT token signing. |
| `HOST` | `127.0.0.1` | Network binding interface. Use `127.0.0.1` for local, `0.0.0.0` in containers. |
| `PORT` | `8000` | HTTP listening port. |
| `USE_SSL` | `false` | Enable built-in TLS on the Python server socket. |
| `SSL_CERT_PATH` | `server-cert.pem` | Path to public SSL certificate file. |
| `SSL_KEY_PATH` | `server-key.pem` | Path to private SSL certificate key. |
| `REQUIRE_AUTH` | `false` | When `true`, requires Bearer JWT token on all non-public API endpoints. |
| `CORS_ORIGIN` | `*` | Allowed CORS origin (e.g. `https://yourdomain.com`). |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `LOG_FORMAT` | `text` | Log format (`text` or `json` for Datadog/ELK/CloudWatch). |
| `SPOTIPY_CLIENT_ID` | `None` | Spotify Developer Client ID (optional). |
| `SPOTIPY_CLIENT_SECRET` | `None` | Spotify Developer Client Secret (optional). |
| `DOWNLOAD_DIR` | `./downloads` | Directory where offline MP3s are exported. |

---

## 🔍 Observability & Health Monitoring

SongBuddy exposes a dedicated observability endpoint at `/api/health`:

```bash
curl -f http://localhost:8000/api/health
```

Sample JSON response:

```json
{
  "status": "healthy",
  "uptime_seconds": 384.12,
  "timestamp": "2026-09-21T15:30:00.000000+00:00",
  "version": "1.0.0",
  "environment": "production",
  "cache": {
    "stream_cache_size": 18,
    "radio_cache_size": 4,
    "search_cache_size": 22,
    "lyrics_cache_size": 12
  },
  "active_locks": 0
}
```

Use this endpoint for:
- Docker `HEALTHCHECK`
- Kubernetes `livenessProbe` and `readinessProbe`
- AWS ALB / Cloudflare Health Monitors
- Prometheus Blackbox Exporter or Uptime Kuma

---

## 🧪 Testing Before Deployment

Always run the test suite prior to deploying new releases:

```bash
# Run complete test suite with coverage
pytest --cov=. --cov-report=term-missing

# Run code style and syntax checks
flake8 . --exclude=.venv,downloads
```
