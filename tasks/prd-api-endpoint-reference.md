# API Endpoint Reference - Complete Documentation

**Version**: 1.0
**Last Updated**: 2025-11-17
**Base URL**: `http://localhost:8080`

This document provides complete documentation for all Quantronaute Trading API endpoints, including request/response formats and usage examples.

---

## Table of Contents

1. [Authentication Endpoints](#authentication-endpoints)
2. [Manual Trading (Signals) Endpoints](#manual-trading-signals-endpoints)
3. [Position Monitoring Endpoints](#position-monitoring-endpoints)
4. [Account Endpoints](#account-endpoints)
5. [Automation Control Endpoints](#automation-control-endpoints)
6. [Strategy Monitoring Endpoints](#strategy-monitoring-endpoints)
7. [Indicator Endpoints](#indicator-endpoints)
8. [Risk Management Endpoints](#risk-management-endpoints)
9. [Configuration Endpoints](#configuration-endpoints)
10. [System Health Endpoints](#system-health-endpoints)

---

## Authentication Endpoints

### POST `/auth/login`
**Description**: Authenticate user and receive JWT tokens

**Request**:
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGc....",
  "refresh_token": "eyJhbGc....",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

---

### POST `/auth/refresh`
**Description**: Refresh access token using refresh token

**Request**:
```json
{
  "refresh_token": "eyJhbGc...."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGc....",
  "refresh_token": "eyJhbGc....",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

### GET `/auth/me`
**Description**: Validate current token and get user info

**Authentication**: Required

**Response** (200 OK):
```json
{
  "username": "admin",
  "exp": 1705432800
}
```

---

## Manual Trading (Signals) Endpoints

### POST `/signals/entry`
**Description**: Trigger manual entry signal (open position)

**Authentication**: Required

**How It Works**:
1. API publishes `EntrySignalEvent` with strategy_name="manual"
2. System reads `manual.yaml` configuration for the symbol
3. Position sizing calculated based on risk parameters in config
4. Stop Loss (SL) and Take Profit (TP) calculated from config
5. Risk validation performed (daily limits, max positions)
6. Order executed through MT5 at market price

**Request**:
```json
{
  "symbol": "XAUUSD",
  "direction": "long"
}
```

**Fields**:
- `symbol` (string, required): Trading symbol (e.g., "XAUUSD", "EURUSD")
- `direction` (string, required): Trade direction - "long" or "short"

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Manual entry signal triggered",
  "symbol": "XAUUSD",
  "direction": "long",
  "strategy": "manual",
  "triggered_by": "admin"
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/signals/entry \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "XAUUSD", "direction": "long"}'
```

**Important Notes**:
- Position size is auto-calculated from `manual.yaml` risk parameters
- SL/TP are auto-calculated based on configuration (ATR, fixed pips, etc.)
- You CANNOT manually specify entry price, SL, or TP via API
- To customize these, edit `configs/[account]/manual.yaml` file
- Trade executes immediately at current market price

---

### POST `/signals/exit`
**Description**: Trigger manual exit signal (close position)

**Authentication**: Required

**How It Works**:
1. API publishes `ExitSignalEvent` with strategy_name="manual"
2. System finds matching open position(s) for symbol + direction
3. Position(s) closed at current market price

**Request**:
```json
{
  "symbol": "XAUUSD",
  "direction": "long",
  "reason": "manual"
}
```

**Fields**:
- `symbol` (string, required): Trading symbol
- `direction` (string, required): "long" or "short"
- `reason` (string, optional): Exit reason (e.g., "manual", "take_profit", "stop_loss")

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Manual exit signal triggered",
  "symbol": "XAUUSD",
  "direction": "long",
  "reason": "manual",
  "triggered_by": "admin"
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/signals/exit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "XAUUSD", "direction": "long", "reason": "take_profit"}'
```

---

### GET `/signals/`
**Description**: List pending orders (NOT YET IMPLEMENTED)

**Authentication**: Required

**Response**:
```json
{
  "status": "not_implemented",
  "message": "Order listing not yet implemented",
  "note": "Manual signals execute immediately at market"
}
```

---

### DELETE `/signals/{ticket}`
**Description**: Cancel pending order (NOT YET IMPLEMENTED)

**Authentication**: Required

**Response**:
```json
{
  "status": "not_implemented",
  "message": "Order cancellation not yet implemented"
}
```

---

## Position Monitoring Endpoints

### GET `/positions`
**Description**: Get all open positions

**Authentication**: Required

**Response** (200 OK):
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
  "total_profit": 48.00
}
```

**Error Response** (MT5 not available):
```json
{
  "error": "Position data not available",
  "reason": "MT5Client not connected to API service"
}
```

**Example**:
```bash
curl http://localhost:8080/positions \
  -H "Authorization: Bearer $TOKEN"
```

---

### GET `/positions/{symbol}`
**Description**: Get positions filtered by symbol

**Authentication**: Required

**Path Parameters**:
- `symbol`: Trading symbol (e.g., XAUUSD)

**Response** (200 OK):
```json
{
  "symbol": "XAUUSD",
  "positions": [...],
  "total_positions": 2,
  "total_profit": 150.25
}
```

---

### GET `/positions/ticket/{ticket}`
**Description**: Get specific position by ticket number

**Authentication**: Required

**Path Parameters**:
- `ticket`: Position ticket number

**Response** (200 OK):
```json
{
  "ticket": 123456,
  "symbol": "XAUUSD",
  "type": 0,
  "volume": 0.1,
  "price_open": 2650.25,
  "price_current": 2655.80,
  "profit": 55.50,
  ...
}
```

**Error Response** (404):
```json
{
  "error": "Position not found",
  "ticket": 12345
}
```

---

### POST `/positions/{ticket}/close`
**Description**: Close specific position (NOT YET IMPLEMENTED)

**Authentication**: Required

**Response**:
```json
{
  "status": "not_implemented",
  "message": "Position closing not yet implemented",
  "ticket": 12345
}
```

---

### POST `/positions/{ticket}/modify`
**Description**: Modify position SL/TP (NOT YET IMPLEMENTED)

**Authentication**: Required

**Future Request Body**:
```json
{
  "stop_loss": 2640.0,
  "take_profit": 2670.0
}
```

**Response**:
```json
{
  "status": "not_implemented",
  "message": "Position modification not yet implemented"
}
```

---

### POST `/positions/close-all`
**Description**: Close all open positions (NOT YET IMPLEMENTED)

**Authentication**: Required

**Response**:
```json
{
  "status": "not_implemented",
  "message": "Mass position closing not yet implemented"
}
```

---

## Account Endpoints

### GET `/account/summary`
**Description**: Get complete account summary

**Authentication**: Required

**Response** (200 OK):
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

**Error Response**:
```json
{
  "error": "Account data not available",
  "reason": "MT5Client not connected to API service"
}
```

---

### GET `/account/balance`
**Description**: Get account balance only

**Authentication**: Required

**Response** (200 OK):
```json
{
  "balance": 10000.50
}
```

---

### GET `/account/equity`
**Description**: Get account equity

**Authentication**: Required

**Response** (200 OK):
```json
{
  "equity": 10250.75
}
```

---

### GET `/account/margin`
**Description**: Get margin information

**Authentication**: Required

**Response** (200 OK):
```json
{
  "margin": 500.00,
  "margin_free": 9750.75,
  "margin_level": 2050.15
}
```

---

## Automation Control Endpoints

### GET `/automation/status`
**Description**: Check automation status

**Authentication**: Required

**Response** (200 OK):
```json
{
  "status": "queried",
  "message": "Automation status query published",
  "note": "Check AutomationStatusEvent on EventBus for actual status"
}
```

---

### POST `/automation/enable`
**Description**: Enable automated trading

**Authentication**: Required

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Automation enable request published"
}
```

---

### POST `/automation/disable`
**Description**: Disable automated trading

**Authentication**: Required

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Automation disable request published"
}
```

---

## Strategy Monitoring Endpoints

### GET `/strategies/`
**Description**: List all strategies (NOT YET IMPLEMENTED)

**Authentication**: Required

---

### GET `/strategies/{symbol}`
**Description**: List strategies for specific symbol

**Authentication**: Required

**Response** (200 OK):
```json
{
  "symbol": "XAUUSD",
  "strategies": ["manual", "breakout", "trend_follow"],
  "total_strategies": 3
}
```

---

### GET `/strategies/{symbol}/{strategy_name}`
**Description**: Get strategy configuration

**Authentication**: Required

**Response** (200 OK):
```json
{
  "symbol": "XAUUSD",
  "strategy_name": "breakout",
  "config": {
    "name": "breakout",
    "description": "Breakout strategy...",
    "risk_params": {...},
    "conditions": {...}
  }
}
```

---

### GET `/strategies/{symbol}/metrics`
**Description**: Get strategy performance metrics

**Authentication**: Required

**Response** (200 OK):
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

---

### GET `/strategies/{symbol}/{strategy_name}/conditions`
**Description**: Get real-time strategy condition evaluation (NOT YET IMPLEMENTED)

**Future Response**:
```json
{
  "symbol": "XAUUSD",
  "strategy": "breakout",
  "timestamp": "2025-11-17T10:30:00Z",
  "would_trigger": false,
  "entry_conditions": [
    {
      "condition": "close > previous_close",
      "satisfied": true,
      "actual_values": {"close": 2650.25, "previous_close": 2649.50}
    },
    {
      "condition": "rsi > 50",
      "satisfied": false,
      "actual_values": {"rsi": 45.3}
    }
  ],
  "blocking_conditions": ["rsi > 50"]
}
```

---

## Indicator Endpoints

### GET `/indicators/{symbol}`
**Description**: Get all indicators for symbol across all timeframes

**Authentication**: Required

**Response** (200 OK):
```json
{
  "symbol": "XAUUSD",
  "timestamp": "2025-11-17T10:30:00Z",
  "timeframes": {
    "M1": {
      "close": 2650.25,
      "sma_50": 2648.10,
      "ema_21": 2649.50,
      "rsi_14": 58.3,
      "atr_14": 1.25
    },
    "H1": {
      "close": 2650.25,
      "sma_50": 2645.00,
      "ema_21": 2647.80,
      "rsi_14": 62.1,
      "atr_14": 3.50
    }
  }
}
```

---

### GET `/indicators/{symbol}/{timeframe}`
**Description**: Get indicators for specific symbol and timeframe

**Authentication**: Required

**Path Parameters**:
- `symbol`: Trading symbol (e.g., XAUUSD)
- `timeframe`: Timeframe (M1, M5, M15, H1, H4, D1)

**Response** (200 OK):
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
    "atr_14": 3.50
  }
}
```

---

### GET `/indicators/{symbol}/{timeframe}/{indicator}`
**Description**: Get specific indicator value

**Authentication**: Required

**Path Parameters**:
- `symbol`: Trading symbol
- `timeframe`: Timeframe
- `indicator`: Indicator name (e.g., sma_50, ema_21, rsi_14)

**Response** (200 OK):
```json
{
  "symbol": "XAUUSD",
  "timeframe": "H1",
  "indicator": "rsi_14",
  "value": 62.1,
  "timestamp": "2025-11-17T10:30:00Z"
}
```

**Error Response** (404):
```json
{
  "error": "Indicator not found",
  "reason": "Indicator 'xyz' not available in calculated indicators",
  "symbol": "XAUUSD",
  "timeframe": "H1",
  "indicator": "xyz",
  "available_indicators": ["close", "sma_50", "ema_21", "rsi_14", "atr_14"]
}
```

---

## Risk Management Endpoints

### GET `/risk/config`
**Description**: Get risk configuration (NOT YET IMPLEMENTED)

**Authentication**: Required

---

### PUT `/risk/config`
**Description**: Update risk configuration (NOT YET IMPLEMENTED)

**Authentication**: Required

---

### GET `/risk/limits`
**Description**: Get current risk limit status (NOT YET IMPLEMENTED)

**Authentication**: Required

---

## Configuration Endpoints

### GET `/config/strategies`
**Description**: List all strategy configurations (NOT YET IMPLEMENTED)

**Authentication**: Required

---

### GET `/config/strategies/{symbol}`
**Description**: List strategies for symbol (NOT YET IMPLEMENTED)

**Authentication**: Required

---

### GET `/config/strategies/{symbol}/{strategy}`
**Description**: Get full strategy configuration (NOT YET IMPLEMENTED)

**Authentication**: Required

---

### GET `/config/strategies/{symbol}/{strategy}/risk`
**Description**: Get risk configuration section (NOT YET IMPLEMENTED)

**Authentication**: Required

---

### PUT `/config/strategies/{symbol}/{strategy}/risk`
**Description**: Update risk configuration (NOT YET IMPLEMENTED)

**Authentication**: Required

---

### GET `/config/broker`
**Description**: Get broker settings (NOT YET IMPLEMENTED)

**Authentication**: Required

---

### GET `/config/broker/symbols`
**Description**: List configured symbols (NOT YET IMPLEMENTED)

**Authentication**: Required

---

## System Health Endpoints

### GET `/`
**Description**: Get API information

**Authentication**: Not required

**Response** (200 OK):
```json
{
  "name": "Quantronaute Trading API",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs"
}
```

---

### GET `/health`
**Description**: Health check endpoint

**Authentication**: Not required

**Response** (200 OK):
```json
{
  "status": "healthy",
  "api_service_running": true
}
```

---

### GET `/system/status`
**Description**: Get system status (requires auth in current implementation)

**Authentication**: Required

**Response** (200 OK):
```json
{
  "status": "operational",
  "components": {
    "api": "running",
    "mt5_client": "connected",
    "orchestrator": "running"
  }
}
```

---

### GET `/system/metrics`
**Description**: Get detailed system metrics (requires auth in current implementation)

**Authentication**: Required

**Response** (200 OK):
```json
{
  "uptime_seconds": 3600,
  "active_positions": 3,
  "automation_enabled": true,
  "last_evaluation": "2025-11-17T10:30:00Z"
}
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not authenticated"
}
```

### 404 Not Found
```json
{
  "detail": "Not Found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "direction"],
      "msg": "Invalid direction: xyz. Must be 'long' or 'short'",
      "type": "value_error"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Common Patterns

### Authentication Header
All authenticated endpoints require:
```
Authorization: Bearer eyJhbGc...
```

### Polling Recommendations
- Positions: Poll every 10 seconds
- Account data: Poll every 15 seconds
- System status: Poll every 30 seconds
- Indicators: Poll every 15-30 seconds based on timeframe

### Position Type Values
- `0`: Buy (long)
- `1`: Sell (short)

### Magic Number
- `12345`: Manual trades
- Other values: Strategy-specific magic numbers

---

## Implementation Status Legend

- ✅ **Fully Implemented**: Endpoint works as documented
- 🚧 **Partial**: Endpoint exists but limited functionality
- ❌ **Not Implemented**: Returns "not_implemented" status

| Endpoint Category | Status |
|------------------|--------|
| Authentication | ✅ |
| Manual Entry/Exit Signals | ✅ |
| Position Monitoring (Read) | ✅ |
| Position Management (Modify/Close) | ❌ |
| Account Info | ✅ |
| Automation Control | ✅ |
| Strategy Monitoring | 🚧 |
| Indicator Access | ✅ |
| Risk Management | ❌ |
| Configuration Management | ❌ |
| System Health | ✅ |
