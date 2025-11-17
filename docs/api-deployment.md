# Manual Trading API - Docker Deployment Guide

## Overview

This guide provides complete instructions for deploying the Manual Trading API using Docker.

**Deployment Modes:**
- **Standalone Mode**: API only (limited functionality)
- **Integrated Mode**: API + Trading System (full functionality)

---

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.10+ (for password generation)

---

## Quick Start - Standalone Deployment

### Step 1: Generate API Password

```bash
# Generate hashed password for admin user
python -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
password = 'your_secure_password_here'
hashed = pwd_context.hash(password)
print(f'API_USER_ADMIN=admin:{hashed}')
"
```

Save the output (it will look like):
```
API_USER_ADMIN=admin:$2b$12$abc123...xyz789
```

### Step 2: Create Environment File

Create `.env.api`:

```bash
# JWT Configuration
API_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
API_ACCESS_TOKEN_EXPIRE_MINUTES=60
API_REFRESH_TOKEN_EXPIRE_DAYS=7

# Admin User Credentials
# Format: username:bcrypt_hashed_password
API_USER_ADMIN=admin:$2b$12$abc123...xyz789

# MT5 API Connection (optional - for integrated mode)
API_BASE_URL=http://host.docker.internal:8000/mt5

# Account Type
ACCOUNT_TYPE=swing
```

### Step 3: Build and Start

```bash
# Build the Docker image
docker-compose -f docker-compose.api.yml build

# Start the API container
docker-compose -f docker-compose.api.yml up -d

# Check logs
docker-compose -f docker-compose.api.yml logs -f api
```

### Step 4: Verify Deployment

```bash
# Check container status
docker ps | grep quantronaute-api

# Test health endpoint
curl http://localhost:8080/health

# Test authentication
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_secure_password_here"}'
```

---

## Complete Deployment Commands

### Build Commands

```bash
# Build API image
docker-compose -f docker-compose.api.yml build

# Build with no cache (force rebuild)
docker-compose -f docker-compose.api.yml build --no-cache

# Build and start in one command
docker-compose -f docker-compose.api.yml up -d --build
```

### Start/Stop Commands

```bash
# Start API container
docker-compose -f docker-compose.api.yml up -d

# Stop API container
docker-compose -f docker-compose.api.yml down

# Stop and remove volumes
docker-compose -f docker-compose.api.yml down -v

# Restart API container
docker-compose -f docker-compose.api.yml restart api
```

### Monitoring Commands

```bash
# View logs (follow mode)
docker-compose -f docker-compose.api.yml logs -f api

# View last 100 lines of logs
docker-compose -f docker-compose.api.yml logs --tail=100 api

# Check container status
docker-compose -f docker-compose.api.yml ps

# Execute command in running container
docker-compose -f docker-compose.api.yml exec api bash

# View container resource usage
docker stats quantronaute-api
```

### Debugging Commands

```bash
# Enter container shell
docker exec -it quantronaute-api bash

# Check Python version
docker exec quantronaute-api python --version

# List installed packages
docker exec quantronaute-api pip list

# Check API process
docker exec quantronaute-api ps aux

# Test API from inside container
docker exec quantronaute-api curl http://localhost:8080/health
```

---

## Integrated Deployment (API + Trading System)

For full functionality with account, position, indicator, and strategy monitoring:

### Option 1: Single Docker Compose File

Create `docker-compose.full.yml`:

```yaml
version: '3.8'

services:
  # MT5 API Server
  mt5-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mt5-api-server
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - configs/ftmo-swing/.env.broker
    volumes:
      - ./configs:/app/configs:ro
      - ./logs:/app/logs
    networks:
      - trading-network

  # Manual Trading API
  trading-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: quantronaute-api
    restart: unless-stopped
    ports:
      - "8080:8080"
    env_file:
      - .env.api
    environment:
      - API_BASE_URL=http://mt5-api:8000/mt5
    volumes:
      - ./configs:/app/configs:ro
      - ./logs:/app/logs
    networks:
      - trading-network
    depends_on:
      - mt5-api
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  trading-network:
    name: quantronaute-network
    driver: bridge
```

Deploy both services:

```bash
# Build and start both services
docker-compose -f docker-compose.full.yml up -d --build

# Check both containers
docker-compose -f docker-compose.full.yml ps

# View logs from both
docker-compose -f docker-compose.full.yml logs -f
```

### Option 2: Separate Deployments with Shared Network

```bash
# Start MT5 API first (if not already running)
docker-compose up -d

# Start Trading API on same network
docker-compose -f docker-compose.api.yml up -d

# Verify network connectivity
docker exec quantronaute-api ping mt5-api
```

---

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `API_SECRET_KEY` | JWT signing key | Random 32+ char string |
| `API_USER_ADMIN` | Admin credentials | `admin:$2b$12$hash...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token lifetime | `30` |
| `API_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` |
| `API_BASE_URL` | MT5 API endpoint | `http://host.docker.internal:8000/mt5` |
| `ACCOUNT_TYPE` | Account type | `swing` |

---

## Production Deployment

### Security Hardening

**1. Generate Strong Secret Key:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**2. Use Docker Secrets (Docker Swarm):**

Create secrets:
```bash
echo "your-secret-key" | docker secret create api_secret_key -
echo "admin:$2b$12$hash..." | docker secret create api_admin_user -
```

Update `docker-compose.api.yml`:
```yaml
services:
  api:
    secrets:
      - api_secret_key
      - api_admin_user
    environment:
      - API_SECRET_KEY_FILE=/run/secrets/api_secret_key
      - API_USER_ADMIN_FILE=/run/secrets/api_admin_user

secrets:
  api_secret_key:
    external: true
  api_admin_user:
    external: true
```

**3. Enable HTTPS with Reverse Proxy:**

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    networks:
      - trading-network
    depends_on:
      - api
```

**4. Restrict Network Access:**

Update firewall:
```bash
# Allow only from specific IP
sudo ufw allow from 192.168.1.100 to any port 8080

# Or use nginx with IP whitelist
```

### Resource Limits

Add to `docker-compose.api.yml`:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Auto-Restart Configuration

```yaml
services:
  api:
    restart: always  # or: unless-stopped, on-failure
```

---

## Backup and Restore

### Backup Configuration

```bash
# Backup environment file
cp .env.api .env.api.backup

# Backup configs directory
tar -czf configs-backup-$(date +%Y%m%d).tar.gz configs/

# Backup logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/
```

### Restore

```bash
# Restore environment
cp .env.api.backup .env.api

# Restore configs
tar -xzf configs-backup-20251117.tar.gz

# Restart with restored config
docker-compose -f docker-compose.api.yml restart
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker-compose -f docker-compose.api.yml logs api

# Check if port is already in use
sudo lsof -i :8080

# Try running without detach to see errors
docker-compose -f docker-compose.api.yml up
```

### Authentication Issues

```bash
# Verify password hash in environment
docker exec quantronaute-api env | grep API_USER_ADMIN

# Test login with curl
curl -v -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"test"}'
```

### Cannot Connect to MT5 API

```bash
# Test connectivity from API container
docker exec quantronaute-api curl -v http://host.docker.internal:8000/mt5/health

# Check if MT5 API is running
docker ps | grep mt5

# Verify network
docker network inspect quantronaute-network
```

### High Memory Usage

```bash
# Check container stats
docker stats quantronaute-api

# Set memory limits
docker update --memory 512m --memory-swap 1g quantronaute-api

# Or add to docker-compose.yml as shown above
```

---

## Monitoring and Logging

### Prometheus Metrics (Optional)

Add to your application:

```python
# app/api/main.py
from prometheus_fastapi_instrumentator import Instrumentator

@app.on_event("startup")
async def startup():
    Instrumentator().instrument(app).expose(app)
```

Access metrics:
```bash
curl http://localhost:8080/metrics
```

### Centralized Logging

Use Docker logging driver:

```yaml
services:
  api:
    logging:
      driver: "syslog"
      options:
        syslog-address: "tcp://logserver:514"
```

Or use ELK stack, Loki, etc.

---

## Scaling

### Multiple API Instances

```bash
# Scale to 3 instances
docker-compose -f docker-compose.api.yml up -d --scale api=3

# Add load balancer (nginx)
```

### Health Checks for Load Balancing

```bash
# Check which instances are healthy
curl http://localhost:8080/health
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy API

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Build Docker image
        run: docker-compose -f docker-compose.api.yml build

      - name: Push to registry
        run: |
          docker tag quantronaute-api:latest registry.example.com/api:latest
          docker push registry.example.com/api:latest

      - name: Deploy
        run: |
          ssh user@server 'cd /app && docker-compose -f docker-compose.api.yml pull && docker-compose -f docker-compose.api.yml up -d'
```

---

## Quick Reference Commands

```bash
# One-line deploy
docker-compose -f docker-compose.api.yml up -d --build

# One-line stop and clean
docker-compose -f docker-compose.api.yml down -v

# View live logs
docker-compose -f docker-compose.api.yml logs -f api

# Restart API
docker-compose -f docker-compose.api.yml restart api

# Update and redeploy
git pull && docker-compose -f docker-compose.api.yml up -d --build

# Health check
curl http://localhost:8080/health

# Test login
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yourpass"}' | jq

# Full system test
python test_api_client.py http://localhost:8080 admin yourpass
```

---

## Related Documentation

- **[API Usage Guide](./api-usage.md)** - How to use the API
- **[API Testing Guide](./api-testing.md)** - How to test the API
- **[API Integration Guide](./api-integration.md)** - How to integrate with trading system

---

**Last Updated:** 2025-11-17
**Version:** 1.0.0
**Docker Compose:** 2.0+
