# PRD: Manual Trading API (Phase 2)

## Document Information
- **Feature Name**: Manual Trading API
- **Version**: 1.0
- **Created**: 2025-11-17
- **Author**: Product Requirements Document
- **Target Audience**: Junior Developers
- **Depends On**: Phase 1 - Automated Trading Toggle (prd-automated-trading-toggle.md)

---

## 1. Introduction / Overview

### What We're Building
This PRD defines **Phase 2** of the manual trading control system: a comprehensive RESTful API that enables traders to manually control the Quantronaute trading system. This API will provide full visibility and control over:

1. **Automation Control** - Enable/disable automated trading (replaces file-based toggle from Phase 1)
2. **Position Management** - Open, close, and modify positions manually
3. **Order Management** - Create, update, and cancel orders
4. **Indicator Monitoring** - View current indicator values and configurations
5. **Risk Configuration** - View and update risk management parameters
6. **System Monitoring** - Access account information, metrics, and system health

### Problem Statement
After Phase 1, traders can toggle automation but lack comprehensive manual control. The current system limitations include:

- No programmatic way to open/close positions manually
- No visibility into current indicator values without checking logs
- No ability to adjust risk parameters at runtime
- No centralized API for building custom trading interfaces or automation scripts
- File-based toggle is cumbersome for frequent use or integration with other tools

Traders need a professional-grade API to:
- Build custom dashboards and monitoring tools
- Execute manual trades while respecting risk management rules
- Integrate with third-party tools (TradingView alerts, Telegram bots, etc.)
- Monitor indicator values in real-time for decision-making
- Adjust risk parameters per symbol or strategy dynamically

### Context
Building on Phase 1's event-driven automation toggle, Phase 2 adds a REST API layer that:
- Publishes events to the EventBus (maintaining architectural consistency)
- Respects the automation state (manual trades work whether automation is on/off)
- Enforces risk management rules (guided control - API calls validated by RiskManager)
- Provides read-only access to system state (indicators, positions, account info)
- Uses JWT authentication for secure access

---

## 2. Goals

### Primary Goals
1. **Enable manual trade execution** via REST API with full risk management validation
2. **Provide comprehensive system visibility** (indicators, positions, account, metrics)
3. **Allow runtime risk configuration** (update stop-loss, take-profit, position sizing parameters)
4. **Replace file-based toggle** with API-based automation control
5. **Maintain architectural integrity** (all API calls flow through EventBus)
6. **Ensure security** (authentication, authorization, rate limiting)
7. **Support integration** (well-documented API for third-party tools)

### Success Criteria
- Traders can execute manual trades via API that respect risk management rules
- Traders can view real-time indicator values for all symbols and timeframes
- Traders can update risk parameters (SL, TP, position sizing) at runtime
- API replaces file-based toggle with instant automation control
- API is secured with authentication and authorization
- API documentation is auto-generated (OpenAPI/Swagger)
- API response times are < 500ms for read operations, < 2s for write operations

---

## 3. User Stories

### As a Manual Trader

**US-1**: As a trader, I want to open a manual position via API so that I can execute trades based on my own analysis while still respecting my risk management rules (position sizing, SL, TP).

**US-2**: As a trader, I want to close a specific position via API so that I can manually exit trades when I see profit-taking or risk-reduction opportunities.

**US-3**: As a trader, I want to modify the stop-loss and take-profit of an existing position via API so that I can adjust my risk as market conditions change.

**US-4**: As a trader, I want to view current indicator values (RSI, MACD, ATR, etc.) via API so that I can make informed manual trading decisions.

**US-5**: As a trader, I want to toggle automation on/off via API instead of writing to a file so that I can quickly pause/resume automated trading from my custom dashboard.

### As a Strategy Analyst

**US-6**: As a trader, I want to view all configured strategies and their entry/exit conditions via API so that I can understand what trading logic is active.

**US-7**: As a trader, I want to see the current state of each strategy condition (true/false) in real-time so that I can understand why a strategy is or isn't generating signals.

**US-8**: As a trader, I want to query specific condition values (e.g., "is regime == bull_contraction?", "is close > previous_close?") so that I can manually verify strategy logic before taking trades.

### As a System Integrator

**US-9**: As a developer, I want to retrieve account balance, equity, and margin information via API so that I can monitor account health in my custom dashboard.

### As a Risk Manager

**US-10**: As a trader, I want to view current risk parameters (position sizing, SL type, TP targets) via API so that I know what rules will be applied to my manual trades.

**US-11**: As a trader, I want to update risk parameters (change SL from fixed to trailing, adjust TP targets) via API so that I can adapt my risk strategy without editing YAML files and restarting the application.

**US-12**: As a trader, I want to query my daily loss limit and remaining risk budget via API so that I know if I'm approaching account-level risk limits.

### As a System Administrator

**US-13**: As an admin, I want to access system health metrics via API so that I can monitor service status, event bus activity, and error rates.

**US-14**: As an admin, I want to configure API authentication tokens so that only authorized users can execute trades or view sensitive information.

---

## 4. Functional Requirements

### FR-1: API Architecture & Technology Stack

**Description**: Define the technical foundation for the REST API.

**Requirements**:
- FR-1.1: Use **FastAPI** as the web framework (async support, auto-documentation, type validation)
- FR-1.2: Deploy API as a separate service alongside the TradingOrchestrator (same process or separate container)
- FR-1.3: API communicates with trading system exclusively via EventBus (no direct service access)
- FR-1.4: Use Pydantic models for request/response validation (consistent with existing codebase)
- FR-1.5: Auto-generate OpenAPI documentation at `/docs` (Swagger UI) and `/redoc`
- FR-1.6: Run API on configurable port (default: 8080) with CORS support for web dashboards
- FR-1.7: Support JSON request/response format only (no XML, no form data)

**Technology Stack**:
```
FastAPI 0.104+
Uvicorn (ASGI server)
Pydantic 2.x
python-jose (JWT tokens)
passlib (password hashing)
python-multipart (file uploads, if needed later)
```

**Configuration** (new environment variables):
```bash
API_ENABLED=true
API_HOST=0.0.0.0
API_PORT=8080
API_CORS_ORIGINS=["http://localhost:3000"]
API_SECRET_KEY={generated-secret}
API_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

### FR-2: Authentication & Authorization

**Description**: Secure the API with token-based authentication.

**Requirements**:
- FR-2.1: Use JWT (JSON Web Tokens) for authentication
- FR-2.2: Provide `/auth/login` endpoint (username/password → JWT token)
- FR-2.3: Provide `/auth/refresh` endpoint (refresh token → new JWT token)
- FR-2.4: Store user credentials in configuration file or environment variables (Phase 2: single user; multi-user is Phase 3+)
- FR-2.5: Require `Authorization: Bearer {token}` header for all protected endpoints
- FR-2.6: Token expiration: 60 minutes (configurable)
- FR-2.7: Return `401 Unauthorized` for missing/invalid tokens
- FR-2.8: Return `403 Forbidden` for valid tokens with insufficient permissions (future multi-user support)

**Single User Configuration**:
```bash
# .env.broker
API_USERNAME=trader
API_PASSWORD={hashed-password}
# OR
API_CREDENTIALS_FILE=/app/config/api_credentials.json
```

**Credential File Format** (`api_credentials.json`):
```json
{
  "username": "trader",
  "password_hash": "$2b$12$...",
  "roles": ["admin"]
}
```

**Out of Scope for Phase 2**:
- Multi-user support (single trader only)
- Role-based access control (RBAC) - all or nothing
- OAuth2 / SSO integration
- API key authentication (JWT only)

---

### FR-3: Automation Control Endpoints

**Description**: Replace Phase 1's file-based toggle with API endpoints.

**Requirements**:
- FR-3.1: `POST /automation/enable` - Enable automated trading
- FR-3.2: `POST /automation/disable` - Disable automated trading
- FR-3.3: `GET /automation/status` - Get current automation state
- FR-3.4: All endpoints publish `ToggleAutomationEvent` to EventBus (reusing Phase 1 infrastructure)
- FR-3.5: Endpoints accept optional `reason` field (why automation is being toggled)
- FR-3.6: Return current state, last changed timestamp, and reason in response
- FR-3.7: Rate limit: 10 requests/minute per user (prevent accidental rapid toggling)

**API Specification**:

**POST /automation/enable**
```json
Request:
{
  "reason": "News event passed, resuming automation"  // Optional
}

Response (200 OK):
{
  "status": "success",
  "automation_enabled": true,
  "previous_state": false,
  "changed_at": "2025-11-17T10:30:00Z",
  "reason": "News event passed, resuming automation"
}
```

**POST /automation/disable**
```json
Request:
{
  "reason": "NFP announcement in 5 minutes"  // Optional
}

Response (200 OK):
{
  "status": "success",
  "automation_enabled": false,
  "previous_state": true,
  "changed_at": "2025-11-17T10:25:00Z",
  "reason": "NFP announcement in 5 minutes"
}
```

**GET /automation/status**
```json
Response (200 OK):
{
  "automation_enabled": true,
  "last_changed": "2025-11-17T10:30:00Z",
  "last_reason": "News event passed, resuming automation",
  "changed_by": "api_user:trader",
  "uptime_enabled_percent": 87.5,  // % time enabled in last 24h
  "toggle_count_24h": 4  // Number of toggles in last 24h
}
```

---

### FR-4: Position Management Endpoints

**Description**: Enable manual position opening, closing, and modification.

**Requirements**:
- FR-4.1: `GET /positions` - List all open positions
- FR-4.2: `GET /positions/{symbol}` - List open positions for a specific symbol
- FR-4.3: `GET /positions/{symbol}/{ticket}` - Get details of a specific position
- FR-4.4: `POST /positions/open` - Open a new manual position (with risk validation)
- FR-4.5: `POST /positions/{symbol}/{ticket}/close` - Close a specific position
- FR-4.6: `POST /positions/{symbol}/{ticket}/modify` - Modify SL/TP of a position
- FR-4.7: `POST /positions/close-all` - Close all positions (with optional symbol filter)
- FR-4.8: All write operations publish events to EventBus and go through TradeExecutionService
- FR-4.9: Position opening validates risk via EntryManager (respects position sizing, SL, TP rules)
- FR-4.10: Return validation errors (400 Bad Request) if risk limits would be breached

**API Specification**:

**POST /positions/open**
```json
Request:
{
  "symbol": "XAUUSD",
  "direction": "long",  // "long" or "short"
  "strategy_name": "manual",  // Special strategy for manual trades
  "volume": null,  // If null, uses EntryManager to calculate position size
  "entry_price": null,  // If null, uses current market price
  "stop_loss": null,  // If null, uses EntryManager to calculate SL
  "take_profit": null,  // If null, uses EntryManager to calculate TP
  "comment": "Manual trade based on 4H support level"
}

Response (200 OK):
{
  "status": "success",
  "position": {
    "ticket": 123456789,
    "symbol": "XAUUSD",
    "direction": "long",
    "volume": 0.5,
    "entry_price": 2650.25,
    "stop_loss": 2645.00,
    "take_profit": 2660.00,
    "comment": "Manual trade based on 4H support level",
    "magic": 999999,  // Special magic number for manual trades
    "opened_at": "2025-11-17T10:30:00Z"
  },
  "risk_calculation": {
    "risk_amount": 525.00,  // Dollar risk
    "risk_percent": 0.525,  // % of account
    "reward_ratio": 2.0  // R:R ratio
  }
}

Response (400 Bad Request - Risk Limit Exceeded):
{
  "status": "error",
  "error": "Daily loss limit exceeded",
  "details": {
    "daily_loss_limit": 1000.00,
    "current_daily_loss": 950.00,
    "requested_risk": 525.00,
    "available_risk": 50.00
  }
}

Response (400 Bad Request - Invalid Parameters):
{
  "status": "error",
  "error": "Invalid stop loss level",
  "details": {
    "stop_loss": 2655.00,
    "entry_price": 2650.25,
    "direction": "long",
    "reason": "Stop loss must be below entry price for long positions"
  }
}
```

**POST /positions/{symbol}/{ticket}/close**
```json
Request:
{
  "volume": null,  // If null, closes entire position; otherwise partial close
  "reason": "Manual profit taking at resistance"  // Optional
}

Response (200 OK):
{
  "status": "success",
  "closed_position": {
    "ticket": 123456789,
    "symbol": "XAUUSD",
    "volume_closed": 0.5,
    "close_price": 2658.75,
    "profit": 425.00,
    "closed_at": "2025-11-17T11:00:00Z"
  }
}
```

**POST /positions/{symbol}/{ticket}/modify**
```json
Request:
{
  "stop_loss": 2652.00,  // New SL level
  "take_profit": 2665.00  // New TP level
}

Response (200 OK):
{
  "status": "success",
  "modified_position": {
    "ticket": 123456789,
    "symbol": "XAUUSD",
    "stop_loss": 2652.00,
    "take_profit": 2665.00,
    "modified_at": "2025-11-17T10:45:00Z"
  }
}
```

**GET /positions**
```json
Response (200 OK):
{
  "positions": [
    {
      "ticket": 123456789,
      "symbol": "XAUUSD",
      "direction": "long",
      "volume": 0.5,
      "entry_price": 2650.25,
      "current_price": 2658.75,
      "stop_loss": 2645.00,
      "take_profit": 2660.00,
      "profit": 425.00,
      "swap": -2.50,
      "magic": 999999,
      "comment": "Manual trade",
      "opened_at": "2025-11-17T10:30:00Z"
    }
  ],
  "total_positions": 1,
  "total_profit": 425.00
}
```

---

### FR-5: Order Management Endpoints

**Description**: Enable manual pending order creation, modification, and cancellation.

**Requirements**:
- FR-5.1: `GET /orders` - List all pending orders
- FR-5.2: `GET /orders/{symbol}` - List pending orders for a specific symbol
- FR-5.3: `POST /orders/create` - Create a new pending order (limit, stop, stop-limit)
- FR-5.4: `POST /orders/{ticket}/modify` - Modify price, SL, or TP of a pending order
- FR-5.5: `POST /orders/{ticket}/cancel` - Cancel a pending order
- FR-5.6: `POST /orders/cancel-all` - Cancel all pending orders (with optional symbol filter)
- FR-5.7: All write operations go through OrdersClient (existing MT5 integration)
- FR-5.8: Validate order types (BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP, etc.)

**API Specification**:

**POST /orders/create**
```json
Request:
{
  "symbol": "XAUUSD",
  "order_type": "BUY_LIMIT",  // BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP, etc.
  "volume": 0.5,
  "price": 2640.00,
  "stop_loss": 2635.00,
  "take_profit": 2650.00,
  "comment": "Manual buy limit at support",
  "expiration": null  // Future: order expiration time
}

Response (200 OK):
{
  "status": "success",
  "order": {
    "ticket": 987654321,
    "symbol": "XAUUSD",
    "order_type": "BUY_LIMIT",
    "volume": 0.5,
    "price": 2640.00,
    "stop_loss": 2635.00,
    "take_profit": 2650.00,
    "comment": "Manual buy limit at support",
    "magic": 999999,
    "created_at": "2025-11-17T10:30:00Z"
  }
}
```

**POST /orders/{ticket}/cancel**
```json
Response (200 OK):
{
  "status": "success",
  "cancelled_order": {
    "ticket": 987654321,
    "symbol": "XAUUSD",
    "cancelled_at": "2025-11-17T11:00:00Z"
  }
}
```

---

### FR-6: Indicator Monitoring Endpoints

**Description**: Provide read-only access to current indicator values and configurations.

**Requirements**:
- FR-6.1: `GET /indicators/{symbol}` - Get all indicator values for a symbol (all timeframes)
- FR-6.2: `GET /indicators/{symbol}/{timeframe}` - Get indicator values for a specific timeframe
- FR-6.3: `GET /indicators/{symbol}/{timeframe}/{indicator}` - Get specific indicator value
- FR-6.4: `GET /indicators/config/{symbol}` - Get indicator configuration (parameters)
- FR-6.5: Return current values (latest calculated) and timestamp
- FR-6.6: Support common indicators: RSI, MACD, ATR, EMA, SMA, BB, ADX, Stochastic, etc.
- FR-6.7: Retrieve values from IndicatorCalculationService via EventBus query
- FR-6.8: Cache indicator values for 5 seconds to reduce load

**API Specification**:

**GET /indicators/XAUUSD/1**
```json
Response (200 OK):
{
  "symbol": "XAUUSD",
  "timeframe": "1",
  "timestamp": "2025-11-17T10:30:00Z",
  "indicators": {
    "RSI": {
      "value": 62.5,
      "config": {"period": 14}
    },
    "MACD": {
      "macd": 1.25,
      "signal": 0.85,
      "histogram": 0.40,
      "config": {"fast": 12, "slow": 26, "signal": 9}
    },
    "ATR": {
      "value": 8.5,
      "config": {"period": 14}
    },
    "EMA_20": {
      "value": 2648.50,
      "config": {"period": 20}
    },
    "BB": {
      "upper": 2655.00,
      "middle": 2650.00,
      "lower": 2645.00,
      "config": {"period": 25, "std_dev": 1.5}
    },
    "regime": {
      "value": "bull_expansion",
      "confidence": 0.85
    }
  },
  "price": {
    "close": 2650.25,
    "open": 2649.50,
    "high": 2651.00,
    "low": 2648.75
  }
}
```

**GET /indicators/XAUUSD**
```json
Response (200 OK):
{
  "symbol": "XAUUSD",
  "timeframes": {
    "1": { /* indicators for 1-minute */ },
    "5": { /* indicators for 5-minute */ },
    "15": { /* indicators for 15-minute */ },
    "60": { /* indicators for 60-minute */ },
    "240": { /* indicators for 240-minute */ }
  },
  "timestamp": "2025-11-17T10:30:00Z"
}
```

**GET /indicators/config/XAUUSD**
```json
Response (200 OK):
{
  "symbol": "XAUUSD",
  "timeframes": {
    "1": {
      "bb": {"window": 25, "num_std_dev": 1.5}
    },
    "15": {
      "rsi": {"period": 14},
      "macd": {"fast": 12, "slow": 26, "signal": 9},
      "atr": {"period": 14}
    }
  },
  "config_file": "config/indicators/xauusd/*.yaml"
}
```

---

### FR-7: Risk Configuration Endpoints

**Description**: View and update risk management parameters at runtime.

**Requirements**:
- FR-7.1: `GET /risk/config` - Get current risk configuration (all symbols and strategies)
- FR-7.2: `GET /risk/config/{symbol}` - Get risk configuration for a specific symbol
- FR-7.3: `GET /risk/config/{symbol}/{strategy}` - Get risk configuration for a specific strategy
- FR-7.4: `POST /risk/config/{symbol}/{strategy}/update` - Update risk parameters (SL, TP, position sizing)
- FR-7.5: `GET /risk/limits` - Get account-level risk limits (daily loss limit, max drawdown, etc.)
- FR-7.6: `GET /risk/status` - Get current risk status (remaining daily risk budget, open risk, etc.)
- FR-7.7: Updates publish `RiskConfigUpdatedEvent` to EventBus
- FR-7.8: Validate updates (e.g., TP must be farther from entry than SL)
- FR-7.9: Updates persist to strategy YAML files (so they survive restarts)

**API Specification**:

**GET /risk/config/XAUUSD/manual**
```json
Response (200 OK):
{
  "symbol": "XAUUSD",
  "strategy": "manual",
  "position_sizing": {
    "type": "percentage",
    "value": 1.0,  // 1% of account per trade
    "atr_distance": 0.0
  },
  "stop_loss": {
    "type": "monetary",
    "value": 500.00,  // Max $500 loss per trade
    "trailing": false
  },
  "take_profit": {
    "type": "multi_target",
    "targets": [
      {"value": 1.0, "percent": 60, "move_stop": true},
      {"value": 2.0, "percent": 40, "move_stop": false}
    ]
  }
}
```

**POST /risk/config/XAUUSD/manual/update**
```json
Request:
{
  "stop_loss": {
    "type": "trailing",
    "value": 50,  // 50 pips trailing
    "activation_profit": 30  // Activate after 30 pips profit
  }
}

Response (200 OK):
{
  "status": "success",
  "updated_config": {
    "symbol": "XAUUSD",
    "strategy": "manual",
    "stop_loss": {
      "type": "trailing",
      "value": 50,
      "activation_profit": 30
    }
  },
  "updated_at": "2025-11-17T10:30:00Z",
  "persisted": true  // Saved to YAML file
}
```

**GET /risk/status**
```json
Response (200 OK):
{
  "daily_loss_limit": 1000.00,
  "current_daily_loss": 350.00,
  "remaining_daily_budget": 650.00,
  "daily_loss_percent": 35.0,
  "max_drawdown_limit": 10.0,  // %
  "current_drawdown": 3.5,  // %
  "open_positions_risk": 1050.00,  // Total $ at risk in open positions
  "available_margin": 45000.00,
  "is_trading_allowed": true,
  "restrictions": []  // e.g., ["daily_loss_limit_breached", "news_restriction_active"]
}
```

**GET /risk/limits**
```json
Response (200 OK):
{
  "account_level": {
    "daily_loss_limit": 1000.00,
    "max_drawdown_pct": 10.0,
    "close_positions_on_breach": true,
    "stop_trading_on_breach": true,
    "cooldown_period_minutes": 60,
    "daily_reset_time": "00:00:00"
  },
  "symbol_limits": {
    "XAUUSD": {
      "max_positions": 5,
      "max_volume_per_position": 2.0,
      "risk_per_trade": 500.00
    },
    "BTCUSD": {
      "max_positions": 3,
      "max_volume_per_position": 1.0,
      "risk_per_trade": 500.00
    }
  }
}
```

---

### FR-8: Strategy Monitoring Endpoints

**Description**: Provide read-only access to strategy configurations and real-time condition evaluation.

**Requirements**:
- FR-8.1: `GET /strategies` - List all configured strategies across all symbols
- FR-8.2: `GET /strategies/{symbol}` - List strategies for a specific symbol
- FR-8.3: `GET /strategies/{symbol}/{strategy_name}` - Get full strategy configuration
- FR-8.4: `GET /strategies/{symbol}/{strategy_name}/conditions` - Get real-time condition evaluation
- FR-8.5: `GET /strategies/{symbol}/{strategy_name}/conditions/entry` - Get entry condition states (long/short)
- FR-8.6: `GET /strategies/{symbol}/{strategy_name}/conditions/exit` - Get exit condition states (long/short)
- FR-8.7: Query StrategyEvaluationService for current condition states via EventBus
- FR-8.8: Return both the condition definition and its current boolean state
- FR-8.9: Include actual values being compared (e.g., close=2650.25, previous_close=2649.50)
- FR-8.10: Cache strategy configs (static YAML data) but always fetch live condition states

**API Specification**:

**GET /strategies**
```json
Response (200 OK):
{
  "strategies": {
    "XAUUSD": [
      {
        "name": "anchors-transitions-and-htf-bias",
        "timeframes": ["1", "15", "240"],
        "has_entry_long": true,
        "has_entry_short": false,
        "has_exit_long": true,
        "has_exit_short": false,
        "active": true
      }
    ],
    "BTCUSD": [
      {
        "name": "test-strategy",
        "timeframes": ["1", "15", "60"],
        "has_entry_long": true,
        "has_entry_short": true,
        "has_exit_long": true,
        "has_exit_short": true,
        "active": true
      }
    ]
  },
  "total_strategies": 2
}
```

**GET /strategies/XAUUSD/anchors-transitions-and-htf-bias**
```json
Response (200 OK):
{
  "symbol": "XAUUSD",
  "name": "anchors-transitions-and-htf-bias",
  "meta": {
    "version": "1.4.0",
    "author": "you",
    "description": "Demonstrates YAML anchors, state transitions, and daily bias gating.",
    "created_at": "2025-08-10T09:25:00Z"
  },
  "timeframes": ["1", "15", "240"],
  "entry": {
    "long": {
      "mode": "all",
      "conditions": [
        {
          "signal": "close",
          "operator": ">",
          "value": "previous_close",
          "timeframe": "1"
        },
        {
          "signal": "regime",
          "operator": "==",
          "value": "bull_contraction",
          "timeframe": "240"
        }
      ]
    },
    "short": null
  },
  "exit": {
    "long": {
      "mode": "all",
      "conditions": [
        {
          "signal": "close",
          "operator": "<",
          "value": "previous_close",
          "timeframe": "240"
        }
      ]
    },
    "short": null
  },
  "risk": {
    "position_sizing": {
      "type": "fixed",
      "value": 1.0
    },
    "sl": {
      "type": "monetary",
      "value": 500.0
    },
    "tp": {
      "type": "fixed",
      "value": 1000.0
    }
  },
  "config_file": "config/strategies/xauusd/test.yaml"
}
```

**GET /strategies/XAUUSD/anchors-transitions-and-htf-bias/conditions**
```json
Response (200 OK):
{
  "symbol": "XAUUSD",
  "strategy": "anchors-transitions-and-htf-bias",
  "timestamp": "2025-11-17T10:30:00Z",
  "entry": {
    "long": {
      "mode": "all",
      "conditions": [
        {
          "condition": {
            "signal": "close",
            "operator": ">",
            "value": "previous_close",
            "timeframe": "1"
          },
          "state": true,
          "evaluation": {
            "left": 2650.25,
            "operator": ">",
            "right": 2649.50,
            "result": true
          }
        },
        {
          "condition": {
            "signal": "regime",
            "operator": "==",
            "value": "bull_contraction",
            "timeframe": "240"
          },
          "state": false,
          "evaluation": {
            "left": "bull_expansion",
            "operator": "==",
            "right": "bull_contraction",
            "result": false
          }
        }
      ],
      "all_conditions_met": false,
      "would_trigger_entry": false
    },
    "short": null
  },
  "exit": {
    "long": {
      "mode": "all",
      "conditions": [
        {
          "condition": {
            "signal": "close",
            "operator": "<",
            "value": "previous_close",
            "timeframe": "240"
          },
          "state": false,
          "evaluation": {
            "left": 2650.25,
            "operator": "<",
            "right": 2648.00,
            "result": false
          }
        }
      ],
      "all_conditions_met": false,
      "would_trigger_exit": false
    },
    "short": null
  },
  "overall_status": {
    "can_enter_long": false,
    "can_enter_short": false,
    "should_exit_long": false,
    "should_exit_short": false
  }
}
```

**GET /strategies/XAUUSD/anchors-transitions-and-htf-bias/conditions/entry**
```json
Response (200 OK):
{
  "symbol": "XAUUSD",
  "strategy": "anchors-transitions-and-htf-bias",
  "timestamp": "2025-11-17T10:30:00Z",
  "entry_type": "long",
  "mode": "all",
  "conditions": [
    {
      "condition": "close > previous_close @ 1min",
      "state": true,
      "details": {
        "close": 2650.25,
        "previous_close": 2649.50
      }
    },
    {
      "condition": "regime == bull_contraction @ 240min",
      "state": false,
      "details": {
        "regime": "bull_expansion"
      }
    }
  ],
  "all_conditions_met": false,
  "would_trigger": false,
  "blocking_conditions": [
    "regime == bull_contraction @ 240min"
  ]
}
```

---

### FR-9: Account Information Endpoints

**Description**: Provide read-only access to account balance, equity, margin, and positions summary.

**Requirements**:
- FR-9.1: `GET /account/info` - Get full account information
- FR-9.2: `GET /account/balance` - Get account balance
- FR-9.3: `GET /account/equity` - Get account equity
- FR-9.4: `GET /account/margin` - Get margin information
- FR-9.5: `GET /account/summary` - Get account summary (balance, equity, profit, positions count)
- FR-9.6: Retrieve data from MT5Client AccountClient
- FR-9.7: Cache account info for 5 seconds to reduce broker API load

**API Specification**:

**GET /account/summary**
```json
Response (200 OK):
{
  "balance": 100000.00,
  "equity": 100425.00,
  "profit": 425.00,
  "margin": 5000.00,
  "margin_free": 95425.00,
  "margin_level": 2008.5,  // %
  "currency": "USD",
  "leverage": 100,
  "positions": {
    "total": 3,
    "long": 2,
    "short": 1,
    "total_volume": 1.5
  },
  "daily_stats": {
    "daily_profit": -350.00,
    "daily_trades": 12,
    "win_rate": 58.3
  },
  "timestamp": "2025-11-17T10:30:00Z"
}
```

---

### FR-9: System Monitoring Endpoints

**Description**: Provide access to system health, metrics, and logs.

**Requirements**:
- FR-9.1: `GET /system/health` - Get system health status (services running, EventBus status)
- FR-9.2: `GET /system/metrics` - Get system metrics (event counts, processing times, errors)
- FR-9.3: `GET /system/services` - Get status of all services (DataFetching, IndicatorCalculation, etc.)
- FR-9.4: `GET /system/events/recent` - Get recent events from EventBus (last 100 events)
- FR-9.5: `GET /system/logs` - Get recent application logs (last 500 lines, with filtering)
- FR-9.6: All data retrieved from TradingOrchestrator metrics and EventBus history

**API Specification**:

**GET /system/health**
```json
Response (200 OK):
{
  "status": "healthy",  // "healthy", "degraded", "unhealthy"
  "automation_enabled": true,
  "services": {
    "DataFetchingService": "running",
    "IndicatorCalculationService": "running",
    "StrategyEvaluationService": "running",
    "TradeExecutionService": "running"
  },
  "eventbus": {
    "status": "running",
    "events_published_1m": 45,
    "events_delivered_1m": 45,
    "failed_deliveries_1m": 0
  },
  "broker_connection": "connected",
  "uptime_seconds": 86400,
  "last_health_check": "2025-11-17T10:30:00Z"
}
```

**GET /system/metrics**
```json
Response (200 OK):
{
  "orchestrator": {
    "uptime_seconds": 86400,
    "loop_iterations": 2880,
    "avg_loop_time_ms": 125.5,
    "last_loop_time_ms": 118.2
  },
  "services": {
    "DataFetchingService": {
      "data_fetches": 2880,
      "new_candles": 720,
      "errors": 0
    },
    "IndicatorCalculationService": {
      "calculations": 720,
      "avg_calc_time_ms": 45.2,
      "errors": 0
    },
    "StrategyEvaluationService": {
      "evaluations": 720,
      "entry_signals": 25,
      "exit_signals": 18,
      "suppressed_signals": 0
    },
    "TradeExecutionService": {
      "orders_placed": 25,
      "orders_rejected": 3,
      "positions_closed": 18,
      "avg_execution_time_ms": 250.5
    }
  },
  "eventbus": {
    "total_events_published": 5760,
    "total_events_delivered": 5760,
    "failed_deliveries": 0,
    "event_types": {
      "DataFetchedEvent": 2880,
      "NewCandleEvent": 720,
      "IndicatorsCalculatedEvent": 720,
      "EntrySignalEvent": 25,
      "OrderPlacedEvent": 25
    }
  }
}
```

---

### FR-10: Error Handling & Validation

**Description**: Define consistent error responses and validation.

**Requirements**:
- FR-10.1: Use HTTP status codes correctly:
  - 200 OK - Successful read operation
  - 201 Created - Successful write operation (position opened, order created)
  - 400 Bad Request - Validation error, invalid parameters
  - 401 Unauthorized - Missing or invalid authentication token
  - 403 Forbidden - Valid token but insufficient permissions
  - 404 Not Found - Resource doesn't exist (position, order, symbol)
  - 429 Too Many Requests - Rate limit exceeded
  - 500 Internal Server Error - Unexpected server error
  - 503 Service Unavailable - Service is down or broker disconnected

- FR-11.2: Return consistent error format:
```json
{
  "status": "error",
  "error": "Human-readable error message",
  "error_code": "DAILY_LOSS_LIMIT_EXCEEDED",
  "details": {
    // Additional context
  },
  "timestamp": "2025-11-17T10:30:00Z"
}
```

- FR-11.3: Validate all inputs using Pydantic models
- FR-11.4: Log all errors with full context (user, endpoint, parameters)
- FR-11.5: Return validation errors with field-level details:
```json
{
  "status": "error",
  "error": "Validation error",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "field": "stop_loss",
    "error": "Stop loss must be below entry price for long positions",
    "received": 2655.00,
    "entry_price": 2650.25
  }
}
```

---

### FR-11: Rate Limiting & Security

**Description**: Protect the API from abuse and ensure security.

**Requirements**:
- FR-11.1: Rate limiting per endpoint category:
  - Read endpoints (GET): 60 requests/minute
  - Write endpoints (POST): 20 requests/minute
  - Automation toggle: 10 requests/minute
  - Login: 5 requests/minute (prevent brute force)

- FR-12.2: Return `429 Too Many Requests` when rate limit exceeded:
```json
{
  "status": "error",
  "error": "Rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "details": {
    "limit": 60,
    "window": "1 minute",
    "retry_after": 35  // seconds
  }
}
```

- FR-12.3: Use HTTPS only in production (enforce TLS 1.2+)
- FR-12.4: Add CORS headers for web dashboard access (configurable origins)
- FR-12.5: Log all authentication attempts (success and failure)
- FR-12.6: Implement request ID tracking for debugging (return in response header `X-Request-ID`)
- FR-12.7: Add request/response logging (sanitize sensitive data like passwords)

---

### FR-12: API Service Architecture

**Description**: Define how the API integrates with the existing trading system.

**Requirements**:
- FR-12.1: Create new `APIService` component inheriting from `EventDrivenService`
- FR-12.2: APIService runs FastAPI server in a separate thread/async task
- FR-12.3: API endpoints publish events to EventBus and subscribe to response events
- FR-12.4: Use request-response pattern for synchronous operations:
  1. API receives request
  2. API publishes command event (e.g., `OpenPositionCommand`)
  3. API waits for response event (e.g., `PositionOpenedEvent` or `PositionOpenFailedEvent`)
  4. API returns HTTP response based on event

- FR-12.5: Timeout for event responses: 5 seconds (return 503 if no response)
- FR-12.6: APIService initialized by TradingOrchestrator alongside other services
- FR-12.7: API graceful shutdown on orchestrator stop (finish in-flight requests)

**Event Flow Example** (Open Position):
```
1. User → POST /positions/open → APIService
2. APIService → EventBus.publish(OpenPositionCommand)
3. TradeExecutionService (subscribed) → validates risk → executes trade
4. TradeExecutionService → EventBus.publish(PositionOpenedEvent)
5. APIService (subscribed with correlation_id) → receives event
6. APIService → HTTP Response 200 OK → User
```

**New Event Types**:
- `OpenPositionCommand` (symbol, direction, volume, SL, TP, etc.)
- `PositionOpenedEvent` (ticket, entry_price, etc.)
- `PositionOpenFailedEvent` (error, reason)
- `ClosePositionCommand`
- `PositionClosedEvent`
- `ModifyPositionCommand`
- `PositionModifiedEvent`
- `QueryIndicatorsCommand`
- `IndicatorsResponseEvent`
- `RiskConfigUpdatedEvent`

---

### FR-13: Documentation & Developer Experience

**Description**: Provide comprehensive documentation for API users.

**Requirements**:
- FR-13.1: Auto-generate OpenAPI 3.0 specification
- FR-13.2: Provide interactive Swagger UI at `/docs`
- FR-13.3: Provide alternative ReDoc UI at `/redoc`
- FR-13.4: Include request/response examples for all endpoints
- FR-13.5: Document authentication flow with code examples (Python, JavaScript, cURL)
- FR-13.6: Create separate markdown documentation in `docs/api/`
  - `authentication.md` - How to authenticate
  - `manual-trading.md` - How to execute manual trades
  - `indicators.md` - How to read indicator values
  - `risk-management.md` - How to configure risk parameters
  - `examples.md` - Common use cases with code

- FR-14.7: Provide Python client SDK (thin wrapper around requests library)
- FR-14.8: Add health check endpoint `/health` (no auth required) for monitoring
- FR-14.9: Add version endpoint `/version` (no auth required)

**Example Documentation Structure**:
```
docs/
└── api/
    ├── README.md (API overview)
    ├── authentication.md
    ├── endpoints/
    │   ├── automation.md
    │   ├── positions.md
    │   ├── orders.md
    │   ├── indicators.md
    │   ├── risk.md
    │   ├── account.md
    │   └── system.md
    ├── examples/
    │   ├── python-client.md
    │   ├── tradingview-integration.md
    │   └── telegram-bot.md
    └── sdk/
        └── quantronaute_api_client.py (Python SDK)
```

---

## 5. Non-Goals (Out of Scope)

### Explicitly Out of Scope for Phase 2

1. **Multi-User Support**: Phase 2 supports a single user. Multi-user with RBAC is Phase 3+.

2. **Advanced Order Types**: No OCO (One-Cancels-Other), bracket orders, or advanced order logic. Basic limit/stop orders only.

3. **Backtesting API**: No API for running backtests. Backtesting remains a separate offline tool.

4. **Strategy Builder API**: No API for creating/editing strategies. Strategies are YAML-based only.

5. **Indicator Configuration Updates**: FR-6 only reads indicator configs. Updating indicator parameters (e.g., changing RSI period) is out of scope.

6. **Historical Data API**: No API for fetching historical OHLCV data. Use existing data fetching mechanisms.

7. **WebSocket Support**: Phase 2 is REST-only. Real-time WebSocket updates are Phase 3+.

8. **Mobile App**: No native mobile app. API is designed for web dashboards and scripts.

9. **Payment/Subscription System**: No billing or subscription management.

10. **Advanced Analytics**: No performance analytics, trade history analysis, or reporting. Basic metrics only.

11. **News/Calendar Integration**: No news event API or economic calendar integration.

12. **Signal Marketplace**: No third-party signal integration or marketplace.

---

## 6. Technical Considerations

### API Performance

**Response Time Targets**:
- Read endpoints (GET): < 200ms (p95), < 500ms (p99)
- Write endpoints (POST): < 1s (p95), < 2s (p99)
- Indicator queries: < 300ms (cached), < 800ms (uncached)

**Optimization Strategies**:
- Cache indicator values for 5 seconds (reduce EventBus queries)
- Cache account info for 5 seconds (reduce broker API calls)
- Use async/await throughout (FastAPI native async support)
- Batch EventBus queries when possible
- Use connection pooling for database (if added later)

### Event-Driven Request-Response Pattern

**Challenge**: REST API is synchronous, but EventBus is async pub/sub.

**Solution**: Correlation ID pattern
```python
# API endpoint
@app.post("/positions/open")
async def open_position(request: OpenPositionRequest):
    correlation_id = str(uuid.uuid4())

    # Publish command event
    command = OpenPositionCommand(
        correlation_id=correlation_id,
        symbol=request.symbol,
        direction=request.direction,
        ...
    )
    event_bus.publish(command)

    # Wait for response event with matching correlation_id
    response_event = await wait_for_event(
        event_type=PositionOpenedEvent,
        correlation_id=correlation_id,
        timeout=5.0
    )

    if isinstance(response_event, PositionOpenedEvent):
        return {"status": "success", "position": response_event.position}
    else:
        return {"status": "error", "error": response_event.error}
```

**Implementation**:
- Create `EventResponseWaiter` utility class
- Maintain dict of pending requests: `{correlation_id: asyncio.Future}`
- Subscribe to all response events, resolve Futures when correlation_id matches
- Timeout after 5 seconds, return 503 Service Unavailable

### Security Considerations

**Password Storage**:
- Never store plaintext passwords
- Use bcrypt for password hashing (cost factor: 12)
- Store hash in config file or environment variable

**JWT Token Security**:
- Use strong secret key (256-bit random)
- Include `exp` (expiration), `iat` (issued at), `sub` (subject/username) claims
- Refresh tokens have longer expiration (7 days)
- Invalidate tokens on password change (future: token blacklist)

**API Access Logs**:
- Log all requests: timestamp, user, endpoint, IP address, status code
- Sanitize sensitive data (passwords, tokens) before logging
- Rotate logs daily, keep 30 days

### Docker Integration

**Deployment Options**:

**Option A: Same Container as Trading System**
- Pros: Simplest deployment, shared memory with EventBus
- Cons: API crashes could affect trading system
- Recommendation: Use for single-broker setups

**Option B: Separate Container**
- Pros: Isolation, independent scaling, better fault tolerance
- Cons: Requires shared EventBus (Redis pub/sub or similar)
- Recommendation: Use for production multi-broker setups

**Docker Compose Configuration**:
```yaml
services:
  trading-system:
    build: .
    environment:
      - API_ENABLED=true
      - API_PORT=8080
    ports:
      - "8080:8080"
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
```

### Error Recovery

**Broker Disconnection**:
- API returns 503 Service Unavailable when broker disconnected
- Health check endpoint reflects broker connection status
- Retry logic for transient broker errors (3 retries with exponential backoff)

**EventBus Failures**:
- If EventBus unresponsive, return 503 Service Unavailable
- Log CRITICAL error, trigger orchestrator health check
- Auto-restart EventBus if health check fails

**Service Failures**:
- If TradeExecutionService down, return 503 for position operations
- If IndicatorCalculationService down, return 503 for indicator queries
- Health endpoint shows which services are unavailable

---

## 7. Design Considerations

### Option A: Monolithic API vs. Microservices
**Decision**: Monolithic API (single FastAPI application)

**Rationale**:
- Simpler deployment and development
- Lower latency (no inter-service communication)
- Easier to maintain for small team
- Can refactor to microservices later if needed

**Alternative Rejected**: Separate microservices for each domain (positions, indicators, risk) would add complexity without clear benefits at current scale.

---

### Option B: REST vs. GraphQL
**Decision**: REST API

**Rationale**:
- Simpler for junior developers to understand and use
- Better tooling (Swagger, Postman)
- Clearer API versioning
- Sufficient for current use cases

**Alternative Rejected**: GraphQL would be over-engineering for this use case. REST provides all needed functionality.

---

### Option C: Synchronous vs. Async Event Handling
**Decision**: Async with correlation ID pattern

**Rationale**:
- Maintains event-driven architecture (no direct service coupling)
- Allows API to respond quickly (no blocking)
- Supports future WebSocket implementation
- EventBus remains central coordination point

**Alternative Rejected**: Direct service calls would bypass EventBus, violating architecture. Purely async (fire-and-forget) doesn't work for REST API (clients need responses).

---

### Option D: Configuration Updates - Ephemeral vs. Persistent
**Decision**: Persist to YAML files

**Rationale**:
- Changes survive application restarts
- Provides audit trail (YAML files in version control)
- Traders expect configuration to persist
- Fallback to YAML if API unavailable

**Alternative Rejected**: Ephemeral (in-memory only) would confuse users when settings reset on restart.

---

## 8. Success Metrics

### Functional Metrics

**FM-1: API Response Time**
- Metric: 95th percentile response time by endpoint category
- Target: Read < 200ms, Write < 1s
- Measurement: Built-in FastAPI request timing middleware

**FM-2: API Availability**
- Metric: Uptime percentage
- Target: 99.5% uptime (excluding planned maintenance)
- Measurement: Health check endpoint monitoring

**FM-3: Manual Trade Success Rate**
- Metric: % of manual trades that execute successfully (not rejected by risk manager)
- Target: > 95% success rate
- Measurement: Count of PositionOpenedEvent vs. PositionOpenFailedEvent

**FM-4: Indicator Data Freshness**
- Metric: Time lag between indicator calculation and API query
- Target: < 30 seconds (one trading loop)
- Measurement: Compare indicator timestamp to query timestamp

### Operational Metrics

**OM-1: API Request Volume**
- Metric: Requests per minute by endpoint
- Target: N/A (baseline measurement)
- Measurement: Request counter middleware

**OM-2: Authentication Failure Rate**
- Metric: % of requests with authentication errors
- Target: < 1% (excludes intentional invalid tokens)
- Measurement: 401/403 response count / total requests

**OM-3: Rate Limit Hit Rate**
- Metric: % of requests that hit rate limits
- Target: < 5% (indicates limits are appropriately set)
- Measurement: 429 response count / total requests

**OM-4: Event Response Timeout Rate**
- Metric: % of API requests that timeout waiting for EventBus response
- Target: < 0.1%
- Measurement: 503 responses due to timeout / total write requests

### User Acceptance Criteria

**UAC-1**: Trader can open a manual position via API, and it respects risk management rules (position sizing, SL, TP calculated by EntryManager).

**UAC-2**: Trader can view current RSI, MACD, and ATR values for XAUUSD 15-minute chart via API with < 1 second response time.

**UAC-3**: Trader can toggle automation on/off via API, and the state change is reflected in logs and metrics within 2 seconds.

**UAC-4**: Trader can update stop-loss type from "fixed" to "trailing" via API, and the change persists after application restart.

**UAC-5**: All API endpoints return consistent error format (status, error, error_code, details) for validation errors.

**UAC-6**: API documentation is accessible at `/docs` with interactive Swagger UI showing all endpoints with examples.

---

## 9. Open Questions

### Questions Requiring PM/Stakeholder Input

**OQ-1: Multi-Symbol Manual Trades**
- Question: Should manual trades support multi-symbol correlation checks (e.g., prevent opening XAUUSD and BTCUSD in same direction)?
- Impact: Adds complexity to risk validation
- Recommendation: Out of scope for Phase 2; add in Phase 3 if needed

**OQ-2: Position Modification Restrictions**
- Question: Should API allow moving stop-loss in unfavorable direction (increasing risk)?
- Impact: Safety vs. flexibility tradeoff
- Recommendation: Allow but log WARNING, require confirmation flag in request

**OQ-3: Indicator Update Frequency**
- Question: Should API trigger on-demand indicator recalculation, or only return cached values?
- Impact: On-demand increases accuracy but adds load
- Recommendation: Cached values only (5-second cache), on-demand is Phase 3+

**OQ-4: Historical Indicator Values**
- Question: Should API provide historical indicator values (e.g., RSI for last 100 candles)?
- Impact: Large response payloads, additional storage
- Recommendation: Out of scope for Phase 2; current value only

**OQ-5: Partial Position Closes**
- Question: Should API support partial position closes (e.g., close 50% of position)?
- Current Decision: Yes (volume parameter in close endpoint)
- Needs Validation: Confirm this aligns with manual trading workflows

### Questions for Technical Team

**TQ-1: EventBus Scalability**
- Question: Can current EventBus handle additional API-generated events without performance degradation?
- Action: Load test EventBus with 100 concurrent API requests

**TQ-2: Token Storage**
- Question: Where to store JWT secret key securely in production?
- Options: Environment variable, AWS Secrets Manager, Kubernetes secrets
- Action: Define secret management strategy per deployment environment

**TQ-3: API Versioning**
- Question: Should we version the API from the start (e.g., /v1/positions)?
- Recommendation: Yes, plan for breaking changes in future
- Action: All endpoints prefixed with `/api/v1/`

**TQ-4: Database Requirement**
- Question: Do we need a database for request logging, token blacklist, or trade history?
- Current Decision: No database for Phase 2 (file-based logging)
- Future: Database for Phase 3+ (PostgreSQL recommended)

**TQ-5: Real-Time Updates**
- Question: Should we plan WebSocket support from the start (even if not implemented)?
- Recommendation: Design API with WebSocket compatibility in mind (use events)
- Action: Document WebSocket plan in Phase 3 PRD

---

## 10. Implementation Notes for Junior Developers

### Step-by-Step Implementation Guide

**Step 1: Setup FastAPI Project Structure**
- Create new folder: `app/api/`
- Files to create:
  - `app/api/main.py` - FastAPI application entry point
  - `app/api/dependencies.py` - Dependency injection (auth, EventBus)
  - `app/api/middleware.py` - Request logging, rate limiting
  - `app/api/models/` - Pydantic request/response models
  - `app/api/routers/` - Endpoint routers by domain
  - `app/api/utils/` - Helper functions (JWT, correlation ID)
  - `app/api/events.py` - API-specific event types

**Step 2: Implement Authentication**
- File: `app/api/auth.py`
- Implement: Password hashing (bcrypt), JWT token generation/validation
- Create: `/auth/login` and `/auth/refresh` endpoints
- Add: OAuth2PasswordBearer dependency for protected endpoints

**Step 3: Create Base API Service**
- File: `app/api/service.py`
- Create `APIService` class inheriting from `EventDrivenService`
- Initialize FastAPI app, register routers, start Uvicorn server in async task
- Implement: `EventResponseWaiter` utility for request-response pattern

**Step 4: Implement Automation Endpoints**
- File: `app/api/routers/automation.py`
- Endpoints: `POST /enable`, `POST /disable`, `GET /status`
- Reuse: Phase 1's `ToggleAutomationEvent` and `AutomationStateManager`
- Test: Toggle automation via API and verify state change

**Step 5: Implement Position Endpoints**
- File: `app/api/routers/positions.py`
- Endpoints: `GET /positions`, `POST /positions/open`, `POST /positions/{symbol}/{ticket}/close`, `POST /positions/{symbol}/{ticket}/modify`
- Create events: `OpenPositionCommand`, `PositionOpenedEvent`, `ClosePositionCommand`, etc.
- Integrate: EntryManager for risk validation on manual trades
- Test: Open/close/modify positions via API

**Step 6: Implement Order Endpoints**
- File: `app/api/routers/orders.py`
- Endpoints: `GET /orders`, `POST /orders/create`, `POST /orders/{ticket}/cancel`
- Use: Existing OrdersClient from MT5 integration
- Test: Create limit/stop orders via API

**Step 7: Implement Indicator Endpoints**
- File: `app/api/routers/indicators.py`
- Endpoints: `GET /indicators/{symbol}`, `GET /indicators/{symbol}/{timeframe}`
- Create: `QueryIndicatorsCommand`, `IndicatorsResponseEvent`
- Add: IndicatorCalculationService handler to respond to queries
- Implement: 5-second cache for indicator values
- Test: Query indicators and verify response time

**Step 8: Implement Strategy Endpoints**
- File: `app/api/routers/strategies.py`
- Endpoints: `GET /strategies`, `GET /strategies/{symbol}/{name}`, `GET /strategies/{symbol}/{name}/conditions`
- Create: `QueryStrategyConditionsCommand`, `StrategyConditionsResponseEvent`
- Add: StrategyEvaluationService handler to respond with live condition states
- Logic: Load strategy YAML, evaluate each condition, return condition + state + actual values
- Test: Query strategy conditions and verify real-time evaluation

**Step 9: Implement Risk Endpoints**
- File: `app/api/routers/risk.py`
- Endpoints: `GET /risk/config`, `POST /risk/config/{symbol}/{strategy}/update`, `GET /risk/status`
- Create: `RiskConfigUpdatedEvent`
- Implement: YAML file updates for persistence
- Test: Update risk config and verify persistence across restart

**Step 10: Implement Account & System Endpoints**
- Files: `app/api/routers/account.py`, `app/api/routers/system.py`
- Account endpoints: `GET /account/summary`, `GET /account/balance`
- System endpoints: `GET /system/health`, `GET /system/metrics`
- Use: Existing MT5Client and Orchestrator metrics
- Test: Query account info and system health

**Step 11: Add Middleware & Security**
- File: `app/api/middleware.py`
- Implement: Request logging, rate limiting, CORS, request ID tracking
- Add: Error handling middleware (catch all exceptions, return consistent format)
- Test: Rate limiting behavior, error responses

**Step 12: Generate Documentation**
- Configure: FastAPI auto-documentation (title, description, version)
- Add: Request/response examples to all endpoints (using Pydantic `Config.schema_extra`)
- Create: Markdown docs in `docs/api/`
- Test: Access `/docs` and `/redoc`, verify examples and descriptions

**Step 13: Integration with Orchestrator**
- File: `app/infrastructure/orchestrator.py`
- Add: APIService initialization and registration
- Add: Environment variable `API_ENABLED` to conditionally start API
- Test: Full system startup with API enabled

**Step 14: Create Python SDK**
- File: `docs/api/sdk/quantronaute_api_client.py`
- Implement: Thin wrapper around `requests` library
- Methods: `login()`, `open_position()`, `get_indicators()`, etc.
- Test: SDK against running API

**Step 15: End-to-End Testing**
- Create integration tests:
  - Authentication flow
  - Manual trade execution with risk validation
  - Automation toggle
  - Indicator queries
  - Risk config updates
  - Error handling (invalid tokens, validation errors, rate limits)
- Performance test: 100 concurrent requests

**Step 16: Documentation & Deployment**
- Write: API usage guide in `docs/api/README.md`
- Update: Main README with API section
- Create: Docker Compose configuration with API exposed
- Deploy: Staging environment for user testing

---

### Code Structure Reference

```
app/
├── api/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── service.py                 # APIService (EventDrivenService)
│   ├── auth.py                    # JWT authentication
│   ├── dependencies.py            # FastAPI dependencies
│   ├── middleware.py              # Logging, rate limiting, CORS
│   ├── events.py                  # API-specific events
│   ├── models/                    # Pydantic models
│   │   ├── requests.py            # Request models
│   │   ├── responses.py           # Response models
│   │   └── auth.py                # Auth models
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── automation.py          # Automation endpoints
│   │   ├── positions.py           # Position endpoints
│   │   ├── orders.py              # Order endpoints
│   │   ├── indicators.py          # Indicator endpoints
│   │   ├── strategies.py          # NEW - Strategy monitoring endpoints
│   │   ├── risk.py                # Risk config endpoints
│   │   ├── account.py             # Account info endpoints
│   │   └── system.py              # System monitoring endpoints
│   └── utils/
│       ├── correlation.py         # Correlation ID utilities
│       ├── event_waiter.py        # EventResponseWaiter
│       ├── cache.py               # Simple cache implementation
│       └── rate_limit.py          # Rate limiting logic
│
├── infrastructure/
│   ├── orchestrator.py            # UPDATED - Initialize APIService
│   └── events.py                  # UPDATED - Add API command/response events
│
└── main_multi_symbol.py           # UPDATED - Wire up APIService

config/
├── api_credentials.json           # NEW - API user credentials
└── {broker}/
    └── .env.broker                # UPDATED - Add API_* env vars

docs/
└── api/
    ├── README.md                  # API overview
    ├── authentication.md          # Auth guide
    ├── endpoints/                 # Per-endpoint docs
    ├── examples/                  # Code examples
    └── sdk/
        └── quantronaute_api_client.py  # Python SDK
```

---

### API Endpoint Summary Table

| Category | Endpoint | Method | Auth | Description |
|----------|----------|--------|------|-------------|
| **Auth** | `/auth/login` | POST | No | Login and get JWT token |
| **Auth** | `/auth/refresh` | POST | Yes | Refresh JWT token |
| **Automation** | `/automation/enable` | POST | Yes | Enable automated trading |
| **Automation** | `/automation/disable` | POST | Yes | Disable automated trading |
| **Automation** | `/automation/status` | GET | Yes | Get automation status |
| **Positions** | `/positions` | GET | Yes | List all open positions |
| **Positions** | `/positions/{symbol}` | GET | Yes | List positions by symbol |
| **Positions** | `/positions/{symbol}/{ticket}` | GET | Yes | Get position details |
| **Positions** | `/positions/open` | POST | Yes | Open manual position |
| **Positions** | `/positions/{symbol}/{ticket}/close` | POST | Yes | Close position |
| **Positions** | `/positions/{symbol}/{ticket}/modify` | POST | Yes | Modify position SL/TP |
| **Positions** | `/positions/close-all` | POST | Yes | Close all positions |
| **Orders** | `/orders` | GET | Yes | List pending orders |
| **Orders** | `/orders/{symbol}` | GET | Yes | List orders by symbol |
| **Orders** | `/orders/create` | POST | Yes | Create pending order |
| **Orders** | `/orders/{ticket}/modify` | POST | Yes | Modify pending order |
| **Orders** | `/orders/{ticket}/cancel` | POST | Yes | Cancel pending order |
| **Orders** | `/orders/cancel-all` | POST | Yes | Cancel all orders |
| **Indicators** | `/indicators/{symbol}` | GET | Yes | Get all indicators |
| **Indicators** | `/indicators/{symbol}/{tf}` | GET | Yes | Get indicators by timeframe |
| **Indicators** | `/indicators/{symbol}/{tf}/{name}` | GET | Yes | Get specific indicator |
| **Indicators** | `/indicators/config/{symbol}` | GET | Yes | Get indicator config |
| **Strategies** | `/strategies` | GET | Yes | List all strategies |
| **Strategies** | `/strategies/{symbol}` | GET | Yes | List strategies by symbol |
| **Strategies** | `/strategies/{symbol}/{name}` | GET | Yes | Get strategy config |
| **Strategies** | `/strategies/{symbol}/{name}/conditions` | GET | Yes | Get real-time condition states |
| **Strategies** | `/strategies/{symbol}/{name}/conditions/entry` | GET | Yes | Get entry condition states |
| **Strategies** | `/strategies/{symbol}/{name}/conditions/exit` | GET | Yes | Get exit condition states |
| **Risk** | `/risk/config` | GET | Yes | Get all risk configs |
| **Risk** | `/risk/config/{symbol}/{strategy}` | GET | Yes | Get risk config |
| **Risk** | `/risk/config/{symbol}/{strategy}/update` | POST | Yes | Update risk config |
| **Risk** | `/risk/limits` | GET | Yes | Get account risk limits |
| **Risk** | `/risk/status` | GET | Yes | Get current risk status |
| **Account** | `/account/info` | GET | Yes | Get full account info |
| **Account** | `/account/balance` | GET | Yes | Get account balance |
| **Account** | `/account/equity` | GET | Yes | Get account equity |
| **Account** | `/account/margin` | GET | Yes | Get margin info |
| **Account** | `/account/summary` | GET | Yes | Get account summary |
| **System** | `/system/health` | GET | Yes | Get system health |
| **System** | `/system/metrics` | GET | Yes | Get system metrics |
| **System** | `/system/services` | GET | Yes | Get service status |
| **System** | `/system/events/recent` | GET | Yes | Get recent events |
| **Health** | `/health` | GET | No | Health check (no auth) |
| **Health** | `/version` | GET | No | API version (no auth) |

**Total Endpoints**: 47

---

### Testing Checklist

**Unit Tests**:
- [ ] JWT token generation and validation
- [ ] Password hashing and verification
- [ ] Pydantic model validation
- [ ] Rate limiting logic
- [ ] EventResponseWaiter (correlation ID matching, timeout)
- [ ] Request/response serialization

**Integration Tests**:
- [ ] Authentication flow (login, token refresh)
- [ ] Automation toggle via API
- [ ] Manual position opening with risk validation
- [ ] Position close and modify
- [ ] Pending order creation and cancellation
- [ ] Indicator queries (all timeframes)
- [ ] Strategy configuration queries
- [ ] Strategy condition evaluation (real-time states)
- [ ] Risk config updates and persistence
- [ ] Account info queries
- [ ] System health and metrics
- [ ] Error handling (401, 400, 429, 503)

**Performance Tests**:
- [ ] Response time under normal load (< 200ms for reads)
- [ ] Response time under high load (100 concurrent requests)
- [ ] Rate limiting behavior
- [ ] EventBus throughput with API events
- [ ] Cache effectiveness (indicator queries)

**Security Tests**:
- [ ] Invalid token rejection (401)
- [ ] Expired token rejection (401)
- [ ] SQL injection attempts (N/A - no database)
- [ ] XSS attempts (sanitize error messages)
- [ ] Rate limit bypass attempts
- [ ] CORS policy enforcement

**User Acceptance Tests**:
- [ ] UAC-1: Open manual position via API
- [ ] UAC-2: View indicator values
- [ ] UAC-3: Toggle automation
- [ ] UAC-4: Update risk config and verify persistence
- [ ] UAC-5: Consistent error format
- [ ] UAC-6: API documentation at `/docs`

---

## 11. Dependencies

### Internal Dependencies
- Phase 1: Automated Trading Toggle (required - automation control events)
- EventBus (existing) - All API operations go through events
- EntryManager (existing) - Risk validation for manual trades
- MT5Client (existing) - Broker integration for positions/orders
- IndicatorCalculationService (existing) - Indicator value queries
- TradingOrchestrator (existing) - System health and metrics

### External Dependencies
- FastAPI 0.104+ (web framework)
- Uvicorn (ASGI server)
- Pydantic 2.x (request/response validation)
- python-jose[cryptography] (JWT tokens)
- passlib[bcrypt] (password hashing)
- python-multipart (file uploads, optional)
- slowapi (rate limiting middleware)

### Infrastructure Dependencies
- Docker (containerization)
- Port 8080 exposed (API access)
- SSL/TLS certificate (production HTTPS)
- Reverse proxy (optional - Nginx, Traefik)

---

## 12. Risks and Mitigations

### Risk 1: API Overwhelms EventBus
**Likelihood**: Medium
**Impact**: High (degrades trading system performance)
**Mitigation**:
- Implement aggressive rate limiting (20 write requests/min)
- Cache read-heavy endpoints (indicators, account info)
- Monitor EventBus queue depth, alert if > 100 pending events
- Run API in separate thread/process with priority lower than trading services

---

### Risk 2: Authentication Bypass
**Likelihood**: Low
**Impact**: Critical (unauthorized trading)
**Mitigation**:
- Use industry-standard JWT with strong secret key
- Implement token expiration (60 minutes)
- Log all authentication attempts
- Add IP whitelisting option (production feature)
- Regular security audits of auth code

---

### Risk 3: Risk Validation Bypass
**Likelihood**: Medium
**Impact**: High (trades exceed risk limits)
**Mitigation**:
- ALL manual trades go through EntryManager (no bypass path)
- Double-check risk limits at TradeExecutionService (defense in depth)
- Log all risk validation failures
- Add integration tests for risk limit enforcement
- Alert if manual trade risk > 2x configured limit (potential bug)

---

### Risk 4: API Downtime Affects Trading
**Likelihood**: Low (if same container), Medium (if separate container)
**Impact**: Low (trading continues, but no manual control)
**Mitigation**:
- Design: Trading system must work without API
- Monitor: API health independently from trading system
- Fallback: Keep Phase 1 file-based toggle as emergency backup
- Isolation: Run API in separate thread to prevent crashes affecting trading

---

### Risk 5: Indicator Cache Stale Data
**Likelihood**: Medium
**Impact**: Low (manual trades based on slightly outdated indicators)
**Mitigation**:
- Cache TTL: 5 seconds only (max staleness)
- Include timestamp in all indicator responses
- Document cache behavior in API docs
- Add cache bypass option (future: `?no_cache=true` query param)

---

### Risk 6: Configuration Updates Break System
**Likelihood**: Medium
**Impact**: High (invalid YAML crashes strategy loader)
**Mitigation**:
- Validate all risk config updates against Pydantic models
- Test YAML syntax before persisting (PyYAML safe_load)
- Create backup of YAML file before overwriting
- Add rollback endpoint: `POST /risk/config/rollback`
- Log all config changes with full before/after state

---

## 13. Future Enhancements (Post-Phase 2)

### Phase 3: Real-Time Updates
- WebSocket support for live indicator updates
- WebSocket for position updates (real-time profit/loss)
- Server-Sent Events (SSE) for event stream
- Notification system (email, Telegram, push notifications)

### Phase 4: Advanced Features
- Multi-user support with RBAC (roles: admin, trader, viewer)
- Advanced order types (OCO, bracket orders, trailing limit)
- Strategy builder API (create/edit strategies via API)
- Backtesting API (run backtests and retrieve results)
- Performance analytics API (win rate, Sharpe ratio, drawdown charts)

### Phase 5: Integration Ecosystem
- TradingView webhook integration (built-in)
- Telegram bot framework (pre-built bot for common operations)
- Discord bot framework
- Zapier/IFTTT integration
- Third-party signal provider integration

### Phase 6: Mobile & Advanced UI
- Native mobile app (React Native)
- Advanced web dashboard (React/Next.js)
- Real-time charting with indicator overlays
- Drag-and-drop strategy builder
- Live trade journal and analytics

---

## Appendix A: Example Usage Scenarios

### Scenario 1: Monitoring Strategy Conditions Before Manual Trade
```python
# Check strategy conditions before taking a manual trade

import requests

API_URL = "https://api.quantronaute.com"
TOKEN = "eyJhbGc..."  # JWT token from login

# Check current strategy conditions
response = requests.get(
    f"{API_URL}/api/v1/strategies/XAUUSD/anchors-transitions-and-htf-bias/conditions/entry",
    headers={"Authorization": f"Bearer {TOKEN}"}
)

data = response.json()

print(f"Strategy: {data['strategy']}")
print(f"Entry Type: {data['entry_type']}")
print(f"\nConditions:")
for cond in data['conditions']:
    status = "✓" if cond['state'] else "✗"
    print(f"  {status} {cond['condition']}")
    print(f"     Details: {cond['details']}")

print(f"\nWould Trigger: {data['would_trigger']}")

if data['would_trigger']:
    # All conditions met, open position via API
    response = requests.post(
        f"{API_URL}/api/v1/positions/open",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "symbol": "XAUUSD",
            "direction": "long",
            "strategy_name": "manual",
            "comment": "Manual trade - strategy conditions aligned"
        }
    )
    print("\nPosition opened:", response.json())
else:
    print(f"\nBlocking conditions: {data['blocking_conditions']}")
```

---

### Scenario 2: Dashboard Monitoring Indicators & Strategy States
```python
# Web dashboard polls API every 5 seconds for indicator updates

import requests
import time

API_URL = "https://api.quantronaute.com"
TOKEN = "eyJhbGc..."

while True:
    # Get current indicators for XAUUSD 15-minute
    response = requests.get(
        f"{API_URL}/api/v1/indicators/XAUUSD/15",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )

    data = response.json()

    # Display on dashboard
    print(f"XAUUSD 15-Min Indicators:")
    print(f"  RSI: {data['indicators']['RSI']['value']}")
    print(f"  MACD: {data['indicators']['MACD']['histogram']}")
    print(f"  ATR: {data['indicators']['ATR']['value']}")
    print(f"  Regime: {data['indicators']['regime']['value']}")
    print(f"  Price: {data['price']['close']}")
    print(f"  Updated: {data['timestamp']}")
    print("-" * 50)

    time.sleep(5)
```

---

### Scenario 3: Risk Manager Adjusting Parameters
```python
# Before high-impact news, reduce position sizing

import requests

API_URL = "https://api.quantronaute.com"
TOKEN = "eyJhbGc..."

# Check current risk config
response = requests.get(
    f"{API_URL}/api/v1/risk/config/XAUUSD/manual",
    headers={"Authorization": f"Bearer {TOKEN}"}
)
current_config = response.json()
print("Current position sizing:", current_config['position_sizing'])

# Update to 0.5% per trade (from 1%)
response = requests.post(
    f"{API_URL}/api/v1/risk/config/XAUUSD/manual/update",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={
        "position_sizing": {
            "type": "percentage",
            "value": 0.5
        }
    }
)

print("Updated config:", response.json())

# After news passes, revert to 1%
# ... (similar POST request with value: 1.0)
```

---

### Scenario 4: Analyzing Why Strategy Didn't Trigger
```python
# Investigate why your strategy didn't generate an entry signal

import requests

API_URL = "https://api.quantronaute.com"
TOKEN = "eyJhbGc..."  # JWT token

# Get full strategy condition evaluation
response = requests.get(
    f"{API_URL}/api/v1/strategies/XAUUSD/anchors-transitions-and-htf-bias/conditions",
    headers={"Authorization": f"Bearer {TOKEN}"}
)

data = response.json()

print(f"Strategy: {data['strategy']}")
print(f"Timestamp: {data['timestamp']}")
print(f"\n{'='*60}")

# Check entry conditions
print("\nENTRY CONDITIONS (Long):")
print(f"Mode: {data['entry']['long']['mode']} (all must be true)")
print(f"\nConditions:")

for i, cond in enumerate(data['entry']['long']['conditions'], 1):
    result = "✓ PASS" if cond['state'] else "✗ FAIL"
    print(f"\n{i}. {result}")
    print(f"   Condition: {cond['condition']['signal']} {cond['condition']['operator']} {cond['condition']['value']}")
    print(f"   Timeframe: {cond['condition']['timeframe']}")
    print(f"   Evaluation:")
    print(f"     Left:  {cond['evaluation']['left']}")
    print(f"     Right: {cond['evaluation']['right']}")
    print(f"     Result: {cond['evaluation']['result']}")

print(f"\n{'='*60}")
print(f"All Conditions Met: {data['entry']['long']['all_conditions_met']}")
print(f"Would Trigger Entry: {data['entry']['long']['would_trigger_entry']}")

# Check overall status
print(f"\n{'='*60}")
print("OVERALL STATUS:")
print(f"  Can Enter Long:  {data['overall_status']['can_enter_long']}")
print(f"  Can Enter Short: {data['overall_status']['can_enter_short']}")
print(f"  Should Exit Long:  {data['overall_status']['should_exit_long']}")
print(f"  Should Exit Short: {data['overall_status']['should_exit_short']}")
```

---

## Appendix B: Python SDK

**File**: `docs/api/sdk/quantronaute_api_client.py`

```python
"""
Quantronaute Trading API Client SDK
Simple wrapper around requests library for easy API access
"""

import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta


class QuantronauteAPI:
    """Client for Quantronaute Trading API"""

    def __init__(self, base_url: str, username: str = None, password: str = None, token: str = None):
        """
        Initialize API client

        Args:
            base_url: API base URL (e.g., "https://api.quantronaute.com")
            username: Username for authentication
            password: Password for authentication
            token: JWT token (if already authenticated)
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.token_expiry = None

        if username and password and not token:
            self.login(username, password)

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login and get JWT token"""
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data['access_token']
        self.token_expiry = datetime.now() + timedelta(minutes=data.get('expires_in', 60))
        return data

    def _headers(self) -> Dict[str, str]:
        """Get request headers with auth token"""
        if not self.token:
            raise ValueError("Not authenticated. Call login() first.")
        return {"Authorization": f"Bearer {self.token}"}

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request"""
        response = requests.request(
            method,
            f"{self.base_url}/api/v1{endpoint}",
            headers=self._headers(),
            **kwargs
        )
        response.raise_for_status()
        return response.json()

    # Automation
    def enable_automation(self, reason: str = None) -> Dict[str, Any]:
        """Enable automated trading"""
        return self._request("POST", "/automation/enable", json={"reason": reason})

    def disable_automation(self, reason: str = None) -> Dict[str, Any]:
        """Disable automated trading"""
        return self._request("POST", "/automation/disable", json={"reason": reason})

    def get_automation_status(self) -> Dict[str, Any]:
        """Get automation status"""
        return self._request("GET", "/automation/status")

    # Positions
    def get_positions(self, symbol: str = None) -> Dict[str, Any]:
        """Get open positions"""
        if symbol:
            return self._request("GET", f"/positions/{symbol}")
        return self._request("GET", "/positions")

    def open_position(
        self,
        symbol: str,
        direction: str,
        strategy_name: str = "manual",
        volume: float = None,
        entry_price: float = None,
        stop_loss: float = None,
        take_profit: float = None,
        comment: str = ""
    ) -> Dict[str, Any]:
        """Open a new position"""
        return self._request("POST", "/positions/open", json={
            "symbol": symbol,
            "direction": direction,
            "strategy_name": strategy_name,
            "volume": volume,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "comment": comment
        })

    def close_position(self, symbol: str, ticket: int, volume: float = None, reason: str = None) -> Dict[str, Any]:
        """Close a position"""
        return self._request("POST", f"/positions/{symbol}/{ticket}/close", json={
            "volume": volume,
            "reason": reason
        })

    def modify_position(self, symbol: str, ticket: int, stop_loss: float = None, take_profit: float = None) -> Dict[str, Any]:
        """Modify position SL/TP"""
        return self._request("POST", f"/positions/{symbol}/{ticket}/modify", json={
            "stop_loss": stop_loss,
            "take_profit": take_profit
        })

    # Indicators
    def get_indicators(self, symbol: str, timeframe: str = None, indicator: str = None) -> Dict[str, Any]:
        """Get indicator values"""
        if indicator:
            return self._request("GET", f"/indicators/{symbol}/{timeframe}/{indicator}")
        elif timeframe:
            return self._request("GET", f"/indicators/{symbol}/{timeframe}")
        return self._request("GET", f"/indicators/{symbol}")

    # Strategies
    def get_strategies(self, symbol: str = None) -> Dict[str, Any]:
        """Get all strategies or strategies for a symbol"""
        if symbol:
            return self._request("GET", f"/strategies/{symbol}")
        return self._request("GET", "/strategies")

    def get_strategy_config(self, symbol: str, strategy_name: str) -> Dict[str, Any]:
        """Get strategy configuration"""
        return self._request("GET", f"/strategies/{symbol}/{strategy_name}")

    def get_strategy_conditions(self, symbol: str, strategy_name: str, condition_type: str = None) -> Dict[str, Any]:
        """
        Get real-time strategy condition evaluation

        Args:
            symbol: Trading symbol
            strategy_name: Strategy name
            condition_type: Optional - 'entry' or 'exit' to filter conditions
        """
        if condition_type:
            return self._request("GET", f"/strategies/{symbol}/{strategy_name}/conditions/{condition_type}")
        return self._request("GET", f"/strategies/{symbol}/{strategy_name}/conditions")

    # Risk
    def get_risk_config(self, symbol: str = None, strategy: str = None) -> Dict[str, Any]:
        """Get risk configuration"""
        if strategy:
            return self._request("GET", f"/risk/config/{symbol}/{strategy}")
        elif symbol:
            return self._request("GET", f"/risk/config/{symbol}")
        return self._request("GET", "/risk/config")

    def update_risk_config(self, symbol: str, strategy: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update risk configuration"""
        return self._request("POST", f"/risk/config/{symbol}/{strategy}/update", json=config)

    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk status"""
        return self._request("GET", "/risk/status")

    # Account
    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary"""
        return self._request("GET", "/account/summary")

    def get_account_balance(self) -> float:
        """Get account balance"""
        return self._request("GET", "/account/balance")['balance']

    # System
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health"""
        return self._request("GET", "/system/health")

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        return self._request("GET", "/system/metrics")


# Example usage
if __name__ == "__main__":
    api = QuantronauteAPI(
        base_url="http://localhost:8080",
        username="trader",
        password="your-password"
    )

    # Get account summary
    summary = api.get_account_summary()
    print(f"Balance: ${summary['balance']:,.2f}")

    # Get indicators
    indicators = api.get_indicators("XAUUSD", "15")
    print(f"RSI: {indicators['indicators']['RSI']['value']}")

    # Check strategy conditions before trading
    conditions = api.get_strategy_conditions(
        symbol="XAUUSD",
        strategy_name="anchors-transitions-and-htf-bias",
        condition_type="entry"
    )
    print(f"Would trigger: {conditions['would_trigger']}")

    if conditions['would_trigger']:
        # Open position if conditions met
        position = api.open_position(
            symbol="XAUUSD",
            direction="long",
            comment="SDK test trade - conditions aligned"
        )
        print(f"Position opened: {position['position']['ticket']}")
    else:
        print(f"Blocking conditions: {conditions['blocking_conditions']}")
```

---

## Document Revision History

| Version | Date       | Changes                          | Author |
|---------|------------|----------------------------------|--------|
| 1.0     | 2025-11-17 | Initial PRD created              | PRD Generator |

---

**END OF DOCUMENT**
