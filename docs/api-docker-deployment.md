# API Docker Deployment Guide

Complete guide for deploying the Quantronaute Manual Trading API using Docker.

## Quick Start

```bash
# 1. Generate API user password hash
python scripts/generate_api_password.py

# 2. Create .env.api file
cp .env.api.example .env.api

# 3. Edit .env.api and add your credentials
# API_USER_ADMIN=$2b$12$your_generated_hash_here
# API_SECRET_KEY=your_secret_key_here

# 4. Build and start the API
docker-compose -f docker-compose.api.yml --env-file .env.api up -d

# 5. Check API status
curl http://localhost:8080/health
```

## Prerequisites

- Docker 20.10+
- Docker Compose 1.29+
- Python 3.13 (for generating password hashes)

## Step-by-Step Setup

### 1. Generate Secure Credentials

#### Generate JWT Secret Key

```bash
# Linux/Mac
openssl rand -hex 32

# Windows (PowerShell)
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))

# Python (any platform)
python -c "import secrets; print(secrets.token_hex(32))"
```

#### Generate User Password Hash

```bash
python scripts/generate_api_password.py
```

Example output:
```
=== API Password Hash Generator ===

Enter username: admin
Enter password:
Confirm password:

=== Generated Hash ===
Username: admin
Hash: $2b$12$KIXl.V8H9V7J8n2Z3Q3X4eU8Y5.6M7N8P9Q0R1S2T3U4V5W6X7Y8Z9

=== Add to .env.api ===
  API_USER_ADMIN=$2b$12$KIXl.V8H9V7J8n2Z3Q3X4eU8Y5.6M7N8P9Q0R1S2T3U4V5W6X7Y8Z9
```

### 2. Configure Environment Variables

Create `.env.api` file:

```bash
cp .env.api.example .env.api
```

Edit `.env.api`:

```bash
# JWT Secret Key (REQUIRED - generate with openssl rand -hex 32)
API_SECRET_KEY=your_64_character_hex_string_here

# Token expiration
API_ACCESS_TOKEN_EXPIRE_MINUTES=30
API_REFRESH_TOKEN_EXPIRE_DAYS=7

# API Users (add as many as needed)
API_USER_ADMIN=$2b$12$your_bcrypt_hash_here
API_USER_TRADER=$2b$12$another_bcrypt_hash_here

# Trading system connection (optional)
API_BASE_URL=http://host.docker.internal:8000/mt5
ACCOUNT_TYPE=swing
```

### 3. Build Docker Image

```bash
# Build the image
docker build -f Dockerfile.api -t quantronaute-api:latest .

# Or use docker-compose to build
docker-compose -f docker-compose.api.yml build
```

### 4. Run the API

#### Using Docker Compose (Recommended)

```bash
# Start in detached mode
docker-compose -f docker-compose.api.yml --env-file .env.api up -d

# View logs
docker-compose -f docker-compose.api.yml logs -f

# Stop the API
docker-compose -f docker-compose.api.yml down
```

#### Using Docker Run

```bash
docker run -d \
  --name quantronaute-api \
  -p 8080:8080 \
  --env-file .env.api \
  -v $(pwd)/configs:/app/configs:ro \
  -v $(pwd)/logs:/app/logs \
  quantronaute-api:latest
```

### 5. Verify Deployment

```bash
# Check container status
docker ps

# Check health
curl http://localhost:8080/health

# Check API info
curl http://localhost:8080/

# Access API documentation
# Open browser: http://localhost:8080/docs
```

## Authentication

### Login to Get Token

```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Use Token in Requests

```bash
# Store token
TOKEN="your_access_token_here"

# Make authenticated request
curl http://localhost:8080/positions \
  -H "Authorization: Bearer $TOKEN"
```

### Refresh Token

```bash
curl -X POST http://localhost:8080/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "your_refresh_token"
  }'
```

## User Management

### Add New User

1. Generate password hash:
```bash
python scripts/generate_api_password.py
```

2. Add to `.env.api`:
```bash
API_USER_NEWUSER=$2b$12$generated_hash_here
```

3. Restart API:
```bash
docker-compose -f docker-compose.api.yml restart
```

### Remove User

1. Remove line from `.env.api`
2. Restart API

### Change Password

1. Generate new hash with `generate_api_password.py`
2. Update hash in `.env.api`
3. Restart API

## Production Deployment

### Security Checklist

- [ ] Use strong JWT secret key (32+ bytes, random)
- [ ] Use strong passwords for all users
- [ ] Enable HTTPS/TLS (use reverse proxy like nginx)
- [ ] Set appropriate CORS origins (not "*")
- [ ] Use firewall to restrict access to port 8080
- [ ] Enable Docker user namespaces
- [ ] Rotate JWT secret key periodically
- [ ] Monitor authentication logs
- [ ] Set up log aggregation
- [ ] Enable rate limiting

### Recommended: Use Reverse Proxy

Example nginx configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Environment-Specific Configuration

Create different `.env` files:

- `.env.api.dev` - Development
- `.env.api.staging` - Staging
- `.env.api.prod` - Production

```bash
# Start with specific environment
docker-compose -f docker-compose.api.yml --env-file .env.api.prod up -d
```

## Monitoring

### Check Container Health

```bash
# Container status
docker ps

# Health check
docker inspect quantronaute-api | grep -A 10 Health

# Logs
docker logs quantronaute-api -f --tail 100
```

### API Metrics

```bash
# System status
curl http://localhost:8080/system/status

# Account info
curl http://localhost:8080/account \
  -H "Authorization: Bearer $TOKEN"

# Position monitoring
curl http://localhost:8080/positions \
  -H "Authorization: Bearer $TOKEN"
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs quantronaute-api

# Common issues:
# 1. Missing API_SECRET_KEY
# 2. No users configured (API_USER_* vars)
# 3. Port 8080 already in use
```

### Authentication Fails

```bash
# Verify credentials are loaded
docker exec quantronaute-api python -c "
import os
print('Users configured:')
for k, v in os.environ.items():
    if k.startswith('API_USER_'):
        print(f'  {k[9:].lower()}')
"
```

### Can't Connect to Trading System

```bash
# Check network connectivity
docker exec quantronaute-api curl http://host.docker.internal:8000/mt5/health

# If using custom network, ensure MT5 bridge is on same network
```

## Updating

### Update API Code

```bash
# Pull latest code
git pull

# Rebuild image
docker-compose -f docker-compose.api.yml build

# Restart with new image
docker-compose -f docker-compose.api.yml up -d
```

### Zero-Downtime Update

```bash
# Start new instance on different port
docker run -d \
  --name quantronaute-api-new \
  -p 8081:8080 \
  --env-file .env.api \
  quantronaute-api:latest

# Test new instance
curl http://localhost:8081/health

# Switch traffic (update load balancer)
# Then stop old instance
docker stop quantronaute-api
docker rm quantronaute-api
docker rename quantronaute-api-new quantronaute-api
```

## Backup & Recovery

### Backup Configuration

```bash
# Backup environment file (contains hashed passwords)
cp .env.api .env.api.backup.$(date +%Y%m%d)

# Backup configs
tar -czf configs-backup-$(date +%Y%m%d).tar.gz configs/
```

### Disaster Recovery

```bash
# 1. Restore .env.api file
cp .env.api.backup.20250117 .env.api

# 2. Restore configs
tar -xzf configs-backup-20250117.tar.gz

# 3. Restart API
docker-compose -f docker-compose.api.yml up -d
```

## Integration with Trading System

The API is designed to work alongside the trading system:

```yaml
# docker-compose.full.yml
version: '3.8'

services:
  # MT5 Bridge
  mt5-bridge:
    # ... your existing MT5 bridge config

  # Trading System
  trading-system:
    # ... your existing trading system config

  # Manual Trading API
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8080:8080"
    environment:
      - API_BASE_URL=http://mt5-bridge:8000/mt5
    depends_on:
      - mt5-bridge
    networks:
      - trading-network
```

## See Also

- [API Documentation](./api/README.md)
- [Authentication Setup](./authentication.md)
- [Manual Trading Configuration](./manual-trading-config.md)
- [Automation Control](./automation-control.md)
