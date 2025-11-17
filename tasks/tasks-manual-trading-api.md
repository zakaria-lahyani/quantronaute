# Implementation Tasks: Manual Trading API (Phase 2)

**Feature**: Manual Trading API
**PRD**: `prd-manual-trading-api.md`
**Dependencies**: Phase 1 - Automated Trading Toggle (completed)
**Target**: RESTful API for manual trading control and system monitoring

---

## Implementation Phases

This implementation is broken into logical phases to allow incremental delivery and testing.

### Phase A: Core API Infrastructure (Foundation)
- Set up FastAPI application structure
- Implement authentication (JWT)
- Create base API service integrated with EventBus
- Establish request-response pattern with correlation IDs

### Phase B: Critical Trading Operations (Smart Manual Trading)
- Automation control endpoints (replace file-based toggle)
- Smart position management (one-click open/close with automatic calculations)
- Smart order placement (system handles sizing, SL/TP, scaling)
- Basic error handling and validation

### Phase C: Monitoring & Analytics
- Indicator monitoring endpoints
- Strategy monitoring endpoints (new - condition evaluation)
- Account information endpoints
- System health and metrics endpoints

### Phase D: Configuration Management (NEW - Full Config API)
- Strategy configuration endpoints (view/edit YAML files)
- Broker configuration endpoints (view/edit .env.broker)
- Configuration validation and backup system
- Config reload without restart
- Template management

### Phase E: Polish & Production Readiness
- Rate limiting and security hardening
- Comprehensive documentation
- Python SDK
- Integration testing
- Performance testing

---

## Task Breakdown

### 0.0: Project Setup and Planning ✅

**Goal**: Prepare for API implementation

- [x] 0.1: Review PRD and create task breakdown
- [x] 0.2: Create feature branch: `feature/manual-trading-api`
- [x] 0.3: Update dependencies in requirements.txt (FastAPI, Uvicorn, python-jose, passlib, slowapi)
- [x] 0.4: Create API project structure (`app/api/` directory tree)

**Status**: COMPLETED
**Date**: 2025-11-17

**Files to create**:
```
app/api/
├── __init__.py
├── main.py
├── service.py
├── auth.py
├── dependencies.py
├── middleware.py
├── events.py
├── models/
│   ├── __init__.py
│   ├── requests.py
│   ├── responses.py
│   └── auth.py
├── routers/
│   ├── __init__.py
│   ├── automation.py
│   ├── positions.py
│   ├── orders.py
│   ├── indicators.py
│   ├── strategies.py
│   ├── risk.py
│   ├── account.py
│   └── system.py
└── utils/
    ├── __init__.py
    ├── correlation.py
    ├── event_waiter.py
    ├── cache.py
    └── rate_limit.py
```

---

### 1.0: Authentication System (JWT) ✅

**Goal**: Secure the API with token-based authentication

**Status**: COMPLETED
**Date**: 2025-11-17

**Tasks**:
- [x] 1.1: Implement password hashing with bcrypt (`app/api/auth.py`)
- [x] 1.2: Implement JWT token generation and validation
- [x] 1.3: Create authentication Pydantic models (`app/api/models/auth.py`)
- [x] 1.4: Implement `/auth/login` endpoint (POST - username/password → JWT)
- [x] 1.5: Implement `/auth/refresh` endpoint (POST - refresh token)
- [x] 1.6: Create OAuth2PasswordBearer dependency for protected endpoints
- [x] 1.7: Add credential storage (environment variables + JSON file fallback)
- [x] 1.8: Unit tests for authentication (17 tests passing)
- [x] 1.9: Fix bcrypt compatibility issues with Python 3.13
- [x] 1.10: Create Docker deployment configuration
- [x] 1.11: Create password generation script
- [x] 1.12: Write deployment documentation

**Success Criteria**:
- User can login with username/password and receive JWT token
- Token validation works correctly
- Invalid/expired tokens are rejected with 401
- Tokens expire after configured time (60 minutes)

**Environment Variables**:
```bash
API_SECRET_KEY={generated-256-bit-secret}
API_ACCESS_TOKEN_EXPIRE_MINUTES=60
API_USERNAME=trader
API_PASSWORD_HASH={bcrypt-hash}
```

---

### 2.0: Core API Service & EventBus Integration ✅

**Goal**: Create APIService that integrates with existing EventBus architecture

**Status**: COMPLETED
**Date**: 2025-11-17

**Tasks**:
- [x] 2.1: Create `APIService` class with EventBus integration (`app/api/service.py`)
- [x] 2.2: Implement FastAPI lifespan for startup/shutdown (`app/api/main.py`)
- [x] 2.3: Implement trading signal methods (trigger_entry_signal, trigger_exit_signal)
- [x] 2.4: Implement automation control methods (enable/disable/query)
- [x] 2.5: Implement system monitoring methods (metrics, status, event history)
- [x] 2.6: Add async lifecycle management (start/stop)
- [x] 2.7: Create get_api_service dependency injection (`app/api/dependencies.py`)
- [x] 2.8: Integrate EventBus initialization in lifespan
- [x] 2.9: Add service status to /health endpoint
- [ ] 2.10: Unit tests for APIService
- [ ] 2.11: Implement EventResponseWaiter utility (deferred to specific endpoints)
- [ ] 2.12: Create correlation ID tracking system (deferred to specific endpoints)

**Success Criteria**:
- APIService starts/stops with FastAPI lifespan
- API can publish events to EventBus
- API can wait for response events with correlation IDs
- Timeouts work correctly (return 503 after 5s)

**Configuration**:
```bash
API_ENABLED=true
API_HOST=0.0.0.0
API_PORT=8080
API_CORS_ORIGINS=["http://localhost:3000"]
```

---

### 3.0: Automation Control Endpoints ✅

**Goal**: Replace Phase 1 file-based toggle with API endpoints

**Status**: COMPLETED
**Date**: 2025-11-17

**Tasks**:
- [x] 3.1: Create automation router (`app/api/routers/automation.py`)
- [x] 3.2: Implement `POST /automation/enable` endpoint
- [x] 3.3: Implement `POST /automation/disable` endpoint
- [x] 3.4: Implement `GET /automation/status` endpoint
- [x] 3.5: Create request/response models (`app/api/models/requests.py`, `responses.py`)
- [x] 3.6: Reuse existing `ToggleAutomationEvent` from Phase 1 (using AutomationEnabledEvent/DisabledEvent)
- [ ] 3.7: Add rate limiting (10 requests/minute) - Deferred to Task 11.0
- [ ] 3.8: Integration tests for automation endpoints - Deferred to Task 14.0

**API Specification**:
```
POST /automation/enable
POST /automation/disable
GET  /automation/status
```

**Success Criteria**:
- ✓ Automation can be toggled via API
- ✓ State changes are reflected through EventBus
- Rate limiting - Pending Task 11.0
- ✓ Response includes current state and user tracking

**Implementation**:
- File: [app/api/routers/automation.py](app/api/routers/automation.py)
- Endpoints integrated with APIService
- JWT authentication required on all endpoints
- User tracking in responses (triggered_by field)

---

### 4.0: Smart Position Management Endpoints

**Goal**: Enable one-click position management with automatic risk calculations

**Philosophy**: User provides ONLY symbol + direction. System handles everything else.

**Tasks**:
- [ ] 4.1: Create positions router (`app/api/routers/positions.py`)
- [ ] 4.2: Implement `GET /positions` (list all positions)
- [ ] 4.3: Implement `GET /positions/{symbol}` (list by symbol)
- [ ] 4.4: Implement `GET /positions/{ticket}` (get specific position by ticket)
- [ ] 4.5: Implement `POST /positions/open` (smart position opening)
  - Request: symbol, direction, strategy_name (optional), risk_override (optional)
  - System calculates: entry price (market), position size, SL (ATR-based), TP (with scaling), validates risk
  - Integrate with EntryManager for risk calculation and validation
  - Create `OpenSmartPositionCommand` event
  - TradeExecutionService handles command and publishes `OrderPlacedEvent`
- [ ] 4.6: Implement `POST /positions/{ticket}/close` (smart close)
  - Support full or partial closes (volume parameter optional)
  - System handles close at market price
- [ ] 4.7: Implement `POST /positions/{ticket}/modify` (modify SL/TP)
- [ ] 4.8: Implement `POST /positions/close-all` (close all positions, optional symbol filter)
- [ ] 4.9: Create comprehensive request/response models
- [ ] 4.10: Add risk validation error responses (400 Bad Request)
- [ ] 4.11: Update TradeExecutionService to handle smart position command events
- [ ] 4.12: Integration tests for position operations

**Success Criteria**:
- Trader specifies ONLY symbol + direction, system handles rest
- Position sizing calculated by EntryManager based on risk config
- SL calculated using ATR or configured method
- TP calculated with proper scaling if configured
- Risk limits enforced (daily loss, max positions, position sizing rules)
- Positions can be closed and modified
- Clear error messages for validation failures (e.g., "Daily loss limit would be exceeded: $X/$Y")

**Example Smart Request**:
```json
POST /positions/open
{
  "symbol": "XAUUSD",
  "direction": "long"
}

Response:
{
  "success": true,
  "orders": [
    {"ticket": 12345, "volume": 0.3, "entry": 2650.25, "sl": 2640.0, "tp": 2670.0},
    {"ticket": 12346, "volume": 0.2, "entry": 2650.25, "sl": 2640.0, "tp": 2680.0}
  ],
  "calculations": {
    "risk_amount": 100.0,
    "risk_percent": 1.0,
    "total_volume": 0.5,
    "sl_distance": 10.25
  }
}
```

---

### 5.0: Manual Trading Signal Endpoints ✅

**Goal**: Enable manual trading signal triggers with automatic calculations

**Philosophy**: User provides signal (symbol + direction), system handles everything else through standard signal pipeline.

**Status**: COMPLETED
**Date**: 2025-11-17

**Tasks**:
- [x] 5.1: Create signals router (`app/api/routers/orders.py`)
- [x] 5.2: Implement `POST /signals/entry` (trigger manual entry signal)
  - Request: symbol, direction
  - Publishes EntrySignalEvent with strategy_name="manual"
  - System calculates: position size, SL, TP, scaling (via EntryManager)
  - Entry price is MARKET (current market price)
- [x] 5.3: Implement `POST /signals/exit` (trigger manual exit signal)
  - Request: symbol, direction, reason
  - Publishes ExitSignalEvent with strategy_name="manual"
- [x] 5.4: Implement `GET /signals` (placeholder for future pending orders list)
- [x] 5.5: Implement `DELETE /signals/{ticket}` (placeholder for order cancellation)
- [x] 5.6: Add input validation (direction must be "long" or "short")
- [x] 5.7: Add authentication to all endpoints
- [x] 5.8: Add user tracking in responses
- [x] 5.9: Create request/response models (TriggerEntrySignalRequest, TriggerExitSignalRequest)
- [ ] 5.10: Integration tests for signal operations - Deferred to Task 14.0

**Success Criteria**:
- ✓ Manual signals can be triggered with one click (symbol + direction only)
- ✓ Signals flow through identical pipeline as automated strategies
- ✓ System handles all calculations (sizing, SL, TP, scaling) via EntryManager
- ✓ Input validation with clear error messages
- ✓ User tracking for all signal triggers

**Implementation**:
- File: [app/api/routers/orders.py](app/api/routers/orders.py)
- Signal-based approach: API publishes EntrySignalEvent/ExitSignalEvent
- strategy_name="manual" differentiates from automated strategies
- Configuration from manual.yaml files per symbol
- Comprehensive docstrings with curl examples

**Note**: Manual signals execute at market price via standard trading pipeline. No pending order support - this is intentional for simplicity and consistency with signal-based architecture.

---

### 6.0: Indicator Monitoring Endpoints

**Goal**: Provide read-only access to current indicator values

**Tasks**:
- [ ] 6.1: Create indicators router (`app/api/routers/indicators.py`)
- [ ] 6.2: Implement `GET /indicators/{symbol}` (all timeframes)
- [ ] 6.3: Implement `GET /indicators/{symbol}/{timeframe}` (specific timeframe)
- [ ] 6.4: Implement `GET /indicators/{symbol}/{timeframe}/{indicator}` (specific indicator)
- [ ] 6.5: Implement `GET /indicators/config/{symbol}` (indicator configuration)
- [ ] 6.6: Create `QueryIndicatorsCommand` and `IndicatorsResponseEvent`
- [ ] 6.7: Update IndicatorCalculationService to handle query events
- [ ] 6.8: Implement 5-second cache for indicator values (`app/api/utils/cache.py`)
- [ ] 6.9: Create request/response models
- [ ] 6.10: Integration tests for indicator queries

**Success Criteria**:
- Current indicator values can be queried via API
- Response includes timestamp for data freshness
- Caching reduces load on IndicatorCalculationService
- Response time < 300ms for cached, < 800ms for uncached

---

### 7.0: Strategy Monitoring Endpoints (NEW Feature)

**Goal**: Provide real-time strategy condition evaluation

**Tasks**:
- [ ] 7.1: Create strategies router (`app/api/routers/strategies.py`)
- [ ] 7.2: Implement `GET /strategies` (list all strategies)
- [ ] 7.3: Implement `GET /strategies/{symbol}` (list by symbol)
- [ ] 7.4: Implement `GET /strategies/{symbol}/{name}` (get strategy config)
- [ ] 7.5: Implement `GET /strategies/{symbol}/{name}/conditions` (real-time condition evaluation)
- [ ] 7.6: Implement `GET /strategies/{symbol}/{name}/conditions/entry` (entry conditions only)
- [ ] 7.7: Implement `GET /strategies/{symbol}/{name}/conditions/exit` (exit conditions only)
- [ ] 7.8: Create `QueryStrategyConditionsCommand` and `StrategyConditionsResponseEvent`
- [ ] 7.9: Update StrategyEvaluationService to:
  - Handle query commands
  - Evaluate each condition individually
  - Return condition definition + boolean state + actual values
  - Include "why didn't it trigger" analysis
- [ ] 7.10: Create comprehensive response models showing:
  - Each condition with true/false state
  - Actual values being compared (e.g., close=2650.25, previous_close=2649.50)
  - Overall "would trigger" status
  - Blocking conditions (which conditions failed)
- [ ] 7.11: Integration tests for strategy condition queries

**Success Criteria**:
- Traders can see real-time evaluation of each strategy condition
- Response shows why a strategy didn't trigger (which conditions failed)
- Actual indicator/price values included for manual verification
- Response time < 500ms

**This is a key differentiator** - allows traders to understand strategy logic in real-time!

---

### 8.0: Configuration Management Endpoints (NEW - Comprehensive Config API)

**Goal**: View and modify all trading configurations via API

**Philosophy**: The API exposes the configuration layer, allowing runtime modification
of strategy configs (.yaml) and broker settings (.env.broker).

**Configuration Hierarchy**:
1. **Strategy Configs** (`configs/{broker}/strategies/{symbol}/{strategy}.yaml`)
   - Risk parameters (position_sizing, SL, TP)
   - Optional scaling overrides
   - Strategy-specific settings

2. **Broker Configs** (`configs/{broker}/.env.broker`)
   - Symbol-specific scaling (XAUUSD_POSITION_SPLIT, SCALING_TYPE, etc.)
   - Account-level risk limits (DAILY_LOSS_LIMIT)
   - Trading parameters (PIP_VALUE, ENTRY_SPACING, etc.)

**Tasks**:
- [ ] 8.1: Create config router (`app/api/routers/config.py`)

**8.1: Strategy Configuration Endpoints**
- [ ] 8.2: Implement `GET /config/strategies` (list all strategies across all symbols)
- [ ] 8.3: Implement `GET /config/strategies/{symbol}` (list strategies for a symbol)
- [ ] 8.4: Implement `GET /config/strategies/{symbol}/{strategy}` (get full strategy config)
- [ ] 8.5: Implement `GET /config/strategies/{symbol}/{strategy}/risk` (get risk section only)
- [ ] 8.6: Implement `PUT /config/strategies/{symbol}/{strategy}/risk` (update risk section)
  - Request body: Complete risk config object
  - Validates: position_sizing, sl, tp, optional scaling
  - Creates backup before modifying
  - Saves to YAML file
- [ ] 8.7: Implement `PATCH /config/strategies/{symbol}/{strategy}/risk` (partial risk update)
  - Update only specified fields (e.g., just position_sizing.value)
- [ ] 8.8: Implement `POST /config/strategies/{symbol}` (create new strategy config)
  - Use template from broker-template/strategies/manual-template.yaml
  - Requires: name, risk config

**8.2: Broker Configuration Endpoints**
- [ ] 8.9: Implement `GET /config/broker` (all broker settings from .env.broker)
- [ ] 8.10: Implement `GET /config/broker/symbols` (list configured symbols)
- [ ] 8.11: Implement `GET /config/broker/symbol/{symbol}` (symbol-specific settings)
  - Returns: PIP_VALUE, POSITION_SPLIT, SCALING_TYPE, ENTRY_SPACING, RISK_PER_GROUP
- [ ] 8.12: Implement `PUT /config/broker/symbol/{symbol}` (update symbol settings)
  - Updates .env.broker file
  - Validates: POSITION_SPLIT > 0, SCALING_TYPE in [equal, progressive, regressive]
  - Creates backup before modifying
- [ ] 8.13: Implement `GET /config/broker/risk-limits` (account-level risk limits)
  - Returns: DAILY_LOSS_LIMIT, NEWS_RESTRICTION_DURATION, etc.
- [ ] 8.14: Implement `PUT /config/broker/risk-limits` (update risk limits)

**8.3: Configuration Validation & Persistence**
- [ ] 8.15: Create configuration validation service
  - Validate YAML structure
  - Validate risk parameter types and values
  - Validate .env.broker key-value pairs
- [ ] 8.16: Implement backup system
  - Create timestamped backups before modifications
  - Keep last 10 backups
  - Provide rollback endpoint
- [ ] 8.17: Implement `POST /config/reload` (reload configs without restart)
  - Publishes ConfigReloadEvent
  - Services reload their configurations
- [ ] 8.18: Implement `GET /config/backups` (list available backups)
- [ ] 8.19: Implement `POST /config/rollback/{backup_id}` (restore from backup)

**8.4: Configuration Templates**
- [ ] 8.20: Implement `GET /config/templates/strategy` (get strategy template)
- [ ] 8.21: Implement `GET /config/templates/strategy/examples` (example configs)
  - Conservative, Moderate, Aggressive examples

**Success Criteria**:
- All strategy and broker configs accessible via API
- Modifications persist to YAML/.env files
- Backup system prevents config loss
- Validation prevents invalid configs
- Changes can be applied without system restart (where possible)
- Clear error messages for validation failures

**API Examples**:

```bash
# View manual strategy config for XAUUSD
GET /config/strategies/XAUUSD/manual

Response:
{
  "name": "manual",
  "risk": {
    "position_sizing": {"type": "fixed", "value": 0.5},
    "sl": {"type": "monetary", "value": 500.0},
    "tp": {
      "type": "multi_target",
      "targets": [
        {"value": 1.0, "percent": 50, "move_stop": true},
        {"value": 2.0, "percent": 50, "move_stop": false}
      ]
    }
  }
}

# Update manual strategy risk
PUT /config/strategies/XAUUSD/manual/risk
{
  "position_sizing": {"type": "percentage", "value": 1.0},
  "sl": {"type": "atr", "value": 1.5},
  "tp": {"type": "rr", "value": 2.0}
}

# View XAUUSD broker-level scaling settings
GET /config/broker/symbol/XAUUSD

Response:
{
  "symbol": "XAUUSD",
  "pip_value": 100,
  "position_split": 4,
  "scaling_type": "equal",
  "entry_spacing": 0.1,
  "risk_per_group": 1000
}

# Update XAUUSD scaling
PUT /config/broker/symbol/XAUUSD
{
  "position_split": 2,
  "scaling_type": "progressive",
  "entry_spacing": 0.2
}
```

---

### 9.0: Account & System Monitoring Endpoints

**Goal**: Provide account information and system health visibility

**Tasks**:
- [ ] 9.1: Create account router (`app/api/routers/account.py`)
- [ ] 9.2: Implement `GET /account/summary` (balance, equity, profit, positions)
- [ ] 9.3: Implement `GET /account/balance`
- [ ] 9.4: Implement `GET /account/equity`
- [ ] 9.5: Implement `GET /account/margin`
- [ ] 9.6: Implement 5-second cache for account info
- [ ] 9.7: Create system router (`app/api/routers/system.py`)
- [ ] 9.8: Implement `GET /system/health` (service status, broker connection)
- [ ] 9.9: Implement `GET /system/metrics` (event counts, processing times)
- [ ] 9.10: Implement `GET /system/services` (individual service status)
- [ ] 9.11: Implement `GET /health` (no auth, for monitoring)
- [ ] 9.12: Implement `GET /version` (no auth, API version info)
- [ ] 9.13: Integration with existing MT5Client and Orchestrator metrics
- [ ] 9.14: Integration tests for account and system endpoints

**Success Criteria**:
- Account information accessible via API
- System health reflects true status (services, broker, EventBus)
- Health endpoint works without authentication (for monitoring tools)
- Caching reduces broker API load

---

### 10.0: Error Handling & Validation

**Goal**: Consistent error responses and comprehensive validation

**Tasks**:
- [ ] 10.1: Create error response models (`app/api/models/responses.py`)
- [ ] 10.2: Implement global exception handler middleware
- [ ] 10.3: Define error codes for common failures
- [ ] 10.4: Add field-level validation error responses
- [ ] 10.5: Implement proper HTTP status codes (400, 401, 403, 404, 429, 503)
- [ ] 10.6: Add request/response logging (sanitize sensitive data)
- [ ] 10.7: Add request ID tracking (X-Request-ID header)
- [ ] 10.8: Create consistent error format:
  ```json
  {
    "status": "error",
    "error": "Human-readable message",
    "error_code": "ERROR_CODE",
    "details": {},
    "timestamp": "2025-11-17T10:30:00Z"
  }
  ```
- [ ] 10.9: Unit tests for error handling
- [ ] 10.10: Integration tests for various error scenarios

**Success Criteria**:
- All errors return consistent format
- Field-level validation errors are clear
- Request IDs can be traced in logs
- Sensitive data is never logged

---

### 11.0: Rate Limiting & Security

**Goal**: Protect API from abuse and ensure security

**Tasks**:
- [ ] 11.1: Implement rate limiting middleware (`app/api/utils/rate_limit.py`)
- [ ] 11.2: Configure rate limits per endpoint category:
  - Read endpoints: 60 req/min
  - Write endpoints: 20 req/min
  - Automation toggle: 10 req/min
  - Login: 5 req/min
- [ ] 11.3: Return 429 Too Many Requests with retry-after header
- [ ] 11.4: Add CORS middleware (configurable origins)
- [ ] 11.5: Enforce HTTPS in production
- [ ] 11.6: Add request/response size limits
- [ ] 11.7: Implement authentication attempt logging
- [ ] 11.8: Add IP whitelisting option (configuration-based)
- [ ] 11.9: Security audit of authentication code
- [ ] 11.10: Load testing (100 concurrent requests)

**Success Criteria**:
- Rate limits prevent API abuse
- CORS configured for web dashboard access
- Authentication attempts are logged
- API handles high load gracefully

---

### 12.0: API Documentation

**Goal**: Comprehensive, auto-generated documentation

**Tasks**:
- [ ] 12.1: Configure FastAPI OpenAPI metadata (title, description, version)
- [ ] 12.2: Add docstrings to all endpoints
- [ ] 12.3: Add request/response examples to Pydantic models
- [ ] 12.4: Verify Swagger UI at `/docs`
- [ ] 12.5: Verify ReDoc UI at `/redoc`
- [ ] 12.6: Create markdown documentation:
  - `docs/api/README.md` - API overview
  - `docs/api/authentication.md` - Auth guide
  - `docs/api/endpoints/automation.md`
  - `docs/api/endpoints/positions.md`
  - `docs/api/endpoints/orders.md`
  - `docs/api/endpoints/indicators.md`
  - `docs/api/endpoints/strategies.md`
  - `docs/api/endpoints/risk.md`
  - `docs/api/endpoints/account.md`
  - `docs/api/endpoints/system.md`
- [ ] 12.7: Create example code in multiple languages (Python, cURL, JavaScript)
- [ ] 12.8: Document common use cases
- [ ] 12.9: Update main README.md with API section

**Success Criteria**:
- Auto-generated docs are complete and accurate
- All endpoints have examples
- Markdown docs cover all common use cases
- README updated with API quick start

---

### 13.0: Python SDK

**Goal**: Easy-to-use Python client library

**Tasks**:
- [ ] 13.1: Create SDK file (`docs/api/sdk/quantronaute_api_client.py`)
- [ ] 13.2: Implement `QuantronauteAPI` class (thin wrapper around requests)
- [ ] 13.3: Add methods for all endpoints:
  - Authentication (login, refresh)
  - Automation control
  - Position management
  - Order management
  - Indicator queries
  - Strategy queries
  - Risk configuration
  - Account info
  - System monitoring
- [ ] 13.4: Add token auto-refresh on expiration
- [ ] 13.5: Add error handling and retries
- [ ] 13.6: Create SDK usage examples
- [ ] 13.7: Add SDK tests (against running API)

**Success Criteria**:
- SDK simplifies API usage
- Token management is automatic
- Examples demonstrate common workflows
- SDK is well-documented

---

### 14.0: Integration Testing

**Goal**: Comprehensive end-to-end tests

**Tasks**:
- [ ] 14.1: Create integration test suite (`tests/api/`)
- [ ] 14.2: Test authentication flow (login, token validation, expiration)
- [ ] 14.3: Test automation toggle via API
- [ ] 14.4: Test manual position opening with risk validation
  - Valid trades execute successfully
  - Invalid trades rejected with clear errors
  - Risk limits enforced
- [ ] 14.5: Test position close and modify
- [ ] 14.6: Test order creation and cancellation
- [ ] 14.7: Test indicator queries (caching behavior)
- [ ] 14.8: Test strategy condition queries
- [ ] 14.9: Test risk config updates and persistence
- [ ] 14.10: Test account and system monitoring
- [ ] 14.11: Test error scenarios (invalid tokens, validation errors, rate limits)
- [ ] 14.12: Test concurrent requests (race conditions)
- [ ] 14.13: Performance testing (response times, throughput)

**Success Criteria**:
- All UAC scenarios pass (UAC-1 through UAC-6 from PRD)
- Read endpoints < 200ms (p95)
- Write endpoints < 1s (p95)
- API handles 100 concurrent requests without errors
- Rate limiting works correctly

---

### 15.0: Docker & Deployment

**Goal**: Production-ready deployment configuration

**Tasks**:
- [ ] 15.1: Update Dockerfile to include API dependencies
- [ ] 15.2: Update docker-compose.yml to expose API port (8080)
- [ ] 15.3: Add API environment variables to broker config templates
- [ ] 15.4: Create API credentials file template (`config/api_credentials.json.example`)
- [ ] 15.5: Update `.gitignore` to exclude credentials and secrets
- [ ] 15.6: Add volume mappings for config files
- [ ] 15.7: Create production deployment guide
- [ ] 15.8: Test full Docker deployment with API enabled
- [ ] 15.9: Create HTTPS/TLS setup guide (reverse proxy)
- [ ] 15.10: Document secret management (JWT secret key)

**Success Criteria**:
- API runs in Docker alongside trading system
- Configuration is externalized
- Secrets are properly managed
- Production deployment guide is clear

---

## Testing Strategy

### Unit Tests
- Authentication (JWT, password hashing)
- Pydantic model validation
- EventResponseWaiter (correlation ID, timeout)
- Rate limiting logic
- Cache implementation

### Integration Tests
- Full request-response cycles
- EventBus integration
- Risk validation
- Config persistence
- Error handling
- Rate limiting behavior

### Performance Tests
- Response time under normal load
- Response time under high load (100 concurrent)
- Cache effectiveness
- EventBus throughput

### Security Tests
- Invalid/expired token rejection
- Rate limit enforcement
- CORS policy
- Input validation (XSS, injection)

---

## Success Metrics

**Functional**:
- All 47 endpoints implemented and working
- API response times meet targets (< 200ms reads, < 1s writes)
- Manual trades execute with proper risk validation
- Strategy condition evaluation works in real-time

**Operational**:
- API uptime > 99.5%
- Authentication failure rate < 1%
- Rate limit hit rate < 5%
- Event timeout rate < 0.1%

**User Acceptance** (from PRD):
- UAC-1: Manual position respects risk management ✓
- UAC-2: Indicators query < 1 second ✓
- UAC-3: Automation toggle reflected within 2 seconds ✓
- UAC-4: Risk config updates persist ✓
- UAC-5: Consistent error format ✓
- UAC-6: Interactive docs at `/docs` ✓

---

## Dependencies

**External**:
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
slowapi>=0.1.9
```

**Internal**:
- Phase 1 automation infrastructure (ToggleAutomationEvent, AutomationStateManager)
- EventBus
- EntryManager (risk validation)
- MT5Client (positions, orders, account)
- IndicatorCalculationService
- StrategyEvaluationService
- TradeExecutionService
- TradingOrchestrator

---

## Estimated Timeline

**Phase A**: Core Infrastructure - 2-3 days
**Phase B**: Trading Operations - 3-4 days
**Phase C**: Monitoring & Analytics - 3-4 days
**Phase D**: Configuration Management - 3-4 days (NEW - expanded scope)
**Phase E**: Polish & Testing - 2-3 days

**Total**: ~13-18 days for full implementation

---

## Notes

1. **Incremental Delivery**: Each phase delivers working functionality
2. **Signal-Based Manual Trading**: API publishes EntrySignalEvent/ExitSignalEvent with strategy_name="manual"
   - Manual signals flow through IDENTICAL pipeline as automated strategies
   - Uses manual.yaml strategy config for each symbol (defines risk parameters)
   - Broker .env.broker settings control scaling (POSITION_SPLIT, SCALING_TYPE, etc.)
   - User provides: Symbol + Direction
   - System handles: Entry price, sizing, SL, TP, scaling, validation
3. **Configuration Management**: Full read/write access to trading configurations via API
   - Strategy configs (YAML files) - risk parameters, optional scaling overrides
   - Broker configs (.env.broker) - symbol scaling settings, account risk limits
   - Backup system with rollback capability
   - Config reload without system restart (where possible)
4. **Strategy Monitoring** (Task 7.0) is a **new feature** not in existing system - provides real-time condition evaluation
5. **EventBus Integration**: All operations go through events (maintains architecture)
6. **Risk First**: Manual trades MUST go through EntryManager (no bypass)
7. **Caching**: 5-second cache for indicators and account info (reduce load)
8. **Security**: JWT with 60-minute expiration, rate limiting, CORS
9. **Documentation**: Auto-generated (Swagger/ReDoc) + markdown guides
10. **Testing**: Comprehensive unit, integration, and performance tests

---

**Document Version**: 1.2
**Created**: 2025-11-17
**Updated**: 2025-11-17
  - v1.1: Refactored to signal-based manual trading
  - v1.2: Added comprehensive configuration management API (Task 8.0)
**Status**: Ready for implementation
