# Debug Tool: Data Fetch Validator

## Overview

A simple debug script that **only fetches data** from MT5 and displays it in a clear, readable format. This helps you validate that data fetching works correctly before running the full trading system.

## What It Does

1. ✅ Loads configuration from `.env`
2. ✅ Connects to MT5 API
3. ✅ Fetches data for configured timeframes
4. ✅ Displays OHLCV data in readable format
5. ✅ Runs continuously with 30-second intervals
6. ❌ **No indicators**
7. ❌ **No strategies**
8. ❌ **No trading**
9. ❌ **No event system**

Just pure data fetching and display!

## Usage

### Run the Debug Script

```bash
python -m app.debug_data_fetch
```

### What You'll See

```
================================================================================
🔍 DATA FETCH DEBUG TOOL
================================================================================

📁 Loading configuration from: c:\Users\zak\...\quantronaute\.env

⚙️  Configuration:
   Symbol: XAUUSD
   API URL: http://127.0.0.1:8000
   Trade Mode: live
   Timeframes: ['1', '5', '15']

🔌 Connecting to MT5 API...
   ✅ Connected successfully

📊 Initializing data source manager...
   ✅ Data source initialized

================================================================================
🚀 STARTING DATA FETCH TEST
================================================================================

Fetching 3 bars for each timeframe...
Press Ctrl+C to stop

────────────────────────────────────────────────────────────────────────────────
📍 ITERATION 1 - 2025-01-07 09:15:30
────────────────────────────────────────────────────────────────────────────────

🔄 Fetching XAUUSD 1...

📊 Data for XAUUSD 1:
   Rows: 3
   Columns: ['time', 'open', 'high', 'low', 'close', 'tick_volume']

   Latest 3 bars:
────────────────────────────────────────────────────────────────────────────────
   Time: 2025-01-07 09:13:00
   Open:   4009.12000
   High:   4009.45000
   Low:    4008.98000
   Close:  4009.23000
   Volume: 245
────────────────────────────────────────────────────────────────────────────────
   Time: 2025-01-07 09:14:00
   Open:   4009.23000
   High:   4009.56000
   Low:    4009.15000
   Close:  4009.43000
   Volume: 198
────────────────────────────────────────────────────────────────────────────────
   Time: 2025-01-07 09:15:00
   Open:   4009.43000
   High:   4009.67000
   Low:    4009.38000
   Close:  4009.52000
   Volume: 212
────────────────────────────────────────────────────────────────────────────────

🔄 Fetching XAUUSD 5...

📊 Data for XAUUSD 5:
   Rows: 3
   Columns: ['time', 'open', 'high', 'low', 'close', 'tick_volume']

   Latest 3 bars:
────────────────────────────────────────────────────────────────────────────────
   Time: 2025-01-07 09:05:00
   Open:   4008.45000
   High:   4009.12000
   Low:    4008.23000
   Close:  4008.98000
   Volume: 1024
────────────────────────────────────────────────────────────────────────────────
   [... more bars ...]
────────────────────────────────────────────────────────────────────────────────

⏳ Waiting 30 seconds before next fetch...
────────────────────────────────────────────────────────────────────────────────
```

## Configuration

The script uses your existing `.env` file:

```bash
# Required in .env
SYMBOL=XAUUSD
API_BASE_URL=http://127.0.0.1:8000
TRADE_MODE=live

# Optional (defaults to "1,5,15" if not set)
TIMEFRAMES=1,5,15
```

## Customization

### Change Timeframes

Set the `TIMEFRAMES` environment variable:

```bash
# In .env
TIMEFRAMES=1,5,15,30,60

# Or run with override
TIMEFRAMES=1,5,15 python -m app.debug_data_fetch
```

### Change Fetch Interval

Edit the `wait_time` variable in the script (default: 30 seconds):

```python
# In app/debug_data_fetch.py, line ~120
wait_time = 60  # Change to 60 seconds
```

### Change Number of Bars

Edit the `nbr_bars` variable in the script (default: 3):

```python
# In app/debug_data_fetch.py, line ~75
nbr_bars = 5  # Fetch 5 bars instead of 3
```

## What to Check

### 1. **Connection Success**
```
✅ Connected successfully
```
If you see this, MT5 API connection is working.

### 2. **Data Retrieved**
```
📊 Data for XAUUSD 1:
   Rows: 3
```
If you see `Rows: 3`, data is being fetched successfully.

### 3. **Data Quality**
Check that:
- ✅ Timestamps are sequential and correct
- ✅ OHLC prices are reasonable (high > low, etc.)
- ✅ Close prices are changing between iterations
- ✅ Volume values are present

### 4. **Empty Data Warning**
```
⚠️  DataFrame is EMPTY!
```
If you see this, there's a problem with data fetching. Check:
- MT5 API is running
- Symbol exists (XAUUSD vs EURUSD)
- Timeframe is valid (M1, M5, M15, etc.)

## Stopping the Script

Press `Ctrl+C` to stop:

```
🛑 STOPPED BY USER
================================================================================

Completed 5 iterations
✅ Debug session finished successfully
```

## Troubleshooting

### Error: Connection Failed
```
❌ Connection failed: [Errno 111] Connection refused
```
**Solution**: Make sure MT5 API server is running at `http://127.0.0.1:8000`

### Error: .env Not Found
```
❌ ERROR: .env file not found at ...
```
**Solution**: Create `.env` file in project root with required variables

### Error: Empty DataFrame
```
⚠️  DataFrame is EMPTY!
```
**Solution**:
- Check symbol name (should match MT5 symbol exactly)
- Verify timeframe format (use M1, M5, M15, not 1m, 5m, 15m)
- Ensure market is open (if using live mode)

## Files

- **[app/debug_data_fetch.py](../app/debug_data_fetch.py)** - Main debug script

## Next Steps

Once data fetching is validated:

1. ✅ Data fetch works → Test with indicators
2. ✅ Indicators work → Test with strategies
3. ✅ Strategies work → Run full `main_orchestrated.py`

## Date

2025-01-07
