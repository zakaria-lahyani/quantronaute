# Configuration: Fetch Interval Update

## Issue

The system was fetching data every 5 seconds, which:
1. Overloads the MT5 API with unnecessary requests
2. Wastes resources since M1 (1-minute) candles only change every 60 seconds
3. Could hit API rate limits

## Recommendation

**Change fetch interval from 5 seconds to 30 seconds**

### Reasoning

- **M1 candles** close every 60 seconds
- Fetching every 30 seconds ensures we catch new candles within 30s of them closing
- Reduces API calls by **83%** (from 12 calls/min to 2 calls/min)
- Still responsive enough for trading (30s delay is acceptable)
- Avoids API rate limiting issues

### API Load Comparison

**Before (5-second interval)**:
- API calls per minute: 12
- API calls per hour: 720
- API calls per day: 17,280
- For 3 timeframes: **51,840 API calls/day**

**After (30-second interval)**:
- API calls per minute: 2
- API calls per hour: 120
- API calls per day: 2,880
- For 3 timeframes: **8,640 API calls/day**

**Reduction**: 83% fewer API calls! (51,840 → 8,640)

## Implementation

### Option 1: Update YAML Config (Applied)

Updated `config/services.yaml`:

```yaml
services:
  data_fetching:
    enabled: true
    fetch_interval: 30  # seconds between data fetches (30s to avoid API rate limits)
    retry_attempts: 3
    candle_index: 1
    nbr_bars: 3
```

### Option 2: Environment Variable Override

Add to `.env` file:

```bash
SERVICES_DATA_FETCHING_FETCH_INTERVAL=30
```

Or run with override:

```bash
SERVICES_DATA_FETCHING_FETCH_INTERVAL=30 python -m app.main_orchestrated
```

## Files Modified

1. **[config/services.yaml](../config/services.yaml:8)** - Changed `fetch_interval: 5` to `fetch_interval: 30`
2. **[docs/MIGRATION_GUIDE.md](../docs/MIGRATION_GUIDE.md:541-556)** - Updated FAQ with recommendation

## Verification

When you run `main_orchestrated.py`, you should see:

```
INFO orchestrator: === STARTING TRADING LOOP (interval=30s) ===
```

And in the logs, you'll see fetch requests every 30 seconds instead of every 5 seconds:

```
[08:11:51] HTTP Request: GET .../bars?timeframe=M1
[08:12:21] HTTP Request: GET .../bars?timeframe=M1  ← 30 seconds later
[08:12:51] HTTP Request: GET .../bars?timeframe=M1  ← 30 seconds later
```

## Impact

- ✅ **Reduced API load**: 83% fewer requests
- ✅ **Avoided rate limits**: No more API overload
- ✅ **Still responsive**: 30s delay is acceptable for trading
- ✅ **Better resource usage**: Less CPU and network usage
- ✅ **No missed candles**: 30s interval catches all M1 candles

## Date

2025-01-07
