# Manual Trading Configuration

This document explains how to configure risk management for manual trading signals triggered via the API.

## Overview

When you trigger a manual entry signal via the API:
```bash
POST /signals/entry
{
  "symbol": "XAUUSD",
  "direction": "long"
}
```

The system uses a **"manual" strategy configuration** for that symbol to determine:
- Position sizing
- Stop loss placement
- Take profit targets
- Position scaling (if configured)

This ensures manual trades go through the exact same risk management pipeline as automated strategy trades.

## Configuration Location

Manual strategy configs are located at:
```
configs/{broker-name}/strategies/{symbol}/manual.yaml
```

**Examples:**
- `configs/ftmo-swing/strategies/xauusd/manual.yaml`
- `configs/ftmo-swing/strategies/btcusd/manual.yaml`

## Configuration Structure

### Basic Structure

```yaml
name: "manual"
meta:
  version: "1.0.0"
  author: "system"
  description: "Manual trading configuration"

# Required but not used for manual signals
timeframes: ["1"]
entry:
  long:
    mode: all
    conditions: []
  short:
    mode: all
    conditions: []
exit:
  long:
    mode: all
    conditions: []
  short:
    mode: all
    conditions: []

# IMPORTANT: Risk configuration
risk:
  position_sizing:
    type: fixed
    value: 0.5
  sl:
    type: monetary
    value: 500.0
  tp:
    type: multi_target
    targets:
      - value: 1.0
        percent: 50
        move_stop: true
      - value: 2.0
        percent: 50
        move_stop: false
```

## Risk Configuration Options

### Position Sizing

**Type: `fixed`** (lots per trade)
```yaml
position_sizing:
  type: fixed
  value: 0.5  # 0.5 lots per trade
```

**Type: `percentage`** (% of account balance)
```yaml
position_sizing:
  type: percentage
  value: 1.0  # Risk 1% of account balance
```

**Type: `monetary`** (fixed dollar amount)
```yaml
position_sizing:
  type: monetary
  value: 100.0  # Risk $100 per trade
```

### Stop Loss

**Type: `fixed`** (pips)
```yaml
sl:
  type: fixed
  value: 100.0  # 100 pip stop loss
```

**Type: `monetary`** (fixed dollar risk)
```yaml
sl:
  type: monetary
  value: 500.0  # $500 risk per trade
```

**Type: `atr`** (ATR multiplier)
```yaml
sl:
  type: atr
  value: 1.5  # Stop loss at 1.5x ATR
```

**Type: `percentage`** (% of entry price)
```yaml
sl:
  type: percentage
  value: 2.0  # Stop loss at 2% below entry
```

### Take Profit

**Type: `fixed`** (pips)
```yaml
tp:
  type: fixed
  value: 200.0  # 200 pip take profit
```

**Type: `monetary`** (fixed dollar profit target)
```yaml
tp:
  type: monetary
  value: 1000.0  # $1000 profit target
```

**Type: `rr`** (risk:reward ratio)
```yaml
tp:
  type: rr
  value: 2.0  # 2:1 risk:reward ratio
```

**Type: `multi_target`** (multiple take profit levels with scaling)
```yaml
tp:
  type: multi_target
  targets:
    - value: 1.0      # 1:1 R:R
      percent: 50     # Close 50% of position
      move_stop: true # Move SL to breakeven
    - value: 2.0      # 2:1 R:R
      percent: 30     # Close 30% more
      move_stop: false
    - value: 3.0      # 3:1 R:R
      percent: 20     # Close final 20%
      move_stop: false
```

### Optional: Position Scaling

Enable multiple entries with different sizes:

```yaml
scaling:
  enabled: true
  num_entries: 2
  distribution: [60, 40]  # First entry: 60%, Second entry: 40%
```

**Example:**
If `position_sizing.value = 1.0` lot and `num_entries = 2`:
- Entry 1: 0.6 lots (60%)
- Entry 2: 0.4 lots (40%)

## How It Works

### 1. API Request
```bash
POST /signals/entry
{
  "symbol": "XAUUSD",
  "direction": "long"
}
```

### 2. Event Published
```python
EntrySignalEvent(
    strategy_name="manual",  # Uses manual.yaml config
    symbol="XAUUSD",
    direction="long",
    entry_price=2650.25
)
```

### 3. System Processing
The `TradeExecutionService`:
1. Loads `configs/ftmo-swing/strategies/xauusd/manual.yaml`
2. Passes config to `EntryManager`
3. `EntryManager` calculates:
   - Position size based on `risk.position_sizing`
   - Stop loss based on `risk.sl`
   - Take profit based on `risk.tp`
   - Validates against account risk limits
4. Executes orders through MT5Client with calculated parameters

### 4. Result
Orders placed with automatic risk management, just like automated strategies!

## Examples

### Example 1: Conservative Manual Trading

```yaml
risk:
  position_sizing:
    type: percentage
    value: 0.5  # Risk 0.5% per trade
  sl:
    type: atr
    value: 2.0  # Wide stop at 2x ATR
  tp:
    type: rr
    value: 3.0  # Target 3:1 R:R
```

### Example 2: Aggressive Scalping

```yaml
risk:
  position_sizing:
    type: fixed
    value: 1.0  # 1 full lot
  sl:
    type: fixed
    value: 20.0  # 20 pip stop
  tp:
    type: fixed
    value: 40.0  # 40 pip target (2:1 R:R)
```

### Example 3: Swing Trading with Scaling

```yaml
risk:
  position_sizing:
    type: monetary
    value: 200.0  # $200 risk
  sl:
    type: atr
    value: 1.5
  tp:
    type: multi_target
    targets:
      - value: 1.5
        percent: 33
        move_stop: true
      - value: 2.5
        percent: 33
        move_stop: false
      - value: 4.0
        percent: 34
        move_stop: false

scaling:
  enabled: true
  num_entries: 3
  distribution: [40, 30, 30]
```

## Best Practices

1. **Match Automated Strategies**: Keep manual config similar to your automated strategies for consistency
2. **Start Conservative**: Begin with lower position sizing and wider stops
3. **Test First**: Test manual signals in a demo account before live trading
4. **Monitor Results**: Track manual vs automated performance separately
5. **Document Changes**: Keep notes when you modify manual configs

## Troubleshooting

### "Strategy 'manual' not found for symbol XAUUSD"
**Solution**: Create `configs/{broker}/strategies/xauusd/manual.yaml`

### "Risk validation failed: Position size exceeds maximum"
**Solution**: Reduce `position_sizing.value` or check broker risk limits

### "SL calculation failed: Invalid ATR value"
**Solution**: If using `sl.type: atr`, ensure indicators are running and ATR is available

## Template

Use the template file as a starting point:
```bash
cp configs/broker-template/strategies/manual-template.yaml \
   configs/ftmo-swing/strategies/NEWSYMBOL/manual.yaml
```

Then customize the risk parameters for your needs.

## See Also

- [Automation Control](./automation-control.md) - Toggle automated trading
- [API Documentation](./api/README.md) - Full API reference
- [Risk Management](./risk-management.md) - Account-level risk limits
