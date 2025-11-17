# Account Types Documentation

## Overview

The Quantronaute trading system supports different account types that determine how positions and orders are managed, especially around market closing times and risk management. The `ACCOUNT_TYPE` configuration parameter controls this behavior.

---

## Supported Account Types

### 1. **Daily** (`ACCOUNT_TYPE=daily`)

#### Description
Daily accounts are designed for **intraday trading challenges** or accounts with strict daily trading windows. All positions and orders are automatically closed at the end of each trading day.

#### Key Characteristics

**✅ Automatic Daily Closure:**
- All open positions are automatically closed before market close
- All pending orders are automatically canceled before market close
- Ensures no overnight exposure or risk

**⏰ Market Close Detection:**
- Monitors market closing times based on `DEFAULT_CLOSE_TIME` configuration
- Checks for holiday-specific close times from `holidays.csv`
- Triggers closure during `MARKET_CLOSE_RESTRICTION_DURATION` window (default: before close time)

**🚫 Trading Restrictions:**
- Trading is blocked when market closing is detected
- No new positions or orders are placed near market close
- Suspensions from news events are cleared during daily closure

#### Configuration Example

```bash
# .env.broker
ACCOUNT_TYPE=daily

# Trading and Risk Configuration
SYMBOLS=XAUUSD,BTCUSD
DAILY_LOSS_LIMIT=5000

# Market Closing Configuration
DEFAULT_CLOSE_TIME=16:55:00           # Daily close time (e.g., 4:55 PM)
MARKET_CLOSE_RESTRICTION_DURATION=30   # Stop trading 30 minutes before close
```

#### Configuration Files Required

1. **config/holidays.csv** - Special market close times for holidays
   ```csv
   Instrument,Dates
   XAUUSD,2024-12-25 14:00:00
   BTCUSD,2024-12-25 14:00:00
   ```

2. **config/economic-calendar.csv** - News events (shared with swing accounts)

#### Use Cases

- ✅ **FTMO Daily Challenges** - No overnight positions allowed
- ✅ **Prop Firm Daily Accounts** - Must close all positions daily
- ✅ **Day Trading Strategies** - Intraday trading only
- ✅ **Risk-Averse Trading** - Avoid overnight gap risk

#### Daily Account Workflow

```
08:00  ┌─────────────────────────────────────────────┐
       │ Trading Session Starts                      │
       │ - News blocks active when detected          │
       │ - Normal trading operations                 │
       └─────────────────────────────────────────────┘

16:25  ┌─────────────────────────────────────────────┐
       │ Market Close Detection Triggered            │
       │ (30 minutes before DEFAULT_CLOSE_TIME)      │
       └─────────────────────────────────────────────┘

16:25  ┌─────────────────────────────────────────────┐
       │ Automatic Closure Sequence:                 │
       │ 1. Block all new trading                    │
       │ 2. Close all open positions for symbol      │
       │ 3. Cancel all pending orders for symbol     │
       │ 4. Clear suspension store                   │
       └─────────────────────────────────────────────┘

16:55  ┌─────────────────────────────────────────────┐
       │ Market Closed                               │
       │ - All positions closed                      │
       │ - All orders canceled                       │
       │ - Ready for next trading day                │
       └─────────────────────────────────────────────┘
```

---

### 2. **Swing** (`ACCOUNT_TYPE=swing`)

#### Description
Swing accounts are designed for **multi-day trading strategies** where positions can be held overnight or for several days. No automatic daily closure is enforced.

#### Key Characteristics

**📈 Overnight Positions Allowed:**
- Positions can remain open across multiple trading days
- No automatic closure at market close time
- Designed for longer-term strategies

**🔄 Continuous Trading:**
- Market closing time is monitored but does NOT trigger automatic closure
- Trading continues across days based on strategy signals
- Only news events trigger temporary suspensions

**⚡ News Event Handling:**
- Pending orders are temporarily suspended during news events
- Stop Loss and Take Profit are removed during news events
- All suspended items are restored after news event passes
- Suspension store is maintained across trading sessions

#### Configuration Example

```bash
# .env.broker
ACCOUNT_TYPE=swing

# Trading and Risk Configuration
SYMBOLS=XAUUSD,BTCUSD
DAILY_LOSS_LIMIT=5000

# News Restriction Configuration
NEWS_RESTRICTION_DURATION=2  # Block trading 2 minutes before/after news
```

#### Configuration Files Required

1. **config/economic-calendar.csv** - High-impact news events
   ```csv
   Dates,Restrictions
   2024-11-10 14:30:00,1
   2024-11-10 16:00:00,1
   ```

2. **config/holidays.csv** - Optional (monitored but doesn't trigger closure)

#### Use Cases

- ✅ **Swing Trading Strategies** - Hold positions for days/weeks
- ✅ **FTMO Swing/Challenge Accounts** - Multi-day position holding
- ✅ **Trend Following Systems** - Long-term trend capture
- ✅ **Position Trading** - Fundamental-based longer-term trades

#### Swing Account Workflow

```
Day 1
08:00  ┌─────────────────────────────────────────────┐
       │ Trading Session Starts                      │
       │ - Normal trading operations                 │
       │ - Entry signals executed                    │
       └─────────────────────────────────────────────┘

14:28  ┌─────────────────────────────────────────────┐
       │ High-Impact News Event Detected             │
       │ (2 minutes before NFP release)              │
       └─────────────────────────────────────────────┘

14:28  ┌─────────────────────────────────────────────┐
       │ News Protection Sequence:                   │
       │ 1. Block new trading                        │
       │ 2. Suspend all pending orders               │
       │ 3. Remove SL/TP from positions              │
       │ 4. Store suspension data for restoration    │
       └─────────────────────────────────────────────┘

14:32  ┌─────────────────────────────────────────────┐
       │ News Event Ended                            │
       │ (2 minutes after release)                   │
       └─────────────────────────────────────────────┘

14:32  ┌─────────────────────────────────────────────┐
       │ Restoration Sequence:                       │
       │ 1. Restore all pending orders               │
       │ 2. Restore SL/TP on positions               │
       │ 3. Clear suspension store                   │
       │ 4. Allow trading                            │
       └─────────────────────────────────────────────┘

16:55  ┌─────────────────────────────────────────────┐
       │ Market Close Time Reached                   │
       │ - NO automatic closure                      │
       │ - Positions remain open                     │
       │ - Orders remain active                      │
       └─────────────────────────────────────────────┘

Day 2
08:00  ┌─────────────────────────────────────────────┐
       │ Next Trading Session                        │
       │ - Positions still open from Day 1           │
       │ - Continue trading based on strategy        │
       └─────────────────────────────────────────────┘
```

---

## Comparison Table

| Feature | Daily Account | Swing Account |
|---------|--------------|---------------|
| **Overnight Positions** | ❌ Not allowed | ✅ Allowed |
| **Automatic Daily Closure** | ✅ Yes, before market close | ❌ No automatic closure |
| **Market Close Detection** | ✅ Triggers closure | ℹ️ Monitored only |
| **News Event Suspension** | ✅ Yes | ✅ Yes |
| **Pending Order Handling** | Canceled at close | Restored after news |
| **SL/TP During News** | Removed at close | Removed during news, restored after |
| **Suspension Store** | Cleared at close | Maintained across sessions |
| **Trading Window** | Single day | Multiple days |
| **Risk Management** | Daily reset | Continuous monitoring |
| **Best For** | Day trading, FTMO Daily | Swing trading, trend following |

---

## Code Implementation Details

### Daily Account Behavior

From [restriction_manager.py:74-88](c:\Users\zak\Desktop\workspace\project\trading\quantronaute\app\trader\managers\restriction_manager.py#L74-L88):

```python
def _apply_market_closing_restrictions(self, context: TradingContext) -> None:
    """Handle market closing restrictions for daily accounts."""
    is_closing = self.trade_restriction.is_market_closing_soon(
        self.symbol,
        context.current_time
    )
    context.market_closing_soon = is_closing

    if is_closing and self.account_type == "daily":
        self._on_market_closing(context.market_state)
        context.block_trading("market_closing")
    elif not is_closing and self.account_type == "daily":
        # Allow trading if no news restriction
        if not context.news_block_active:
            context.allow_trading()
```

**Key Points:**
- Market close check is ONLY enforced for `account_type == "daily"`
- Triggers `_on_market_closing()` which closes positions and cancels orders
- Blocks trading when market closing is detected

### Swing Account Behavior

For swing accounts, the market closing check passes through without triggering closure:

```python
if is_closing and self.account_type == "daily":  # This condition is FALSE for swing
    # Closure logic not executed
```

**Result:** Swing accounts ignore market closing times and maintain positions/orders.

---

## Market Close Time Detection

From [trade_restriction.py:42-96](c:\Users\zak\Desktop\workspace\project\trading\quantronaute\app\trader\managers\trade_restriction.py#L42-L96):

### Close Time Priority

1. **Holiday-specific close time** (from `holidays.csv`)
2. **Default close time** (from `DEFAULT_CLOSE_TIME` config)
3. **Fallback** to default if holiday file load fails

### Time Window Calculation

```python
if default_close_time - timedelta(minutes=MARKET_CLOSE_RESTRICTION_DURATION)
   <= current_time
   <= default_close_time + timedelta(minutes=MARKET_CLOSE_RESTRICTION_DURATION):
    return True  # Market closing soon
```

**Example:**
- `DEFAULT_CLOSE_TIME = 16:55:00`
- `MARKET_CLOSE_RESTRICTION_DURATION = 30`
- **Closure window:** 16:25:00 to 17:25:00

---

## News Event Handling (Both Account Types)

From [restriction_manager.py:56-73](c:\Users\zak\Desktop\workspace\project\trading\quantronaute\app\trader\managers\restriction_manager.py#L56-L73):

### News Block Lifecycle

**1. News Event Start:**
```python
def _on_news_started(self, market_state: MarketState) -> None:
    # Suspend pending orders
    for order in market_state.pending_orders:
        if order.symbol == self.symbol:
            self._suspend_order(order)  # Cancel and store for restoration

    # Suspend position SL/TP
    for position in market_state.open_positions:
        if position.symbol == self.symbol and (position.sl != 0 or position.tp != 0):
            self._suspend_position_protection(position)  # Remove SL/TP, store original values
```

**2. News Event End:**
```python
def _on_news_ended(self) -> None:
    # Restore pending orders (recreate with original parameters)
    for item in self.suspension_store.get_by_kind('pending_order'):
        self._restore_order(item)

    # Restore position SL/TP
    for item in self.suspension_store.get_by_kind('position_sl_tp'):
        self._restore_position_protection(item)

    self.suspension_store.clear()
```

### News Time Window

```python
if event_time - timedelta(minutes=NEWS_RESTRICTION_DURATION)
   <= current_time
   <= event_time + timedelta(minutes=NEWS_RESTRICTION_DURATION):
    return True  # News block active
```

**Example:**
- NFP release at `14:30:00`
- `NEWS_RESTRICTION_DURATION = 2`
- **Block window:** 14:28:00 to 14:32:00

---

## Configuration Parameters

### Required for All Account Types

```bash
# Account type selection
ACCOUNT_TYPE=daily  # or "swing"

# Trading symbols
SYMBOLS=XAUUSD,BTCUSD

# Risk management
DAILY_LOSS_LIMIT=5000

# News restriction
NEWS_RESTRICTION_DURATION=2  # Minutes before/after news event
```

### Daily Account Specific

```bash
# Market closing time (local timezone)
DEFAULT_CLOSE_TIME=16:55:00

# Minutes before/after close time to trigger closure
MARKET_CLOSE_RESTRICTION_DURATION=30

# Configuration paths
RESTRICTION_CONF_FOLDER_PATH=/app/config
```

### Swing Account Specific

No additional parameters required beyond base configuration. Market close parameters are optional (monitored but not enforced).

---

## Best Practices

### For Daily Accounts

1. **Set appropriate close time:**
   ```bash
   DEFAULT_CLOSE_TIME=16:55:00  # 5 minutes before actual market close
   ```

2. **Allow sufficient closure window:**
   ```bash
   MARKET_CLOSE_RESTRICTION_DURATION=30  # 30 minutes to close all positions
   ```

3. **Maintain holiday calendar:**
   - Update `holidays.csv` with special close times
   - Test holiday closure behavior in advance

4. **Monitor closure logs:**
   - Verify all positions close successfully
   - Check for order cancellation failures

### For Swing Accounts

1. **Configure robust news protection:**
   ```bash
   NEWS_RESTRICTION_DURATION=2  # Sufficient time before/after news
   ```

2. **Maintain economic calendar:**
   - Keep `economic-calendar.csv` updated
   - Include all high-impact events (NFP, FOMC, CPI, etc.)

3. **Test news suspension/restoration:**
   - Verify orders are canceled and restored correctly
   - Check SL/TP removal and restoration

4. **Monitor overnight risk:**
   - Set appropriate `DAILY_LOSS_LIMIT`
   - Use wider stop losses for overnight positions

---

## Troubleshooting

### Daily Account Issues

**Problem:** Positions not closing at market close
- **Check:** `ACCOUNT_TYPE=daily` is set correctly
- **Check:** `DEFAULT_CLOSE_TIME` matches broker's close time
- **Check:** Timezone configuration is correct
- **Logs:** Look for `[MARKET CLOSING SOON]` warnings

**Problem:** Positions closing too early/late
- **Adjust:** `MARKET_CLOSE_RESTRICTION_DURATION` parameter
- **Check:** Holiday calendar for special close times

### Swing Account Issues

**Problem:** Orders not restored after news event
- **Check:** `economic-calendar.csv` has `Restrictions=1` for the event
- **Check:** News event time in CSV matches actual event time
- **Logs:** Look for suspension/restoration messages

**Problem:** SL/TP not restored
- **Check:** Position had SL/TP before news event
- **Logs:** Check for restoration errors in logs

---

## Migration Guide

### Switching from Daily to Swing

```bash
# Before
ACCOUNT_TYPE=daily
DEFAULT_CLOSE_TIME=16:55:00
MARKET_CLOSE_RESTRICTION_DURATION=30

# After
ACCOUNT_TYPE=swing
# DEFAULT_CLOSE_TIME=16:55:00  # Optional - not enforced
# MARKET_CLOSE_RESTRICTION_DURATION=30  # Optional
NEWS_RESTRICTION_DURATION=2  # Now critical for swing accounts
```

**Important:**
- Review and update `economic-calendar.csv` with all high-impact events
- Adjust `DAILY_LOSS_LIMIT` for multi-day exposure
- Test news suspension/restoration thoroughly
- Update strategies to handle overnight positions

### Switching from Swing to Daily

```bash
# Before
ACCOUNT_TYPE=swing
NEWS_RESTRICTION_DURATION=2

# After
ACCOUNT_TYPE=daily
DEFAULT_CLOSE_TIME=16:55:00  # Required
MARKET_CLOSE_RESTRICTION_DURATION=30  # Required
NEWS_RESTRICTION_DURATION=2  # Still used
```

**Important:**
- Add `holidays.csv` with special market close times
- Test daily closure sequence before live trading
- Adjust strategies for intraday trading only
- Verify all positions close successfully each day

---

## Related Configuration Files

### Economic Calendar (economic-calendar.csv)

```csv
Dates,Restrictions
2024-11-10 14:30:00,1
2024-11-10 16:00:00,1
2024-11-15 13:30:00,1
```

- **Dates:** Event time in UTC
- **Restrictions:** `1` = block trading, `0` = monitor only

### Holidays Calendar (holidays.csv)

```csv
Instrument,Dates
XAUUSD,2024-12-25 14:00:00
BTCUSD,2024-12-25 14:00:00
XAUUSD,2025-01-01 14:00:00
BTCUSD,2025-01-01 14:00:00
```

- **Instrument:** Trading symbol
- **Dates:** Special close time for that instrument

---

## Summary

- **Daily accounts** = Intraday trading with automatic daily closure
- **Swing accounts** = Multi-day trading with overnight positions allowed
- Both types support news event protection
- Account type is controlled by `ACCOUNT_TYPE` environment variable
- Choose based on trading strategy and account requirements

For more information, see:
- [restriction_manager.py](../app/trader/managers/restriction_manager.py)
- [trade_restriction.py](../app/trader/managers/trade_restriction.py)
- [Configuration Guide](../README.md)
