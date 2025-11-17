# Manual Trading API - Testing Guide

## Overview

This guide provides step-by-step instructions for testing the Manual Trading API in both standalone and integrated modes.

---

## Prerequisites

**Required:**
- Python 3.10+
- `curl` or `httpie` (for command-line testing)
- `jq` (optional, for JSON formatting)

**For Full Integration Testing:**
- MT5 API server running (for account/position data)
- Trading system with Orchestrator configured (for indicator/strategy data)

---

## Quick Test Setup

### 1. Start the API Server

**Option A: Standalone Mode (Limited Functionality)**

Create a test startup script:

```python
# test_api_standalone.py
import asyncio
import logging
from app.infrastructure.event_bus import EventBus
from app.api.service import APIService
from app.api.main import create_app
import uvicorn

async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Initialize EventBus only (standalone mode)
    event_bus = EventBus(logger=logger, log_all_events=False)

    # Initialize APIService without MT5Client or Orchestrator
    api_service = APIService(
        event_bus=event_bus,
        logger=logger
    )
    await api_service.start()

    # Create FastAPI app
    app = create_app()
    app.state.api_service = api_service

    # Start server
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)

    try:
        await server.serve()
    finally:
        await api_service.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python test_api_standalone.py
```

**Option B: Integrated Mode (Full Functionality)**

You need to integrate with your existing trading system. See [api-integration.md](api-integration.md) for details.

For testing, create an integration test script:

```python
# test_api_integrated.py
import asyncio
import logging
from app.infrastructure.event_bus import EventBus
from app.infrastructure.multi_symbol_orchestrator import MultiSymbolOrchestrator
from app.clients.mt5.client import MT5Client
from app.api.service import APIService
from app.api.main import create_app
import uvicorn

async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # 1. Initialize EventBus
    event_bus = EventBus(logger=logger, log_all_events=False)

    # 2. Initialize MT5Client
    mt5_client = MT5Client(base_url="http://localhost:8000")  # Your MT5 API URL

    # 3. Initialize Orchestrator (simplified - add your actual setup)
    orchestrator = MultiSymbolOrchestrator(event_bus=event_bus)

    # Add your symbols with configured services
    # orchestrator.add_symbol("XAUUSD", components={...})

    # 4. Initialize APIService with full integration
    api_service = APIService(
        event_bus=event_bus,
        mt5_client=mt5_client,
        orchestrator=orchestrator,
        logger=logger
    )
    await api_service.start()

    # 5. Create and start FastAPI app
    app = create_app()
    app.state.api_service = api_service

    config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)

    try:
        await server.serve()
    finally:
        await api_service.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python test_api_integrated.py
```

---

## Test Suite 1: Authentication

### Test 1.1: Login
```bash
# Get JWT token
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' | jq

# Expected: 200 OK
# {
#   "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "token_type": "bearer",
#   "expires_in": 3600
# }
```

### Test 1.2: Invalid Login
```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"wrong"}' | jq

# Expected: 401 Unauthorized
# {
#   "detail": "Incorrect username or password"
# }
```

### Test 1.3: Access Protected Endpoint Without Token
```bash
curl http://localhost:8080/account/summary | jq

# Expected: 401 Unauthorized
# {
#   "detail": "Not authenticated"
# }
```

### Test 1.4: Set Token for Remaining Tests
```bash
# Save token to environment variable
export TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"
```

---

## Test Suite 2: System Monitoring (Always Available)

### Test 2.1: System Status
```bash
curl http://localhost:8080/system/status \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected: 200 OK
# {
#   "running": true,
#   "uptime_seconds": 123.45,
#   "startup_time": "2025-11-17T10:00:00Z",
#   "event_bus_metrics": {...}
# }
```

### Test 2.2: System Metrics
```bash
curl http://localhost:8080/system/metrics \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected: 200 OK
# {
#   "events_published": 100,
#   "events_delivered": 98,
#   "handler_errors": 0,
#   "subscription_count": 5
# }
```

---

## Test Suite 3: Manual Trading (Always Available)

### Test 3.1: Trigger Entry Signal
```bash
curl -X POST http://localhost:8080/signals/entry \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "XAUUSD",
    "direction": "long",
    "entry_price": 2650.25
  }' | jq

# Expected: 200 OK
# {
#   "status": "success",
#   "message": "Manual entry signal triggered",
#   "symbol": "XAUUSD",
#   "direction": "long",
#   "strategy_name": "manual"
# }
```

### Test 3.2: Trigger Exit Signal
```bash
curl -X POST http://localhost:8080/signals/exit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "XAUUSD",
    "direction": "long",
    "reason": "manual_close"
  }' | jq

# Expected: 200 OK
```

---

## Test Suite 4: Automation Control (Always Available)

### Test 4.1: Disable Automation
```bash
curl -X POST http://localhost:8080/automation/disable \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected: 200 OK
# {
#   "status": "success",
#   "message": "Automation disabled",
#   "automation_enabled": false
# }
```

### Test 4.2: Enable Automation
```bash
curl -X POST http://localhost:8080/automation/enable \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected: 200 OK
```

### Test 4.3: Check Automation Status
```bash
curl http://localhost:8080/automation/status \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected: 200 OK
# {
#   "automation_enabled": true
# }
```

---

## Test Suite 5: Account Monitoring (Requires MT5Client)

### Test 5.1: Account Summary
```bash
curl http://localhost:8080/account/summary \
  -H "Authorization: Bearer $TOKEN" | jq

# Standalone Mode: Error response
# Integrated Mode: Account data
# {
#   "balance": 10000.50,
#   "equity": 10250.75,
#   "margin": 500.00,
#   "margin_free": 9750.75,
#   "profit": 250.25
# }
```

### Test 5.2: Account Balance
```bash
curl http://localhost:8080/account/balance \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected (integrated): {"balance": 10000.50}
```

### Test 5.3: Account Equity
```bash
curl http://localhost:8080/account/equity \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Test 5.4: Margin Info
```bash
curl http://localhost:8080/account/margin \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## Test Suite 6: Position Management (Requires MT5Client)

### Test 6.1: List All Positions
```bash
curl http://localhost:8080/positions \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected (integrated):
# {
#   "positions": [...],
#   "total_positions": 2,
#   "total_profit": 150.25
# }
```

### Test 6.2: Positions by Symbol
```bash
curl http://localhost:8080/positions/XAUUSD \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Test 6.3: Position by Ticket
```bash
# Replace 123456 with actual ticket number
curl http://localhost:8080/positions/ticket/123456 \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## Test Suite 7: Indicator Monitoring (Requires Orchestrator)

### Test 7.1: All Indicators for Symbol
```bash
curl http://localhost:8080/indicators/XAUUSD \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected (integrated):
# {
#   "symbol": "XAUUSD",
#   "timestamp": "2025-11-17T10:30:00Z",
#   "timeframes": {
#     "M1": {...},
#     "H1": {...}
#   }
# }
```

### Test 7.2: Indicators for Specific Timeframe
```bash
curl http://localhost:8080/indicators/XAUUSD/H1 \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected:
# {
#   "symbol": "XAUUSD",
#   "timeframe": "H1",
#   "indicators": {
#     "close": 2650.25,
#     "sma_50": 2645.00,
#     "rsi_14": 62.1
#   }
# }
```

### Test 7.3: Specific Indicator Value
```bash
curl http://localhost:8080/indicators/XAUUSD/H1/rsi_14 \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected:
# {
#   "symbol": "XAUUSD",
#   "timeframe": "H1",
#   "indicator": "rsi_14",
#   "value": 62.1
# }
```

---

## Test Suite 8: Strategy Monitoring (Requires Orchestrator)

### Test 8.1: List Strategies
```bash
curl http://localhost:8080/strategies/XAUUSD \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected:
# {
#   "symbol": "XAUUSD",
#   "strategies": ["manual", "breakout"],
#   "total_strategies": 2
# }
```

### Test 8.2: Strategy Configuration
```bash
curl http://localhost:8080/strategies/XAUUSD/breakout \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected:
# {
#   "symbol": "XAUUSD",
#   "strategy_name": "breakout",
#   "config": {...}
# }
```

### Test 8.3: Strategy Metrics
```bash
curl http://localhost:8080/strategies/XAUUSD/metrics \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected:
# {
#   "symbol": "XAUUSD",
#   "metrics": {
#     "strategies_evaluated": 1250,
#     "entry_signals_generated": 15,
#     "automation_enabled": true
#   }
# }
```

---

## Automated Testing Script

Create `test_api.sh`:

```bash
#!/bin/bash

# Configuration
API_URL="http://localhost:8080"
USERNAME="admin"
PASSWORD="your_password"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test counter
TOTAL=0
PASSED=0
FAILED=0

# Function to run test
run_test() {
    local test_name=$1
    local command=$2
    local expected_status=$3

    TOTAL=$((TOTAL + 1))
    echo -n "Test $TOTAL: $test_name... "

    http_code=$(eval "$command -w '%{http_code}' -o /dev/null -s")

    if [ "$http_code" == "$expected_status" ]; then
        echo -e "${GREEN}PASSED${NC} (HTTP $http_code)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}FAILED${NC} (Expected $expected_status, got $http_code)"
        FAILED=$((FAILED + 1))
    fi
}

echo "=== Manual Trading API Test Suite ==="
echo ""

# Get token
echo "Authenticating..."
TOKEN=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
  | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}Authentication failed!${NC}"
    exit 1
fi

echo -e "${GREEN}Authenticated successfully${NC}"
echo ""

# System Tests
echo "=== System Monitoring Tests ==="
run_test "System Status" \
    "curl $API_URL/system/status -H 'Authorization: Bearer $TOKEN'" \
    "200"

run_test "System Metrics" \
    "curl $API_URL/system/metrics -H 'Authorization: Bearer $TOKEN'" \
    "200"
echo ""

# Manual Trading Tests
echo "=== Manual Trading Tests ==="
run_test "Entry Signal" \
    "curl -X POST $API_URL/signals/entry -H 'Authorization: Bearer $TOKEN' -H 'Content-Type: application/json' -d '{\"symbol\":\"XAUUSD\",\"direction\":\"long\"}'" \
    "200"

run_test "Exit Signal" \
    "curl -X POST $API_URL/signals/exit -H 'Authorization: Bearer $TOKEN' -H 'Content-Type: application/json' -d '{\"symbol\":\"XAUUSD\",\"direction\":\"long\"}'" \
    "200"
echo ""

# Automation Tests
echo "=== Automation Control Tests ==="
run_test "Disable Automation" \
    "curl -X POST $API_URL/automation/disable -H 'Authorization: Bearer $TOKEN'" \
    "200"

run_test "Enable Automation" \
    "curl -X POST $API_URL/automation/enable -H 'Authorization: Bearer $TOKEN'" \
    "200"
echo ""

# Account Tests (may fail in standalone mode)
echo "=== Account Monitoring Tests (may fail if not integrated) ==="
run_test "Account Summary" \
    "curl $API_URL/account/summary -H 'Authorization: Bearer $TOKEN'" \
    "200"

run_test "Account Balance" \
    "curl $API_URL/account/balance -H 'Authorization: Bearer $TOKEN'" \
    "200"
echo ""

# Position Tests
echo "=== Position Management Tests (may fail if not integrated) ==="
run_test "List Positions" \
    "curl $API_URL/positions -H 'Authorization: Bearer $TOKEN'" \
    "200"
echo ""

# Indicator Tests
echo "=== Indicator Monitoring Tests (may fail if not integrated) ==="
run_test "Indicators for XAUUSD H1" \
    "curl $API_URL/indicators/XAUUSD/H1 -H 'Authorization: Bearer $TOKEN'" \
    "200"
echo ""

# Strategy Tests
echo "=== Strategy Monitoring Tests (may fail if not integrated) ==="
run_test "List Strategies" \
    "curl $API_URL/strategies/XAUUSD -H 'Authorization: Bearer $TOKEN'" \
    "200"
echo ""

# Summary
echo "================================"
echo "Test Results:"
echo -e "Total: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "================================"

if [ $FAILED -eq 0 ]; then
    exit 0
else
    exit 1
fi
```

Make it executable and run:
```bash
chmod +x test_api.sh
./test_api.sh
```

---

## Python Test Client

Create `test_api_client.py`:

```python
import requests
import json

class APITestClient:
    def __init__(self, base_url="http://localhost:8080", username="admin", password="your_password"):
        self.base_url = base_url
        self.token = None
        self.username = username
        self.password = password

    def login(self):
        """Authenticate and get JWT token."""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"username": self.username, "password": self.password}
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            print("✓ Authenticated successfully")
            return True
        else:
            print("✗ Authentication failed")
            return False

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def test_system_status(self):
        """Test system status endpoint."""
        response = requests.get(f"{self.base_url}/system/status", headers=self._headers())
        print(f"System Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))

    def test_account_summary(self):
        """Test account summary endpoint."""
        response = requests.get(f"{self.base_url}/account/summary", headers=self._headers())
        print(f"Account Summary: {response.status_code}")
        print(json.dumps(response.json(), indent=2))

    def test_positions(self):
        """Test positions endpoint."""
        response = requests.get(f"{self.base_url}/positions", headers=self._headers())
        print(f"Positions: {response.status_code}")
        print(json.dumps(response.json(), indent=2))

    def test_indicators(self, symbol="XAUUSD", timeframe="H1"):
        """Test indicators endpoint."""
        response = requests.get(
            f"{self.base_url}/indicators/{symbol}/{timeframe}",
            headers=self._headers()
        )
        print(f"Indicators ({symbol} {timeframe}): {response.status_code}")
        print(json.dumps(response.json(), indent=2))

    def test_manual_entry(self, symbol="XAUUSD", direction="long"):
        """Test manual entry signal."""
        response = requests.post(
            f"{self.base_url}/signals/entry",
            headers=self._headers(),
            json={"symbol": symbol, "direction": direction}
        )
        print(f"Manual Entry Signal: {response.status_code}")
        print(json.dumps(response.json(), indent=2))

# Usage
if __name__ == "__main__":
    client = APITestClient()

    if client.login():
        print("\n=== Testing Endpoints ===\n")

        client.test_system_status()
        print()

        client.test_account_summary()
        print()

        client.test_positions()
        print()

        client.test_indicators()
        print()

        client.test_manual_entry()
```

Run it:
```bash
python test_api_client.py
```

---

## Troubleshooting Tests

### Issue: All tests return 401
**Solution**: Check authentication credentials in `.env` or test script

### Issue: Account/Position tests fail
**Solution**: Start API in integrated mode with MT5Client

### Issue: Indicator/Strategy tests fail
**Solution**: Start API in integrated mode with Orchestrator and configured symbols

### Issue: Connection refused
**Solution**: Ensure API server is running on port 8080

---

## Next Steps

1. Run standalone tests first to verify basic functionality
2. Integrate with MT5Client to test account/position endpoints
3. Integrate with Orchestrator to test indicator/strategy endpoints
4. Build your own monitoring dashboard using the API

**See also:**
- [API Usage Guide](./api-usage.md)
- [Integration Guide](./api-integration.md)
