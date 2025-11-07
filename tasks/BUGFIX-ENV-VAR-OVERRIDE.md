# Bug Fix: Environment Variable Override Not Working

## Issue

When running `main_orchestrated.py`, the system was using `EURUSD` from the `config/services.yaml` file instead of `XAUUSD` from the `.env` file.

**Expected**: System should use `SYMBOL=XAUUSD` from `.env`
**Actual**: System was using `symbol: "EURUSD"` from YAML config

## Root Cause

The `ConfigLoader._apply_env_overrides()` method was only checking for environment variables with the new naming convention:
- `TRADING_SYMBOL` (not found in user's `.env`)
- `TRADING_TIMEFRAMES` (not found in user's `.env`)

But the user's existing `.env` file uses the legacy naming convention:
- `SYMBOL=XAUUSD`
- `TIMEFRAMES=1,5,15`

This caused the YAML config values to be used instead of the `.env` values, violating the documented priority:
1. Environment variables (highest priority) ❌ Not working
2. Configuration file (being used instead)
3. Default values (lowest priority)

## Fix

Updated `ConfigLoader._apply_env_overrides()` to check **both** naming conventions:

```python
# Trading overrides
# Check TRADING_SYMBOL first (new naming), then fall back to SYMBOL (legacy .env naming)
if symbol := os.getenv("TRADING_SYMBOL") or os.getenv("SYMBOL"):
    env_var_name = "TRADING_SYMBOL" if os.getenv("TRADING_SYMBOL") else "SYMBOL"
    logger.info(f"Environment override: {env_var_name}={symbol}")
    config_dict.setdefault("trading", {})["symbol"] = symbol

# Check TRADING_TIMEFRAMES first, then fall back to TIMEFRAMES (legacy .env naming)
if timeframes := os.getenv("TRADING_TIMEFRAMES") or os.getenv("TIMEFRAMES"):
    timeframes_list = [tf.strip() for tf in timeframes.split(",")]
    env_var_name = "TRADING_TIMEFRAMES" if os.getenv("TRADING_TIMEFRAMES") else "TIMEFRAMES"
    logger.info(f"Environment override: {env_var_name}={timeframes_list}")
    config_dict.setdefault("trading", {})["timeframes"] = timeframes_list
```

**Location**: `app/infrastructure/config.py`, lines 277-288

### Priority Logic

1. **TRADING_SYMBOL** (if exists) - Highest priority
2. **SYMBOL** (if exists and TRADING_SYMBOL doesn't) - Fallback
3. YAML config value - Used if no env var
4. Default value - Used if no YAML or env var

This ensures backward compatibility with existing `.env` files while supporting the new naming convention.

## Testing

```bash
# Test with legacy SYMBOL env var
python -c "
import os
os.environ['SYMBOL'] = 'XAUUSD'
os.environ['TIMEFRAMES'] = '5,15,30'

from app.infrastructure.config import ConfigLoader
import logging

config = ConfigLoader.load('config/services.yaml', logger=logging.getLogger())
assert config.trading.symbol == 'XAUUSD', f'Expected XAUUSD, got {config.trading.symbol}'
assert config.trading.timeframes == ['5', '15', '30'], f'Expected [5,15,30], got {config.trading.timeframes}'
print('✅ Legacy SYMBOL env var works correctly')
"
```

**Result**: ✅ PASSED

### Output When Running main_orchestrated.py

Now when you run with `SYMBOL=XAUUSD` in your `.env`:

```
INFO:config_loader:Loading configuration from config/services.yaml
INFO:config_loader:Environment override: SYMBOL=XAUUSD
INFO:config_loader:Configuration loaded and validated successfully
```

And the HTTP requests will use the correct symbol:
```
HTTP Request: GET http://127.0.0.1:8000/mt5/symbols/XAUUSD/bars?timeframe=M15&num_bars=3
```

## Impact

- **Services affected**: All services that use symbol/timeframes
- **Breaking changes**: None (backward compatible)
- **Migration needed**: None - automatically works with existing `.env` files

## Files Modified

1. **[app/infrastructure/config.py](../app/infrastructure/config.py:277-288)** - Updated env var override logic
2. **[config/services.yaml](../config/services.yaml:48-54)** - Added comments about env var overrides
3. **[docs/MIGRATION_GUIDE.md](../docs/MIGRATION_GUIDE.md:242-262)** - Updated documentation

## Backward Compatibility

✅ **Old `.env` files** with `SYMBOL` and `TIMEFRAMES` work automatically
✅ **New naming** with `TRADING_SYMBOL` and `TRADING_TIMEFRAMES` also works
✅ **Priority**: TRADING_* vars take priority over legacy vars if both exist

## Date

2025-01-07
