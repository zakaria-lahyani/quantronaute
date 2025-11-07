# Enhancement: Detailed Debug Logging

## Overview

Added comprehensive debug logging throughout the trading system to help track data flow and debug issues at each step of the trading cycle.

## Changes Made

### 1. DataFetchingService - Enhanced Fetch Logging

**Location**: `app/services/data_fetching.py`

**Added Logging**:

```
🔄 [FETCH START] XAUUSD 1 - Requesting 3 bars...
✅ [FETCH SUCCESS] XAUUSD 1 - Received 3 bars | Latest: time=2025-01-07 09:00:00, open=4009.12000, high=4009.45000, low=4008.98000, close=4009.23000, volume=245
📤 [EVENT] DataFetchedEvent published for XAUUSD 1

🆕 [NEW CANDLE] XAUUSD 1 | Old: time=2025-01-07 08:59:00, close=4008.99000 → New: time=2025-01-07 09:00:00, close=4009.23000
📤 [EVENT] NewCandleEvent published for XAUUSD 1

⏸️  [NO NEW CANDLE] XAUUSD 5 - Same as previous

❌ [FETCH FAILED] XAUUSD 15 - Empty data received
```

**What You'll See**:
- **Fetch start**: When data request begins
- **Fetch success**: Complete OHLCV data for the latest bar
- **New candle detected**: Comparison of old vs new candle with timestamps and close prices
- **No new candle**: When the candle hasn't changed
- **Fetch failed**: When data fetch fails

### 2. IndicatorCalculationService - Enhanced Indicator Logging

**Location**: `app/services/indicator_calculation.py`

**Added Logging**:

```
📊 [INDICATOR START] XAUUSD 1 | Bar: time=2025-01-07 09:00:00, close=4009.23000

🎯 [REGIME] XAUUSD 1 | regime=trending, confidence=0.85, is_transition=False, changed=False (prev=trending)

✅ [INDICATOR SUCCESS] XAUUSD 1 | Recent rows available: 6, regime=trending
```

**What You'll See**:
- **Indicator start**: Which bar is being processed
- **Regime detection**: Current regime, confidence, transition state, and if it changed
- **Indicator success**: Number of recent rows available after processing

### 3. StrategyEvaluationService - Enhanced Strategy Logging

**Location**: `app/services/strategy_evaluation.py`

**Added Logging**:

```
🎲 [STRATEGY START] XAUUSD | Available rows per TF: {'1': 6, '5': 6, '15': 6}

📈 [STRATEGY EVAL] XAUUSD | Evaluated 1 strategies

💡 [TRADE DECISIONS] XAUUSD | Entries: 0, Exits: 1

🟢 [ENTRY SIGNAL] anchors-transitions-and-htf-bias | long XAUUSD @ 4009.23

🔴 [EXIT SIGNAL] anchors-transitions-and-htf-bias | long XAUUSD
```

**What You'll See**:
- **Strategy start**: How many rows are available for each timeframe
- **Strategy evaluation**: Number of strategies evaluated
- **Trade decisions**: How many entry and exit signals were generated
- **Entry signals**: Strategy name, direction, symbol, and price
- **Exit signals**: Strategy name, direction, and symbol

## Benefits

### 1. **Complete Data Flow Visibility**
You can now track a single trading cycle from start to finish:
```
🔄 [FETCH START] → ✅ [FETCH SUCCESS] → 🆕 [NEW CANDLE] →
📊 [INDICATOR START] → 🎯 [REGIME] → ✅ [INDICATOR SUCCESS] →
🎲 [STRATEGY START] → 📈 [STRATEGY EVAL] → 💡 [TRADE DECISIONS] →
🔴 [EXIT SIGNAL]
```

### 2. **Easy Debugging**
- Identify at which step data flow breaks
- See exact values at each step (OHLCV, regime, signals)
- Compare old vs new candles to verify new candle detection
- Verify regime detection and changes

### 3. **Performance Monitoring**
- See how many rows are available for strategy evaluation
- Track which timeframes have new candles
- Monitor strategy evaluation frequency

### 4. **Visual Markers**
Emoji markers make it easy to scan logs:
- 🔄 Fetch operations
- ✅ Success
- ❌ Failures
- 🆕 New candles
- ⏸️ No change
- 📊 Indicators
- 🎯 Regime
- 🎲 Strategy
- 💡 Trade decisions
- 🟢 Entry signals
- 🔴 Exit signals
- 📤 Events published

## Example Log Output

```
2025-01-07 09:00:30 INFO services.DataFetchingService: 🔄 [FETCH START] XAUUSD 1 - Requesting 3 bars...
2025-01-07 09:00:30 INFO services.DataFetchingService: ✅ [FETCH SUCCESS] XAUUSD 1 - Received 3 bars | Latest: time=2025-01-07 09:00:00, open=4009.12000, high=4009.45000, low=4008.98000, close=4009.23000, volume=245
2025-01-07 09:00:30 INFO services.DataFetchingService: 🆕 [NEW CANDLE] XAUUSD 1 | Old: time=2025-01-07 08:59:00, close=4008.99000 → New: time=2025-01-07 09:00:00, close=4009.23000
2025-01-07 09:00:30 INFO services.IndicatorCalculationService: 📊 [INDICATOR START] XAUUSD 1 | Bar: time=2025-01-07 09:00:00, close=4009.23000
2025-01-07 09:00:30 INFO services.IndicatorCalculationService: 🎯 [REGIME] XAUUSD 1 | regime=trending, confidence=0.85, is_transition=False, changed=False (prev=trending)
2025-01-07 09:00:30 INFO services.IndicatorCalculationService: ✅ [INDICATOR SUCCESS] XAUUSD 1 | Recent rows available: 6, regime=trending
2025-01-07 09:00:30 INFO services.StrategyEvaluationService: 🎲 [STRATEGY START] XAUUSD | Available rows per TF: {'1': 6, '5': 6, '15': 6}
2025-01-07 09:00:30 INFO services.StrategyEvaluationService: 📈 [STRATEGY EVAL] XAUUSD | Evaluated 1 strategies
2025-01-07 09:00:30 INFO services.StrategyEvaluationService: 💡 [TRADE DECISIONS] XAUUSD | Entries: 0, Exits: 1
2025-01-07 09:00:30 INFO services.StrategyEvaluationService: 🔴 [EXIT SIGNAL] anchors-transitions-and-htf-bias | long XAUUSD
```

## Files Modified

1. **[app/services/data_fetching.py](../app/services/data_fetching.py)** - Lines 200-270
2. **[app/services/indicator_calculation.py](../app/services/indicator_calculation.py)** - Lines 244-289
3. **[app/services/strategy_evaluation.py](../app/services/strategy_evaluation.py)** - Lines 248-336

## Usage

The enhanced logging is automatically enabled when you run `main_orchestrated.py`. The logs will show in your console and in the JSON log format if configured.

To see more detailed logs, set the logging level to INFO or DEBUG in `config/services.yaml`:

```yaml
logging:
  level: INFO  # or DEBUG for even more details
  format: json  # or text
```

## Date

2025-01-07
