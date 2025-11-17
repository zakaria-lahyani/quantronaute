# API Testing Guide

Complete guide for setting up users, starting the Docker container, and testing all API endpoints.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Step 1: Generate API User](#step-1-generate-api-user)
3. [Step 2: Configure Environment](#step-2-configure-environment)
4. [Step 3: Build and Start Docker Container](#step-3-build-and-start-docker-container)
5. [Step 4: Test Authentication](#step-4-test-authentication)
6. [Step 5: Test All Endpoints](#step-5-test-all-endpoints)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Docker 20.10+
- Docker Compose 1.29+
- Python 3.13
- `curl` or Postman for testing
- Text editor

---

## Step 1: Generate API User

### 1.1 Run the Password Generation Script

```bash
python scripts/generate_api_password.py
```

### 1.2 Follow the Prompts

```
=== API Password Hash Generator ===

Enter username: admin
Enter password: [type your password]
Confirm password: [retype your password]
```

### 1.3 Save the Output

Example output:
```
=== Generated Hash ===
Username: admin
Hash: $2b$12$KIXl.V8H9V7J8n2Z3Q3X4eU8Y5.6M7N8P9Q0R1S2T3U4V5W6X7Y8Z9

=== Add to .env.api ===
  API_USER_ADMIN=$2b$12$KIXl.V8H9V7J8n2Z3Q3X4eU8Y5.6M7N8P9Q0R1S2T3U4V5W6X7Y8Z9
```

**IMPORTANT**: Save this information! You'll need:
- The username (e.g., `admin`)
- The password you entered (you'll use this to login)
- The hash (you'll add this to `.env.api`)

### 1.4 Generate Additional Users (Optional)

Repeat the process for additional users:

```bash
# Generate trader user
python scripts/generate_api_password.py
# Enter username: trader
# Enter password: [trader password]

# Generate viewer user
python scripts/generate_api_password.py
# Enter username: viewer
# Enter password: [viewer password]
```

---

## Step 2: Configure Environment

### 2.1 Generate JWT Secret Key

Choose one method:

**Python (Recommended):**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**PowerShell (Windows):**
```powershell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```

**OpenSSL (Linux/Mac):**
```bash
openssl rand -hex 32
```

Example output:
```
9f3b8c7d2e1a5f6b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b
```

### 2.2 Create .env.api File

Check if `.env.api` already exists:

```bash
# Windows PowerShell
Test-Path .env.api

# Linux/Mac
ls -la .env.api
```

If it doesn't exist, create it from the template:

```bash
# Copy template
cp .env.api.template .env.api
```

### 2.3 Edit .env.api

Open `.env.api` in a text editor and update the following fields:

```bash
# ============================================================================
# JWT Configuration
# ============================================================================

# Replace with your generated secret key
API_SECRET_KEY=9f3b8c7d2e1a5f6b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b

# Token expiration (adjust as needed)
API_ACCESS_TOKEN_EXPIRE_MINUTES=60
API_REFRESH_TOKEN_EXPIRE_DAYS=7

# ============================================================================
# User Authentication
# ============================================================================

# Replace with your generated hash from Step 1.3
API_USER_ADMIN=$2b$12$KIXl.V8H9V7J8n2Z3Q3X4eU8Y5.6M7N8P9Q0R1S2T3U4V5W6X7Y8Z9

# Optional: Add more users
# API_USER_TRADER=$2b$12$another_hash_here
# API_USER_VIEWER=$2b$12$yet_another_hash_here

# ============================================================================
# MT5 API Integration (Optional)
# ============================================================================

# If you have MT5 API running on host machine
API_BASE_URL=http://host.docker.internal:8000/mt5

# Account type
ACCOUNT_TYPE=swing
```

### 2.4 Verify Configuration

```bash
# Windows PowerShell
Get-Content .env.api

# Linux/Mac
cat .env.api
```

Make sure:
- `API_SECRET_KEY` is set and is NOT the default value
- At least one `API_USER_*` is configured
- No sensitive information has trailing spaces

---

## Step 3: Build and Start Docker Container

### 3.1 Build the Docker Image

```bash
docker-compose -f docker-compose.api.yml build
```

Expected output:
```
Building api
[+] Building 45.2s (16/16) FINISHED
...
Successfully tagged quantronaute-api:latest
```

### 3.2 Start the Container

```bash
docker-compose -f docker-compose.api.yml --env-file .env.api up -d
```

Expected output:
```
Creating network "quantronaute-network" with driver "bridge"
Creating quantronaute-api ... done
```

### 3.3 Verify Container is Running

```bash
docker ps
```

Expected output:
```
CONTAINER ID   IMAGE                 COMMAND            CREATED         STATUS                   PORTS                    NAMES
abc123def456   quantronaute-api      "uvicorn app..."   10 seconds ago  Up 9 seconds (healthy)   0.0.0.0:8080->8080/tcp   quantronaute-api
```

### 3.4 Check Container Logs

```bash
docker-compose -f docker-compose.api.yml logs -f
```

Expected output:
```
quantronaute-api | INFO:     Started server process [1]
quantronaute-api | INFO:     Waiting for application startup.
quantronaute-api | INFO:     Application startup complete.
quantronaute-api | INFO:     Uvicorn running on http://0.0.0.0:8080
```

Press `Ctrl+C` to exit log viewing.

### 3.5 Test Health Endpoint

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "api_service_running": true
}
```

### 3.6 Access API Documentation

Open your browser and navigate to:

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

---

## Step 4: Test Authentication

### 4.1 Login Request

Use the username and password from Step 1:

```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password_here"
  }'
```

**Windows PowerShell:**
```powershell
$body = @{
    username = "admin"
    password = "your_password_here"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8080/auth/login -Method Post -Body $body -ContentType "application/json"
```

### 4.2 Expected Response

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 4.3 Save Your Token

**Linux/Mac:**
```bash
export TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."
```

**Windows PowerShell:**
```powershell
$TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGc..."
```

**Windows CMD:**
```cmd
set TOKEN=eyJ0eXAiOiJKV1QiLCJhbGc...
```

### 4.4 Test Token Validation

```bash
# Linux/Mac
curl http://localhost:8080/auth/me \
  -H "Authorization: Bearer $TOKEN"

# PowerShell
Invoke-RestMethod -Uri http://localhost:8080/auth/me -Headers @{ Authorization = "Bearer $TOKEN" }
```

Expected response:
```json
{
  "username": "admin",
  "exp": 1705432800
}
```

### 4.5 Test Token Refresh

```bash
# Save your refresh token
export REFRESH_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."

# Request new access token
curl -X POST http://localhost:8080/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "'"$REFRESH_TOKEN"'"
  }'
```

---

## Step 5: Test All Endpoints

### 5.1 System Endpoints (No Authentication Required)

#### Root Information
```bash
curl http://localhost:8080/
```

#### Health Check
```bash
curl http://localhost:8080/health
```

#### System Status
```bash
curl http://localhost:8080/system/status
```

#### System Metrics
```bash
curl http://localhost:8080/system/metrics
```

### 5.2 Authentication Endpoints

#### Login
```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password"
  }'
```

#### Validate Token
```bash
curl http://localhost:8080/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

#### Refresh Token
```bash
curl -X POST http://localhost:8080/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "your_refresh_token"
  }'
```

### 5.3 Automation Control Endpoints (Requires Authentication)

#### Check Automation Status
```bash
curl http://localhost:8080/automation/status \
  -H "Authorization: Bearer $TOKEN"
```

#### Enable Automation
```bash
curl -X POST http://localhost:8080/automation/enable \
  -H "Authorization: Bearer $TOKEN"
```

#### Disable Automation
```bash
curl -X POST http://localhost:8080/automation/disable \
  -H "Authorization: Bearer $TOKEN"
```

### 5.4 Manual Trading Signal Endpoints (Requires Authentication)

#### Send Entry Signal
```bash
curl -X POST http://localhost:8080/signals/entry \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "manual_strategy",
    "symbol": "EURUSD",
    "direction": "long",
    "strength": 0.8,
    "entry_price": 1.0850,
    "stop_loss": 1.0800,
    "take_profit": 1.0950,
    "risk_amount": 100.0,
    "timeframe": "H1"
  }'
```

#### Send Exit Signal
```bash
curl -X POST http://localhost:8080/signals/exit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "position_id": "position_123",
    "reason": "manual_exit",
    "partial_close_percentage": 100.0
  }'
```

### 5.5 Position Monitoring Endpoints (Requires Authentication)

#### Get All Positions
```bash
curl http://localhost:8080/positions \
  -H "Authorization: Bearer $TOKEN"
```

#### Get Single Position
```bash
curl http://localhost:8080/positions/position_123 \
  -H "Authorization: Bearer $TOKEN"
```

#### Get Position Summary
```bash
curl http://localhost:8080/positions/summary \
  -H "Authorization: Bearer $TOKEN"
```

### 5.6 Account Endpoints (Requires Authentication)

#### Get Account Info
```bash
curl http://localhost:8080/account \
  -H "Authorization: Bearer $TOKEN"
```

#### Get Account Balance
```bash
curl http://localhost:8080/account/balance \
  -H "Authorization: Bearer $TOKEN"
```

#### Get Account Equity
```bash
curl http://localhost:8080/account/equity \
  -H "Authorization: Bearer $TOKEN"
```

### 5.7 Indicator Monitoring Endpoints (Requires Authentication)

#### Get All Indicators
```bash
curl http://localhost:8080/indicators \
  -H "Authorization: Bearer $TOKEN"
```

#### Get Specific Indicator
```bash
curl http://localhost:8080/indicators/EURUSD/H1/ema \
  -H "Authorization: Bearer $TOKEN"
```

### 5.8 Strategy Monitoring Endpoints (Requires Authentication)

#### Get All Strategies
```bash
curl http://localhost:8080/strategies \
  -H "Authorization: Bearer $TOKEN"
```

#### Get Specific Strategy
```bash
curl http://localhost:8080/strategies/manual_strategy \
  -H "Authorization: Bearer $TOKEN"
```

### 5.9 Risk Management Endpoints (Requires Authentication)

#### Get Risk Status
```bash
curl http://localhost:8080/risk/status \
  -H "Authorization: Bearer $TOKEN"
```

#### Get Daily Risk
```bash
curl http://localhost:8080/risk/daily \
  -H "Authorization: Bearer $TOKEN"
```

### 5.10 Configuration Endpoints (Requires Authentication)

#### Get Current Configuration
```bash
curl http://localhost:8080/config \
  -H "Authorization: Bearer $TOKEN"
```

#### Update Configuration
```bash
curl -X PUT http://localhost:8080/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "max_positions": 5,
    "risk_per_trade": 0.02
  }'
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker logs quantronaute-api
```

**Common issues:**
1. Missing `API_SECRET_KEY`
2. No users configured (`API_USER_*` variables)
3. Port 8080 already in use
4. Invalid bcrypt hash format

**Solution:**
```bash
# Stop container
docker-compose -f docker-compose.api.yml down

# Verify .env.api configuration
cat .env.api

# Rebuild and restart
docker-compose -f docker-compose.api.yml build
docker-compose -f docker-compose.api.yml --env-file .env.api up -d
```

### Authentication Fails

**Test 1: Verify users are loaded**
```bash
docker exec quantronaute-api python -c "
import os
print('Users configured:')
for k, v in os.environ.items():
    if k.startswith('API_USER_'):
        print(f'  {k[9:].lower()}')
"
```

**Test 2: Check password hash format**
```bash
# Hash should start with $2b$ and be about 60 characters
echo $API_USER_ADMIN
```

**Test 3: Verify secret key is loaded**
```bash
docker exec quantronaute-api python -c "
import os
key = os.getenv('API_SECRET_KEY', 'NOT SET')
print(f'Secret key: {key[:10]}... (length: {len(key)})')
"
```

### Invalid Token Error

**Possible causes:**
1. Token expired (default: 60 minutes)
2. Wrong secret key (container restarted with different key)
3. Malformed token

**Solution:**
```bash
# Login again to get fresh token
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password"
  }'
```

### Can't Connect to Trading System

**Test MT5 API connection:**
```bash
docker exec quantronaute-api curl http://host.docker.internal:8000/mt5/health
```

**Common issues:**
1. MT5 API not running
2. Wrong `API_BASE_URL` in `.env.api`
3. Network connectivity issues

**Solutions:**
```bash
# Check if MT5 API is running on host
curl http://localhost:8000/mt5/health

# Update API_BASE_URL in .env.api
# Then restart container
docker-compose -f docker-compose.api.yml restart
```

### Port Already in Use

**Find process using port 8080:**

**Windows:**
```powershell
netstat -ano | findstr :8080
```

**Linux/Mac:**
```bash
lsof -i :8080
```

**Solution:**
```bash
# Option 1: Stop the process using the port
# Option 2: Change port in docker-compose.api.yml
# Change "8080:8080" to "8081:8080"
docker-compose -f docker-compose.api.yml up -d
```

### Container Keeps Restarting

**Check health status:**
```bash
docker inspect quantronaute-api | grep -A 10 Health
```

**View last 100 log lines:**
```bash
docker logs quantronaute-api --tail 100
```

**Common causes:**
1. Application crashes on startup
2. Health check fails
3. Missing dependencies

**Solution:**
```bash
# Run container in foreground to see errors
docker-compose -f docker-compose.api.yml up
```

---

## Testing Checklist

Use this checklist to verify all functionality:

- [ ] User generated successfully
- [ ] `.env.api` configured with secret key
- [ ] `.env.api` configured with at least one user
- [ ] Docker container built successfully
- [ ] Docker container started successfully
- [ ] Health endpoint responds
- [ ] API documentation accessible at `/docs`
- [ ] Login successful
- [ ] Token validation successful
- [ ] Token refresh successful
- [ ] System status endpoint works
- [ ] Automation status check works
- [ ] Automation enable/disable works
- [ ] Manual entry signal works
- [ ] Manual exit signal works
- [ ] Position endpoints work
- [ ] Account endpoints work
- [ ] Indicator endpoints work
- [ ] Strategy endpoints work
- [ ] Risk endpoints work
- [ ] Configuration endpoints work

---

## Next Steps

After successful testing:

1. **Production Deployment**: Review [API Docker Deployment Guide](./api-docker-deployment.md) for production best practices
2. **Integration**: Review [API Integration Guide](./api-integration-guide.md) to connect API to your trading system
3. **Security**: Enable HTTPS, configure CORS, and set up rate limiting
4. **Monitoring**: Set up log aggregation and alerting
5. **Backup**: Implement regular backups of `.env.api` and configuration files

---

## Quick Reference

### Environment Variables
- `API_SECRET_KEY`: JWT signing key
- `API_USER_ADMIN`: Admin user hash
- `API_BASE_URL`: MT5 API endpoint
- `ACCOUNT_TYPE`: Trading account type

### Key Commands
```bash
# Generate user
python scripts/generate_api_password.py

# Start container
docker-compose -f docker-compose.api.yml --env-file .env.api up -d

# View logs
docker-compose -f docker-compose.api.yml logs -f

# Stop container
docker-compose -f docker-compose.api.yml down

# Restart container
docker-compose -f docker-compose.api.yml restart
```

### Key URLs
- Health: http://localhost:8080/health
- API Docs: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc
- Login: http://localhost:8080/auth/login
