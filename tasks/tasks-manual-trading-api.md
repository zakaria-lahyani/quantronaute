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

### Phase D: Risk Management
- Risk configuration endpoints
- Risk status endpoints
- Configuration persistence

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

### 1.0: Authentication System (JWT)

**Goal**: Secure the API with token-based authentication

**Tasks**:
- [ ] 1.1: Implement password hashing with bcrypt (`app/api/auth.py`)
- [ ] 1.2: Implement JWT token generation and validation
- [ ] 1.3: Create authentication Pydantic models (`app/api/models/auth.py`)
- [ ] 1.4: Implement `/auth/login` endpoint (POST - username/password → JWT)
- [ ] 1.5: Implement `/auth/refresh` endpoint (POST - refresh token)
- [ ] 1.6: Create OAuth2PasswordBearer dependency for protected endpoints
- [ ] 1.7: Add credential storage (JSON file or environment variables)
- [ ] 1.8: Unit tests for authentication (hashing, token validation)

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

### 2.0: Core API Service & EventBus Integration

**Goal**: Create APIService that integrates with existing EventBus architecture

**Tasks**:
- [ ] 2.1: Create `APIService` class inheriting from `EventDrivenService` (`app/api/service.py`)
- [ ] 2.2: Initialize FastAPI app within APIService
- [ ] 2.3: Implement EventResponseWaiter utility (`app/api/utils/event_waiter.py`)
- [ ] 2.4: Create correlation ID tracking system (`app/api/utils/correlation.py`)
- [ ] 2.5: Define API command events (`app/api/events.py`):
  - `PlaceSmartOrderCommandEvent` (symbol, direction, strategy_name, risk_override)
  - `ClosePositionCommandEvent` (ticket, volume)
  - `ModifyPositionCommandEvent` (ticket, sl, tp)
  - `QueryIndicatorsCommandEvent` (symbol, timeframe)
  - `QueryStrategyConditionsCommandEvent` (symbol, strategy_name)
  - Response events for each
- [ ] 2.6: Implement async request-response pattern (publish command → wait for response event)
- [ ] 2.7: Add timeout handling (5 seconds → 503 Service Unavailable)
- [ ] 2.8: Integrate APIService into TradingOrchestrator initialization
- [ ] 2.9: Add graceful shutdown handling
- [ ] 2.10: Unit tests for EventResponseWaiter and correlation ID matching

**Success Criteria**:
- APIService starts/stops with orchestrator
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

### 3.0: Automation Control Endpoints

**Goal**: Replace Phase 1 file-based toggle with API endpoints

**Tasks**:
- [ ] 3.1: Create automation router (`app/api/routers/automation.py`)
- [ ] 3.2: Implement `POST /automation/enable` endpoint
- [ ] 3.3: Implement `POST /automation/disable` endpoint
- [ ] 3.4: Implement `GET /automation/status` endpoint
- [ ] 3.5: Create request/response models (`app/api/models/requests.py`, `responses.py`)
- [ ] 3.6: Reuse existing `ToggleAutomationEvent` from Phase 1
- [ ] 3.7: Add rate limiting (10 requests/minute)
- [ ] 3.8: Integration tests for automation endpoints

**API Specification**:
```
POST /api/v1/automation/enable
POST /api/v1/automation/disable
GET  /api/v1/automation/status
```

**Success Criteria**:
- Automation can be toggled via API
- State changes are reflected in logs and metrics
- Rate limiting prevents rapid toggling
- Response includes current state, timestamp, reason

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

### 5.0: Smart Order Management Endpoints

**Goal**: Enable smart pending order creation with automatic calculations

**Philosophy**: System calculates order parameters based on risk config, not manual specification.

**Tasks**:
- [ ] 5.1: Create orders router (`app/api/routers/orders.py`)
- [ ] 5.2: Implement `GET /orders` (list all pending orders)
- [ ] 5.3: Implement `GET /orders/{symbol}` (list by symbol)
- [ ] 5.4: Implement `POST /orders` (smart order placement)
  - Request: symbol, direction, strategy_name (optional), risk_override (optional)
  - System calculates: position size, SL, TP, scaling
  - Entry price is MARKET (immediate execution)
  - System uses EntryManager for all calculations
- [ ] 5.5: Implement `DELETE /orders/{ticket}` (cancel order)
- [ ] 5.6: Implement `DELETE /orders/all` (cancel all, optional symbol filter)
- [ ] 5.7: Integrate with TradeExecutionService via PlaceSmartOrderCommandEvent
- [ ] 5.8: Create request/response models
- [ ] 5.9: Integration tests for order operations

**Success Criteria**:
- Orders can be placed with one click (symbol + direction only)
- System handles all calculations (sizing, SL, TP, scaling)
- Orders can be cancelled
- Validation errors return clear messages

**Note**: No support for limit/stop orders - all orders execute at market price. This is intentional for simplicity.

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

### 8.0: Risk Configuration Endpoints

**Goal**: View and update risk parameters at runtime

**Tasks**:
- [ ] 8.1: Create risk router (`app/api/routers/risk.py`)
- [ ] 8.2: Implement `GET /risk/config` (all symbols and strategies)
- [ ] 8.3: Implement `GET /risk/config/{symbol}` (specific symbol)
- [ ] 8.4: Implement `GET /risk/config/{symbol}/{strategy}` (specific strategy)
- [ ] 8.5: Implement `POST /risk/config/{symbol}/{strategy}/update` (update risk params)
- [ ] 8.6: Implement `GET /risk/limits` (account-level risk limits)
- [ ] 8.7: Implement `GET /risk/status` (current risk status and budget)
- [ ] 8.8: Create `RiskConfigUpdatedEvent`
- [ ] 8.9: Implement YAML file persistence for config updates
- [ ] 8.10: Add validation (TP > SL, valid types, etc.)
- [ ] 8.11: Create backup before overwriting YAML files
- [ ] 8.12: Integration tests for risk config operations

**Success Criteria**:
- Risk parameters can be updated via API
- Changes persist across application restarts (saved to YAML)
- Invalid configurations are rejected with clear errors
- Backup files created before modifications

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
**Phase D**: Risk Management - 2-3 days
**Phase E**: Polish & Testing - 2-3 days

**Total**: ~12-17 days for full implementation

---

## Notes

1. **Incremental Delivery**: Each phase delivers working functionality
2. **Smart Manual Trading Philosophy**: API is a control panel - all intelligence stays in trading system
   - User provides: Symbol + Direction (+ optional risk override)
   - System handles: Entry price, sizing, SL, TP, scaling, validation
   - No manual specification of prices or volumes
3. **Strategy Monitoring** (Task 7.0) is a **new feature** not in existing system - provides real-time condition evaluation
4. **EventBus Integration**: All operations go through events (maintains architecture)
5. **Risk First**: Manual trades MUST go through EntryManager (no bypass)
6. **Caching**: 5-second cache for indicators and account info (reduce load)
7. **Security**: JWT with 60-minute expiration, rate limiting, CORS
8. **Documentation**: Auto-generated (Swagger/ReDoc) + markdown guides
9. **Testing**: Comprehensive unit, integration, and performance tests

---

**Document Version**: 1.1
**Created**: 2025-11-17
**Updated**: 2025-11-17 - Refactored to smart manual trading philosophy
**Status**: Ready for implementation
