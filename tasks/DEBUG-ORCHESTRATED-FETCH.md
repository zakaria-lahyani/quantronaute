# Debug Tool: Orchestrated Data Fetch

## Overview

A minimal version of the orchestrated system that **only runs DataFetchingService** with clean, focused logging. This helps validate the event-driven data fetching without the noise from indicators, strategies, and trading.

## Differences from `debug_data_fetch.py`

| Feature | `debug_data_fetch.py` | `debug_orchestrated_fetch.py` |
|---------|----------------------|-------------------------------|
| Architecture | Direct data source calls | Event-driven with DataFetchingService |
| Events | None | Publishes DataFetchedEvent, NewCandleEvent |
| Logging | Raw DataFrame display | Event-based logging |
| Purpose | Validate raw data | Validate service + events |
| Complexity | Simple | Closer to production |

## What It Shows

### 1. **Data Fetched**
```
📥 [EVENT] DataFetchedEvent: XAUUSD 1
   Bars received: 3
   Latest bar: close=4009.23000, volume=245
```

### 2. **New Candle Detected**
```
🆕 [EVENT] NewCandleEvent: XAUUSD 1
   Time: 2025-01-07 09:15:00
   Open: 4009.12000
   High: 4009.45000
   Low: 4008.98000
   Close: 4009.23000
   Volume: 245
```

### 3. **Selected Row**
The service shows which candle is selected using `candle_index: 1`:
- `candle_index: 1` = Most recent **closed** candle (recommended)
- `candle_index: 2` = Second most recent closed candle

## Usage

### Run the Debug Script

```bash
python -m app.debug_orchestrated_fetch
```

### What You'll See

```
================================================================================
🔍 ORCHESTRATED DATA FETCH DEBUG
   (Event-Driven - DataFetchingService Only)
================================================================================

📁 Loading configuration from: ...

⚙️  Configuration:
   Symbol: XAUUSD
   API URL: http://127.0.0.1:8000
   Timeframes: ['1', '5', '15']

🔌 Connecting to MT5 API...
   ✅ Connected successfully

📊 Initializing data source manager...
   ✅ Data source initialized

🚌 Creating EventBus...
   ✅ EventBus created and subscribed

🔄 Creating DataFetchingService...
   ✅ DataFetchingService created
      Candle index: 1 (most recent closed)
      Bars to fetch: 3

▶️  Starting DataFetchingService...
   ✅ Service started

================================================================================
🚀 STARTING DATA FETCH LOOP
================================================================================
Press Ctrl+C to stop

────────────────────────────────────────────────────────────────────────────────
📍 ITERATION 1 - 2025-01-07 09:15:30
────────────────────────────────────────────────────────────────────────────────

🔄 Fetching data for all timeframes...

   📥 [EVENT] DataFetchedEvent: XAUUSD 1
      Bars received: 3
      Latest bar: close=4009.23000, volume=245

   🆕 [EVENT] NewCandleEvent: XAUUSD 1
      Time: 2025-01-07 09:15:00
      Open: 4009.12000
      High: 4009.45000
      Low: 4008.98000
      Close: 4009.23000
      Volume: 245

   📥 [EVENT] DataFetchedEvent: XAUUSD 5
      Bars received: 3
      Latest bar: close=4008.98000, volume=1024

   📥 [EVENT] DataFetchedEvent: XAUUSD 15
      Bars received: 3
      Latest bar: close=4008.45000, volume=3456

✅ Fetch complete: 3/3 timeframes successful

📊 Service Metrics:
   Total fetches: 3
   New candles detected: 1
   Fetch errors: 0

⏳ Waiting 30 seconds before next fetch...
────────────────────────────────────────────────────────────────────────────────
```

## Benefits

### 1. **Clean Logs**
- ✅ Only data fetch related logs
- ✅ No indicator calculation logs
- ✅ No strategy evaluation logs
- ✅ No trading execution logs
- ✅ HTTP logs are suppressed

### 2. **Event Flow Visibility**
See exactly what events are published:
- `DataFetchedEvent` - Every time data is fetched
- `NewCandleEvent` - Only when a new candle is detected

### 3. **Service Validation**
Validates that:
- ✅ DataFetchingService starts correctly
- ✅ Events are published correctly
- ✅ New candle detection works
- ✅ Service metrics are tracked

### 4. **Selected Row Display**
Shows which candle is being selected:
```
Candle index: 1 (most recent closed)
```

This corresponds to `df.iloc[-1]` in the DataFrame (last row = most recent closed candle).

## Configuration

The script uses:

```python
config = {
    'symbol': env_config.SYMBOL,        # From .env
    'timeframes': timeframes,            # From .env or default
    'candle_index': 1,                   # Most recent closed candle
    'nbr_bars': 3,                       # Fetch 3 bars per request
    'retry_attempts': 3,
    'fetch_interval': 30,
}
```

### Change Candle Selection

Edit the `candle_index` in the script (line ~105):

```python
config = {
    'candle_index': 1,  # 1 = most recent closed, 2 = second most recent, etc.
}
```

### Change Number of Bars

Edit the `nbr_bars` in the script (line ~106):

```python
config = {
    'nbr_bars': 5,  # Fetch 5 bars instead of 3
}
```

## What to Validate

### 1. **Service Starts**
```
✅ Service started
```

### 2. **Events Published**
You should see:
- `DataFetchedEvent` for each timeframe
- `NewCandleEvent` only when candles change

### 3. **New Candle Detection**
```
New candles detected: 1
```

This should increase when M1 candles change (every minute).

### 4. **No Errors**
```
Fetch errors: 0
```

### 5. **Correct Row Selected**
The `NewCandleEvent` shows the selected candle:
```
🆕 [EVENT] NewCandleEvent: XAUUSD 1
   Time: 2025-01-07 09:15:00  ← This should be the most recent CLOSED candle
```

## Troubleshooting

### Too Many New Candles Detected

If you see new candles detected on every iteration:
```
New candles detected: 10  ← Should be lower!
```

**Cause**: The new candle detection might be too sensitive.

**Solution**: Check `has_new_candle()` logic in `app/utils/functions_helper.py`.

### No New Candles Ever

If you never see new candles:
```
New candles detected: 0  ← Should increase over time!
```

**Cause**: Candles might not be changing, or detection is broken.

**Solution**:
- Wait 1-2 minutes for M1 candle to change
- Check that market is open
- Verify data is being fetched

### Events Not Showing

If you don't see `[EVENT]` logs:

**Cause**: Event handlers not subscribed.

**Solution**: Check that `event_bus.subscribe()` calls are working.

## Files

- **[app/debug_orchestrated_fetch.py](../app/debug_orchestrated_fetch.py)** - Main debug script

## Progression Path

1. ✅ `debug_data_fetch.py` - Validate raw data fetching
2. ✅ `debug_orchestrated_fetch.py` - Validate DataFetchingService + events ← **You are here**
3. ⏭️ Create `debug_orchestrated_indicators.py` - Add IndicatorCalculationService
4. ⏭️ Create `debug_orchestrated_strategies.py` - Add StrategyEvaluationService
5. ⏭️ Run `main_orchestrated.py` - Full system

## Date

2025-01-07
