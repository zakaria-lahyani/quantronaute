# Debug Tool: Full Orchestrated Pipeline

## Overview

The complete orchestrated debug script that runs **all four services** with comprehensive trade execution logging. This shows the entire pipeline: Data → Indicators → Strategies → Trade Execution.

## Differences from Previous Debug Scripts

| Feature | `debug_orchestrated_strategies.py` | `debug_orchestrated_full.py` |
|---------|-----------------------------------|------------------------------|
| Services | Data + Indicators + Strategies | Data + Indicators + Strategies + **Trades** |
| Events | Entry/Exit signals only | All trade execution events |
| Trade Executor | Not included | **Included** |
| Order Execution | Not shown | **Shown** |
| Risk Management | Not shown | **Shown** |
| Trading Blocks | Not shown | **Shown (news, market close, risk)** |
| Complexity | Near production | **Full production** |

## What It Shows

### 1. **Entry/Exit Signals** (from StrategyEvaluationService)
```
🟢 ═══════════════════════════════════════════════════════
🟢 ENTRY SIGNAL #1
🟢 ═══════════════════════════════════════════════════════
   Strategy: MeanReversionV3
   Symbol:   XAUUSD
   Direction: BUY
   Price:    4009.23000
🟢 ═══════════════════════════════════════════════════════

🔴 ═══════════════════════════════════════════════════════
🔴 EXIT SIGNAL #1
🔴 ═══════════════════════════════════════════════════════
   Strategy: MeanReversionV3
   Symbol:   XAUUSD
   Direction: BUY
   Reason:   stop_loss
🔴 ═══════════════════════════════════════════════════════
```

### 2. **Trading Authorization** (from TradeExecutionService)
```
✅ ═══════════════════════════════════════════════════════
✅ TRADING AUTHORIZED #1
✅ ═══════════════════════════════════════════════════════
   Symbol: XAUUSD
   Reason: all_checks_passed
✅ ═══════════════════════════════════════════════════════
```

### 3. **Trading Blocked** (from TradeExecutionService)
```
🚫 ═══════════════════════════════════════════════════════
🚫 TRADING BLOCKED #1
🚫 ═══════════════════════════════════════════════════════
   Symbol:  XAUUSD
   Reasons: news_block, market_closing
🚫 ═══════════════════════════════════════════════════════
```

### 4. **Risk Limit Breach** (from TradeExecutionService)
```
⚠️  ═══════════════════════════════════════════════════════
⚠️  RISK LIMIT BREACHED #1
⚠️  ═══════════════════════════════════════════════════════
   Symbol:        XAUUSD
   Limit Type:    daily_loss
   Current Value: -1500.00
   Limit Value:   -1000.00
⚠️  ═══════════════════════════════════════════════════════
```

### 5. **Order Placed** (from TradeExecutionService)
```
📤 ═══════════════════════════════════════════════════════
📤 ORDER PLACED #1
📤 ═══════════════════════════════════════════════════════
   Order ID:  12345678
   Symbol:    XAUUSD
   Direction: BUY
   Volume:    0.10
   Price:     4009.23000
   Stop Loss: 4008.50000
   Take Profit: 4010.50000
📤 ═══════════════════════════════════════════════════════
```

### 6. **Order Rejected** (from TradeExecutionService)
```
❌ ═══════════════════════════════════════════════════════
❌ ORDER REJECTED #1
❌ ═══════════════════════════════════════════════════════
   Symbol:    XAUUSD
   Direction: BUY
   Reason:    insufficient_margin
❌ ═══════════════════════════════════════════════════════
```

### 7. **Position Closed** (from TradeExecutionService)
```
🔒 ═══════════════════════════════════════════════════════
🔒 POSITION CLOSED #1
🔒 ═══════════════════════════════════════════════════════
   Position ID: 87654321
   Symbol:      XAUUSD
   Profit:      +45.50
   Reason:      take_profit
🔒 ═══════════════════════════════════════════════════════
```

### 8. **Complete Metrics**
```
📊 Metrics Summary:
   ├─ Data fetches:          15
   ├─ New candles:           3
   ├─ Indicators calculated: 15
   ├─ Regime changes:        1
   ├─ Strategies evaluated:  6
   ├─ Entry signals:         2 (Total: 2)
   ├─ Exit signals:          1 (Total: 1)
   ├─ Trades executed:       3
   ├─ Orders placed:         2
   ├─ Orders rejected:       0
   ├─ Positions closed:      1
   ├─ Trading authorized:    3
   ├─ Trading blocked:       0
   └─ Risk breaches:         0
```

## Usage

### Run the Debug Script

```bash
python -m app.debug_orchestrated_full
```

### What You'll See

```
================================================================================
🔍 ORCHESTRATED DEBUG: FULL PIPELINE (DATA + INDICATORS + STRATEGIES + TRADES)
================================================================================

📁 Loading configuration from: ...

⚙️  Configuration:
   Symbol: XAUUSD
   API URL: http://127.0.0.1:8000

🔌 Connecting to MT5 API...
   ✅ Connected successfully

📊 Initializing data source manager...
   ✅ Data source initialized

🎯 Loading strategy configuration...
   ✅ Loaded 2 strategies: ['MeanReversionV3', 'TrendFollowingV2']

   ✅ Entry manager created

📈 Loading indicator configuration...
   ✅ Loaded indicators for timeframes: ['1', '5', '15']

📚 Fetching historical data for indicator initialization...
   ✅ 1: 500 historical bars
   ✅ 5: 500 historical bars
   ✅ 15: 500 historical bars

🧮 Initializing indicator processor...
   ✅ Indicator processor initialized

🎯 Initializing regime manager...
   ✅ Regime manager initialized

💼 Initializing trade executor...
   ✅ Trade executor initialized

🚌 Creating EventBus...
   ✅ EventBus created and subscribed to all events

📄 Loading service configuration...
   ✅ Loaded config from: config/services.yaml

🔄 Creating DataFetchingService...
   ✅ DataFetchingService created

🧮 Creating IndicatorCalculationService...
   ✅ IndicatorCalculationService created

🎲 Creating StrategyEvaluationService...
   ✅ StrategyEvaluationService created

💼 Creating TradeExecutionService...
   ✅ TradeExecutionService created

▶️  Starting services...
   ✅ All services started

================================================================================
🚀 STARTING FULL PIPELINE: DATA → INDICATORS → STRATEGIES → TRADES
================================================================================
Press Ctrl+C to stop

────────────────────────────────────────────────────────────────────────────────
📍 ITERATION 1 - 2025-01-07 10:30:00
────────────────────────────────────────────────────────────────────────────────

🔄 Fetching data for all timeframes...

   🟢 ═══════════════════════════════════════════════════════
   🟢 ENTRY SIGNAL #1
   🟢 ═══════════════════════════════════════════════════════
      Strategy: MeanReversionV3
      Symbol:   XAUUSD
      Direction: BUY
      Price:    4009.23000
   🟢 ═══════════════════════════════════════════════════════

   ✅ ═══════════════════════════════════════════════════════
   ✅ TRADING AUTHORIZED #1
   ✅ ═══════════════════════════════════════════════════════
      Symbol: XAUUSD
      Reason: all_checks_passed
   ✅ ═══════════════════════════════════════════════════════

   📤 ═══════════════════════════════════════════════════════
   📤 ORDER PLACED #1
   📤 ═══════════════════════════════════════════════════════
      Order ID:  12345678
      Symbol:    XAUUSD
      Direction: BUY
      Volume:    0.10
      Price:     4009.23000
      Stop Loss: 4008.50000
      Take Profit: 4010.50000
   📤 ═══════════════════════════════════════════════════════

✅ Pipeline triggered: 3/3 timeframes

📊 Metrics Summary:
   ├─ Data fetches:          3
   ├─ New candles:           1
   ├─ Indicators calculated: 3
   ├─ Regime changes:        0
   ├─ Strategies evaluated:  2
   ├─ Entry signals:         1 (Total: 1)
   ├─ Exit signals:          0 (Total: 0)
   ├─ Trades executed:       1
   ├─ Orders placed:         1
   ├─ Orders rejected:       0
   ├─ Positions closed:      0
   ├─ Trading authorized:    1
   ├─ Trading blocked:       0
   └─ Risk breaches:         0

⏳ Waiting 30 seconds before next fetch...
────────────────────────────────────────────────────────────────────────────────
```

## Benefits

### 1. **Complete Pipeline Validation**
- ✅ Data fetching works
- ✅ Indicators calculate correctly
- ✅ Strategies generate signals
- ✅ **Trades execute successfully**
- ✅ **Risk management works**
- ✅ **Trading blocks are respected**

### 2. **Trade Execution Visibility**
See exactly what happens during trade execution:
- Trading authorization checks
- News blocks and market closing blocks
- Risk limit breaches
- Order placement success/failure
- Position closures with profit/loss

### 3. **Full Event Flow**
Track complete event flow:
```
DataFetchedEvent
  → NewCandleEvent
    → IndicatorsCalculatedEvent
      → EntrySignalEvent
        → TradingAuthorizedEvent
          → OrderPlacedEvent
```

### 4. **Production-Ready Testing**
This is the closest to the actual production system:
- All four services running
- Full event-driven architecture
- Complete error handling
- Comprehensive metrics

## Configuration

The script uses `config/services.yaml`:

```yaml
services:
  trade_execution:
    enabled: true
    execution_mode: "immediate"  # "immediate" or "batch"
    batch_size: 1  # only used in batch mode
```

### Execution Modes

**Immediate Mode** (recommended):
- Executes trades as soon as signals are received
- Lower latency
- Better for live trading

**Batch Mode**:
- Collects signals and executes in batches
- Useful for testing or specific strategies
- Controlled via `batch_size`

## What to Validate

### 1. **Service Initialization**
```
✅ Trade executor initialized
✅ TradeExecutionService created
✅ All services started
```

### 2. **Signal → Execution Flow**
You should see this sequence:
1. Entry signal generated
2. Trading authorization checked
3. Order placed (if authorized)

### 3. **Trading Blocks Respected**
When trading is blocked:
```
🚫 TRADING BLOCKED
   Reasons: news_block, market_closing
```

No orders should be placed during blocks.

### 4. **Risk Limits Enforced**
When risk limits breached:
```
⚠️  RISK LIMIT BREACHED
   Current Value: -1500.00
   Limit Value:   -1000.00
```

No new orders should be placed after breach.

### 5. **Order Success Rate**
```
Orders placed:   5
Orders rejected: 1
Success rate:    83%
```

High rejection rate indicates issues with:
- Insufficient margin
- Invalid order parameters
- Broker connectivity

### 6. **Position Management**
```
Entry signals:    5
Positions closed: 3
Open positions:   2
```

Verify positions are closed correctly.

## Trading Context

The TradeExecutionService checks multiple conditions before executing:

### 1. **News Block**
- Checks if major news events are scheduled
- Blocks trading during high-impact news

### 2. **Market Closing**
- Checks if market is about to close
- Prevents opening positions near closing time

### 3. **Risk Management**
- Checks daily loss limit
- Checks max open positions
- Checks max position size per trade

### 4. **Broker Availability**
- Verifies connection to broker
- Validates account status

## Troubleshooting

### No Orders Placed

If you see entry signals but no orders:

**Check 1**: Trading authorized?
```
✅ TRADING AUTHORIZED
```
If you see `🚫 TRADING BLOCKED` instead, check the reasons.

**Check 2**: Risk limits?
```
⚠️  RISK LIMIT BREACHED
```
Adjust risk limits in config or reset account.

**Check 3**: Broker connection?
```
❌ Connection failed
```
Verify MT5 API is running and accessible.

### High Rejection Rate

If many orders are rejected:

**Issue**: Insufficient margin
```
❌ ORDER REJECTED
   Reason: insufficient_margin
```
**Solution**: Reduce position size or increase account balance.

**Issue**: Invalid parameters
```
❌ ORDER REJECTED
   Reason: invalid_stops
```
**Solution**: Check SL/TP calculation in EntryManager.

### Orders Placed But No Positions

If orders are placed but positions don't open:

**Check**: Order type
- Market orders execute immediately
- Pending orders wait for price

**Check**: Broker logs
- Look at MT5 terminal for rejection reasons
- Check journal for detailed error messages

### Positions Not Closing

If exit signals generate but positions stay open:

**Check**: Position ID matching
```
🔒 POSITION CLOSED
   Position ID: 87654321
```
Verify position IDs match between signals and actual positions.

**Check**: Exit signal processing
Look for errors in TradeExecutionService logs.

## Metrics Interpretation

### Good Metrics Example
```
Data fetches:          60
New candles:           12
Strategies evaluated:  24
Entry signals:         5
Trades executed:       5
Orders placed:         5
Orders rejected:       0
Trading blocked:       2
Risk breaches:         0
```

This shows:
- ✅ All entry signals executed successfully
- ✅ No order rejections
- ✅ Trading blocks respected (news/market close)
- ✅ No risk breaches

### Problem Metrics Example
```
Entry signals:         10
Trades executed:       3
Orders placed:         3
Orders rejected:       7
Risk breaches:         2
```

This indicates:
- ❌ 70% rejection rate (7/10 orders rejected)
- ❌ Risk management issues (2 breaches)
- ❌ Need to investigate order rejection reasons

## Files

- **[app/debug_orchestrated_full.py](../app/debug_orchestrated_full.py)** - Main debug script
- **[app/services/trade_execution.py](../app/services/trade_execution.py)** - TradeExecutionService implementation
- **[config/services.yaml](../config/services.yaml)** - Service configuration

## Progression Path

1. ✅ `debug_data_fetch.py` - Validate raw data fetching
2. ✅ `debug_orchestrated_fetch.py` - Validate DataFetchingService + events
3. ✅ `debug_orchestrated_indicators.py` - Add IndicatorCalculationService
4. ✅ `debug_orchestrated_strategies.py` - Add StrategyEvaluationService
5. ✅ `debug_orchestrated_full.py` - Add TradeExecutionService ← **You are here**
6. ⏭️ Run `main_orchestrated.py` - Full production system

## Next Steps

Once trade execution is validated:

1. ✅ All services work independently
2. ✅ Event flow is correct
3. ✅ Trades execute successfully
4. ✅ Risk management works
5. → Run full `main_orchestrated.py` for production

## Important Notes

### Execution Mode

The script uses `execution_mode: "immediate"` which means:
- Trades execute as soon as signals are received
- No batching or delays
- Best for live trading

If you want batch execution:
```python
trade_config = {
    'execution_mode': 'batch',
    'batch_size': 5,  # Execute after 5 signals collected
}
```

### Event Order

Events are published in this order:
1. `EntrySignalEvent` or `ExitSignalEvent`
2. `TradingAuthorizedEvent` or `TradingBlockedEvent`
3. `RiskLimitBreachedEvent` (if applicable)
4. `OrderPlacedEvent` or `OrderRejectedEvent`
5. `PositionClosedEvent` (for exits)

### Metrics Reset

Metrics accumulate during the session. To reset:
- Stop the script (Ctrl+C)
- Restart it

Or add a reset mechanism if needed.

## Date

2025-01-07
