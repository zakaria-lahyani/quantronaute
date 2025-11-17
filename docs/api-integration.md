# API Integration Guide

## Overview

The Manual Trading API can run in two modes:

1. **Standalone Mode** (Current - Limited): API runs independently, only signal publishing works
2. **Integrated Mode** (Recommended): API connected to trading system, full functionality available

This guide explains how to integrate the API with your trading system to enable full functionality.

---

## Integration Architecture

```
Trading System (main.py)
├── MT5Client (account data)
├── MultiSymbolOrchestrator
│   ├── IndicatorCalculationService (per symbol)
│   ├── StrategyEvaluationService (per symbol)
│   └── TradeExecutionService (per symbol)
└── EventBus (shared)

FastAPI (app/api/main.py)
├── APIService
│   ├── EventBus (same instance) ✅
│   ├── MT5Client (reference) → Account endpoints
│   └── Orchestrator (reference) → Indicator endpoints
└── HTTP Endpoints
```

---

## Current Status

### ✅ Working Without Integration
- **Authentication**: JWT login/refresh
- **Manual Trading Signals**: POST /signals/entry, POST /signals/exit
- **Automation Control**: POST /automation/enable, POST /automation/disable
- **System Monitoring**: GET /system/status, GET /system/metrics

### ⚡ Requires Integration
- **Account Monitoring**: GET /account/* (needs MT5Client)
- **Indicator Monitoring**: GET /indicators/* (needs Orchestrator)
- **Position Management**: GET /positions/* (needs MT5Client)
- **Strategy Monitoring**: GET /strategies/* (needs Orchestrator)

---

## How to Integrate

### Step 1: Update Your Trading System Startup

When initializing your trading system, pass the MT5Client and Orchestrator to the APIService.

**Before (Standalone Mode)**:
```python
# In your trading system startup (e.g., main.py or live_trader.py)

# Initialize EventBus
event_bus = EventBus(logger=logger)

# Initialize MT5Client
mt5_client = MT5Client(base_url="http://localhost:8000")

# Initialize Orchestrator
orchestrator = MultiSymbolTradingOrchestrator(...)
orchestrator.initialize(
    client=mt5_client,
    data_source=data_source,
    symbol_components=symbol_components
)

# Start the API (if running embedded)
api_service = APIService(event_bus=event_bus, logger=logger)
await api_service.start()
```

**After (Integrated Mode)**:
```python
# In your trading system startup (e.g., main.py or live_trader.py)

# Initialize EventBus
event_bus = EventBus(logger=logger)

# Initialize MT5Client
mt5_client = MT5Client(base_url="http://localhost:8000")

# Initialize Orchestrator
orchestrator = MultiSymbolTradingOrchestrator(...)
orchestrator.initialize(
    client=mt5_client,
    data_source=data_source,
    symbol_components=symbol_components
)

# Start the API with references to trading components
api_service = APIService(
    event_bus=event_bus,
    mt5_client=mt5_client,      # ADD THIS
    orchestrator=orchestrator,   # ADD THIS
    logger=logger
)
await api_service.start()
```

### Step 2: Update FastAPI Lifespan (If Running Standalone)

If the API runs as a separate FastAPI application (recommended for production), update `app/api/main.py`:

**Current Implementation** (working, but limited):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    event_bus = EventBus(logger=logger, log_all_events=False)

    api_service = APIService(event_bus=event_bus, logger=logger)
    await api_service.start()

    app.state.event_bus = event_bus
    app.state.api_service = api_service

    yield

    # Shutdown
    await api_service.stop()
```

**For Full Integration** (requires shared EventBus):

```python
# Option A: Import from trading system (requires shared memory/process)
from your_trading_system import get_event_bus, get_mt5_client, get_orchestrator

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - get references from trading system
    event_bus = get_event_bus()
    mt5_client = get_mt5_client()
    orchestrator = get_orchestrator()

    api_service = APIService(
        event_bus=event_bus,
        mt5_client=mt5_client,
        orchestrator=orchestrator,
        logger=logger
    )
    await api_service.start()

    app.state.api_service = api_service

    yield

    await api_service.stop()
```

### Step 3: Verify Integration

After integration, test the endpoints:

**1. Test Account Endpoints**:
```bash
# Get JWT token first
TOKEN=$(curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' \
  | jq -r '.access_token')

# Test account summary
curl http://localhost:8080/account/summary \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected: Real account data
# {
#   "balance": 10000.50,
#   "equity": 10250.75,
#   "margin": 500.00,
#   ...
# }
```

**2. Test Indicator Endpoints**:
```bash
# Get indicators for XAUUSD H1
curl http://localhost:8080/indicators/XAUUSD/H1 \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected: Live indicator data
# {
#   "symbol": "XAUUSD",
#   "timeframe": "H1",
#   "timestamp": "2025-11-17T10:30:00Z",
#   "indicators": {
#     "close": 2650.25,
#     "sma_50": 2645.00,
#     ...
#   }
# }
```

**3. Test Manual Signals** (should work in both modes):
```bash
# Trigger entry signal
curl -X POST http://localhost:8080/signals/entry \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"XAUUSD","direction":"long"}' | jq

# Expected: Success response
# {
#   "status": "success",
#   "message": "Manual entry signal triggered",
#   ...
# }
```

---

## Deployment Scenarios

### Scenario 1: API Embedded in Trading System
- API runs in the same process as trading system
- Direct access to all components
- Simplest integration
- Used for development/testing

**Implementation**: See Step 1 above

### Scenario 2: API as Separate Service (Docker)
- API runs in separate Docker container
- Trading system runs in separate container
- Requires shared EventBus via message broker (Redis, RabbitMQ)
- Production-ready architecture

**Requirements**:
- Shared EventBus implementation (e.g., Redis Pub/Sub)
- Network connectivity between containers
- Shared data store for account/indicator state

### Scenario 3: API with Read-Only Access
- API queries data via HTTP from MT5 API server
- No direct access to internal services
- Requires MT5 API server to expose account/indicator endpoints

**Not currently supported** - would require building HTTP clients

---

## API Endpoint Status

| Endpoint | Standalone | Integrated | Notes |
|----------|------------|------------|-------|
| POST /auth/login | ✅ | ✅ | Always works |
| POST /signals/entry | ✅ | ✅ | Publishes to EventBus |
| POST /signals/exit | ✅ | ✅ | Publishes to EventBus |
| POST /automation/enable | ✅ | ✅ | Publishes to EventBus |
| POST /automation/disable | ✅ | ✅ | Publishes to EventBus |
| GET /system/status | ✅ | ✅ | Returns EventBus metrics |
| GET /system/metrics | ✅ | ✅ | Returns EventBus metrics |
| GET /account/summary | ❌ | ✅ | Needs MT5Client |
| GET /account/balance | ❌ | ✅ | Needs MT5Client |
| GET /account/equity | ❌ | ✅ | Needs MT5Client |
| GET /account/margin | ❌ | ✅ | Needs MT5Client |
| GET /indicators/{symbol} | ❌ | ✅ | Needs Orchestrator |
| GET /indicators/{symbol}/{tf} | ❌ | ✅ | Needs Orchestrator |
| GET /indicators/{symbol}/{tf}/{ind} | ❌ | ✅ | Needs Orchestrator |
| GET /positions | ❌ | 🔄 | Needs MT5Client (pending implementation) |
| GET /strategies | ❌ | 🔄 | Needs Orchestrator (pending implementation) |

Legend:
- ✅ Fully working
- ❌ Returns error (service not available)
- 🔄 Pending implementation

---

## Troubleshooting

### Issue: Account endpoints return "not available"

**Cause**: MT5Client not passed to APIService

**Solution**:
```python
# Check APIService initialization
api_service = APIService(
    event_bus=event_bus,
    mt5_client=mt5_client,  # Make sure this is not None
    logger=logger
)
```

### Issue: Indicator endpoints return "not available"

**Cause**: Orchestrator not passed to APIService

**Solution**:
```python
# Check APIService initialization
api_service = APIService(
    event_bus=event_bus,
    orchestrator=orchestrator,  # Make sure this is not None
    logger=logger
)
```

### Issue: Indicator endpoint returns "symbol not configured"

**Cause**: Symbol not initialized in orchestrator

**Solution**: Ensure symbol is added to orchestrator:
```python
orchestrator.add_symbol("XAUUSD", components={...})
```

### Issue: Manual signals not executing

**Cause**: EventBus not properly shared between API and trading system

**Solution**: Ensure both use the same EventBus instance:
```python
# Create single EventBus instance
event_bus = EventBus(logger=logger)

# Use same instance in both
orchestrator = MultiSymbolOrchestrator(event_bus=event_bus)
api_service = APIService(event_bus=event_bus)
```

---

## Next Steps

After integration:

1. ✅ **Account Monitoring**: Test all account endpoints
2. ✅ **Indicator Monitoring**: Test indicator endpoints for all symbols
3. 🔄 **Position Management**: Implement position query methods in APIService
4. 🔄 **Strategy Monitoring**: Implement strategy condition evaluation
5. 🔄 **Configuration Management**: Implement config read/write endpoints

---

## Example: Full Integration Code

Here's a complete example of integrated startup:

```python
import asyncio
import logging
from app.infrastructure.event_bus import EventBus
from app.infrastructure.multi_symbol_orchestrator import MultiSymbolOrchestrator
from app.clients.mt5.client import MT5Client
from app.api.service import APIService
from app.api.main import create_app
import uvicorn

async def main():
    logger = logging.getLogger(__name__)

    # 1. Initialize shared EventBus
    event_bus = EventBus(logger=logger, log_all_events=False)

    # 2. Initialize MT5Client
    mt5_client = MT5Client(base_url="http://localhost:8000")

    # 3. Initialize Orchestrator with symbols
    orchestrator = MultiSymbolOrchestrator(event_bus=event_bus)

    # Add symbols (your existing setup)
    orchestrator.add_symbol("XAUUSD", components={
        "indicator_calculation": indicator_service,
        "strategy_evaluation": strategy_service,
        "trade_execution": trade_service
    })

    # 4. Initialize APIService with full integration
    api_service = APIService(
        event_bus=event_bus,
        mt5_client=mt5_client,
        orchestrator=orchestrator,
        logger=logger
    )
    await api_service.start()

    # 5. Create and configure FastAPI app
    app = create_app()
    app.state.api_service = api_service

    # 6. Start FastAPI server
    config = uvicorn.Config(app, host="0.0.0.0", port=8080)
    server = uvicorn.Server(config)

    try:
        await server.serve()
    finally:
        await api_service.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

**Document Version**: 1.0
**Date**: 2025-11-17
**Status**: Ready for integration
