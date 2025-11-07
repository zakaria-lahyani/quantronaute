# Bug Fix: DataFetchingService Restart Issue

## Issue

When running `main_orchestrated.py`, after the orchestrator's health check detected an unhealthy DataFetchingService and automatically restarted it, the service threw `KeyError` exceptions for timeframes ('1', '5', '15'):

```
KeyError: '1'
  File "app\services\data_fetching.py", line 226, in fetch_streaming_data
    if has_new_candle(df_stream, self.last_known_bars[tf], self.candle_index):
                                 ~~~~~~~~~~~~~~~~~~~~^^^^
```

## Root Cause

In `app/services/data_fetching.py`:

1. **Line 149** (`stop()` method): `self.last_known_bars.clear()` - The dictionary is cleared when the service stops
2. **Line 131-141** (`start()` method): The dictionary was **not** being reinitialized when the service starts

This caused a problem during the auto-restart flow:
1. Service encounters error (e.g., network connection issue)
2. Health check detects service is unhealthy
3. Orchestrator calls `stop()` on the service (clears `last_known_bars`)
4. Orchestrator calls `start()` on the service (doesn't reinitialize `last_known_bars`)
5. Service tries to fetch data and access `last_known_bars[tf]` → KeyError!

## Fix

Added initialization of `last_known_bars` dictionary in the `start()` method:

```python
def start(self) -> None:
    """Start the DataFetchingService."""
    self.logger.info(f"Starting {self.service_name}...")

    # DataFetchingService doesn't subscribe to events
    # It's called directly by the orchestrator

    # Reinitialize last_known_bars for all timeframes
    # This is important when restarting the service
    self.last_known_bars = {tf: None for tf in self.timeframes}

    self._set_status(ServiceStatus.RUNNING)
    self.logger.info(f"{self.service_name} started successfully")
```

**Location**: `app/services/data_fetching.py`, lines 136-138

## Testing

The fix was verified with the existing integration test:

```bash
python -m pytest tests/integration/test_trading_cycle.py::TestCompleteTradingCycle::test_service_restart -v
```

**Result**: ✅ PASSED

This test specifically verifies that services can be restarted successfully, and with the fix, the `last_known_bars` dictionary is properly reinitialized on restart.

## Impact

- **Services affected**: DataFetchingService only
- **Breaking changes**: None
- **Migration needed**: None - automatic fix

## Verification Steps

After this fix, the service restart flow now works correctly:

1. Service encounters error → enters ERROR state
2. Health check detects unhealthy service
3. Orchestrator calls `stop()` → `last_known_bars` is cleared
4. Orchestrator calls `start()` → `last_known_bars` is **reinitialized** with all timeframe keys
5. Service resumes fetching data → no KeyError!

## Related Files

- **Fixed**: `app/services/data_fetching.py` (lines 136-138)
- **Tests**: `tests/integration/test_trading_cycle.py` (test_service_restart)

## Date

2025-01-07
