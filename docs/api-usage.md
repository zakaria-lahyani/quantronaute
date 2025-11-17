# Manual Trading API - Usage Guide

## Overview

The Manual Trading API provides a REST interface for monitoring and controlling your trading system. It enables real-time access to account data, positions, indicators, strategies, and allows manual trade execution through a secure, authenticated API.

**Key Features:**
- 🔐 JWT-based authentication
- 📊 Real-time account monitoring
- 📈 Live indicator data streaming
- 💼 Position tracking and management
- 🎯 Strategy monitoring and metrics
- ✋ Manual trade signal triggering
- 🤖 Automation control (enable/disable)

---

## Quick Start

### 1. Authentication

All endpoints (except login) require JWT authentication via Bearer token.

**Login:**
```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Using the token:**
```bash
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."
curl http://localhost:8080/account/summary \
  -H "Authorization: Bearer $TOKEN"
```

### 2. Integration Setup

For full functionality, integrate the API with your trading system:

```python
from app.api.service import APIService

# Pass MT5Client and Orchestrator to enable all endpoints
api_service = APIService(
    event_bus=event_bus,
    mt5_client=mt5_client,      # Enables account & position endpoints
    orchestrator=orchestrator,   # Enables indicator & strategy endpoints
    logger=logger
)
await api_service.start()
```

**See [api-integration.md](api-integration.md) for detailed integration instructions.**

---

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Login and receive JWT token |
| POST | `/auth/refresh` | Refresh expired token |

### Account Monitoring

| Method | Endpoint | Description | Requires |
|--------|----------|-------------|----------|
| GET | `/account/summary` | Account summary (balance, equity, margin, profit) | MT5Client |
| GET | `/account/balance` | Current account balance | MT5Client |
| GET | `/account/equity` | Current account equity | MT5Client |
| GET | `/account/margin` | Margin information | MT5Client |

**Example:**
```bash
curl http://localhost:8080/account/summary -H "Authorization: Bearer $TOKEN" | jq
```

```json
{
  "balance": 10000.50,
  "equity": 10250.75,
  "margin": 500.00,
  "margin_free": 9750.75,
  "margin_level": 2050.15,
  "profit": 250.25,
  "currency": "USD",
  "leverage": 100
}
```

### Position Management

| Method | Endpoint | Description | Requires |
|--------|----------|-------------|----------|
| GET | `/positions` | List all open positions | MT5Client |
| GET | `/positions/{symbol}` | List positions for specific symbol | MT5Client |
| GET | `/positions/ticket/{ticket}` | Get specific position by ticket | MT5Client |

**Example:**
```bash
curl http://localhost:8080/positions -H "Authorization: Bearer $TOKEN" | jq
```

```json
{
  "positions": [
    {
      "ticket": 123456,
      "symbol": "XAUUSD",
      "type": 0,
      "volume": 0.1,
      "price_open": 2650.25,
      "price_current": 2655.80,
      "profit": 55.50,
      "swap": -2.50,
      "commission": -5.00,
      "sl": 2640.00,
      "tp": 2670.00,
      "time": "2025-11-17T08:30:00Z",
      "magic": 12345,
      "comment": "manual"
    }
  ],
  "total_positions": 1,
  "total_profit": 55.50
}
```

### Indicator Monitoring

| Method | Endpoint | Description | Requires |
|--------|----------|-------------|----------|
| GET | `/indicators/{symbol}` | All indicators for symbol (all timeframes) | Orchestrator |
| GET | `/indicators/{symbol}/{timeframe}` | Indicators for specific timeframe | Orchestrator |
| GET | `/indicators/{symbol}/{timeframe}/{indicator}` | Specific indicator value | Orchestrator |

**Example:**
```bash
curl http://localhost:8080/indicators/XAUUSD/H1 -H "Authorization: Bearer $TOKEN" | jq
```

```json
{
  "symbol": "XAUUSD",
  "timeframe": "H1",
  "timestamp": "2025-11-17T10:30:00Z",
  "indicators": {
    "close": 2650.25,
    "sma_50": 2645.00,
    "ema_21": 2647.80,
    "rsi_14": 62.1,
    "atr_14": 3.50,
    "bb_upper": 2660.00,
    "bb_lower": 2640.00
  }
}
```

### Strategy Monitoring

| Method | Endpoint | Description | Requires |
|--------|----------|-------------|----------|
| GET | `/strategies/{symbol}` | List available strategies for symbol | Orchestrator |
| GET | `/strategies/{symbol}/{name}` | Get strategy configuration | Orchestrator |
| GET | `/strategies/{symbol}/metrics` | Get strategy evaluation metrics | Orchestrator |

**Example - List strategies:**
```bash
curl http://localhost:8080/strategies/XAUUSD -H "Authorization: Bearer $TOKEN" | jq
```

```json
{
  "symbol": "XAUUSD",
  "strategies": ["manual", "breakout", "trend_follow"],
  "total_strategies": 3
}
```

**Example - Strategy metrics:**
```bash
curl http://localhost:8080/strategies/XAUUSD/metrics -H "Authorization: Bearer $TOKEN" | jq
```

```json
{
  "symbol": "XAUUSD",
  "metrics": {
    "strategies_evaluated": 1250,
    "entry_signals_generated": 15,
    "exit_signals_generated": 12,
    "evaluation_errors": 0,
    "entry_signals_suppressed": 3,
    "automation_enabled": true
  }
}
```

### Manual Trading

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/signals/entry` | Trigger manual entry signal |
| POST | `/signals/exit` | Trigger manual exit signal |

**Example - Entry signal:**
```bash
curl -X POST http://localhost:8080/signals/entry \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "XAUUSD",
    "direction": "long",
    "entry_price": 2650.25
  }' | jq
```

```json
{
  "status": "success",
  "message": "Manual entry signal triggered",
  "symbol": "XAUUSD",
  "direction": "long",
  "strategy_name": "manual",
  "timestamp": "2025-11-17T10:30:00Z"
}
```

**Example - Exit signal:**
```bash
curl -X POST http://localhost:8080/signals/exit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "XAUUSD",
    "direction": "long",
    "reason": "manual_close"
  }' | jq
```

### Automation Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/automation/enable` | Enable automated trading |
| POST | `/automation/disable` | Disable automated trading |
| GET | `/automation/status` | Get current automation status |

**Example:**
```bash
curl -X POST http://localhost:8080/automation/disable \
  -H "Authorization: Bearer $TOKEN" | jq
```

```json
{
  "status": "success",
  "message": "Automation disabled",
  "automation_enabled": false,
  "timestamp": "2025-11-17T10:30:00Z"
}
```

### System Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/system/status` | System status and uptime |
| GET | `/system/metrics` | EventBus metrics |

**Example:**
```bash
curl http://localhost:8080/system/status -H "Authorization: Bearer $TOKEN" | jq
```

```json
{
  "running": true,
  "uptime_seconds": 3600.5,
  "startup_time": "2025-11-17T09:00:00Z",
  "event_bus_metrics": {
    "events_published": 1250,
    "events_delivered": 1248,
    "handler_errors": 0,
    "subscription_count": 15
  }
}
```

---

## Operating Modes

### Standalone Mode (Limited)
API runs independently without MT5Client or Orchestrator connection.

**Available:**
- ✅ Authentication
- ✅ Manual trading signals
- ✅ Automation control
- ✅ System monitoring

**Not Available:**
- ❌ Account monitoring
- ❌ Position tracking
- ❌ Indicator data
- ❌ Strategy monitoring

### Integrated Mode (Full)
API connected to trading system with MT5Client and Orchestrator.

**All endpoints fully functional** when properly integrated.

---

## Error Responses

All endpoints return consistent error responses when services are unavailable:

**MT5Client not connected:**
```json
{
  "error": "Account data not available",
  "reason": "MT5Client not connected to API service"
}
```

**Orchestrator not connected:**
```json
{
  "error": "Indicator data not available",
  "reason": "Orchestrator not connected or symbol not configured",
  "symbol": "XAUUSD"
}
```

**Resource not found:**
```json
{
  "error": "Position not found",
  "ticket": 12345
}
```

**Authentication error:**
```json
{
  "detail": "Could not validate credentials"
}
```

---

## Best Practices

### Security
- 🔒 **Never commit credentials** - Use environment variables for passwords
- 🔑 **Rotate tokens regularly** - Tokens expire after 1 hour by default
- 🌐 **Use HTTPS in production** - Never send tokens over unencrypted connections
- 🚫 **Restrict API access** - Use firewall rules to limit API access

### Performance
- ⚡ **Cache responses** - Indicator and account data can be cached for 5-10 seconds
- 📊 **Use specific endpoints** - Request only the data you need
- 🔄 **Implement retry logic** - Handle temporary network errors gracefully
- ⏱️ **Set appropriate timeouts** - Don't wait indefinitely for responses

### Integration
- 🔗 **Verify integration** - Test all endpoints after connecting MT5Client and Orchestrator
- 📝 **Monitor logs** - Check APIService logs for warnings and errors
- 🧪 **Test in development** - Verify functionality before production deployment
- 📈 **Monitor metrics** - Use `/system/metrics` to track API health

---

## Common Use Cases

### Building a Trading Dashboard
```python
import requests

class TradingDashboard:
    def __init__(self, api_url, token):
        self.api_url = api_url
        self.headers = {"Authorization": f"Bearer {token}"}

    def get_overview(self, symbol):
        """Get complete trading overview for a symbol."""
        account = requests.get(
            f"{self.api_url}/account/summary",
            headers=self.headers
        ).json()

        positions = requests.get(
            f"{self.api_url}/positions/{symbol}",
            headers=self.headers
        ).json()

        indicators = requests.get(
            f"{self.api_url}/indicators/{symbol}/H1",
            headers=self.headers
        ).json()

        strategies = requests.get(
            f"{self.api_url}/strategies/{symbol}/metrics",
            headers=self.headers
        ).json()

        return {
            "account": account,
            "positions": positions,
            "indicators": indicators,
            "strategies": strategies
        }

# Usage
dashboard = TradingDashboard("http://localhost:8080", token)
overview = dashboard.get_overview("XAUUSD")
```

### Emergency Stop (Disable Automation)
```bash
#!/bin/bash
# Quick script to disable automation in emergency

TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"'$API_PASSWORD'"}' \
  | jq -r '.access_token')

curl -X POST http://localhost:8080/automation/disable \
  -H "Authorization: Bearer $TOKEN"

echo "Automation disabled!"
```

### Monitor Specific Indicator
```bash
# Watch RSI for XAUUSD H1 every 30 seconds
while true; do
  curl -s http://localhost:8080/indicators/XAUUSD/H1/rsi_14 \
    -H "Authorization: Bearer $TOKEN" \
    | jq '.value'
  sleep 30
done
```

---

## Troubleshooting

### Issue: "Account data not available"
**Cause:** MT5Client not passed to APIService

**Solution:**
```python
api_service = APIService(
    event_bus=event_bus,
    mt5_client=mt5_client,  # Make sure this is set
    logger=logger
)
```

### Issue: "Indicator data not available"
**Cause:** Orchestrator not passed to APIService or symbol not configured

**Solution:**
```python
# Ensure orchestrator is passed
api_service = APIService(
    event_bus=event_bus,
    orchestrator=orchestrator,  # Make sure this is set
    logger=logger
)

# Ensure symbol is added to orchestrator
orchestrator.add_symbol("XAUUSD", components={...})
```

### Issue: "Could not validate credentials"
**Cause:** Invalid or expired JWT token

**Solution:** Re-authenticate to get a new token
```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'
```

---

## API Reference

**Base URL:** `http://localhost:8080` (development)

**Authentication:** Bearer token in `Authorization` header

**Content-Type:** `application/json`

**Rate Limits:** None (add as needed)

**API Version:** 1.0

---

## Related Documentation

- **[Integration Guide](./api-integration.md)** - How to integrate API with trading system
- **[Account Types](./account-types.md)** - Daily vs Swing account configuration

---

**Last Updated:** 2025-11-17
**Version:** 1.0.0
**Status:** Production Ready
