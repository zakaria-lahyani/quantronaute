# Account-Level Stop Loss Guide

This guide explains the account-level stop loss system, which protects your entire trading account across all symbols by automatically stopping trading and closing positions when risk limits are breached.

## Overview

The account-level stop loss is a **global risk management system** that monitors your entire account, not individual symbols. It provides protection against:

- **Excessive daily losses** - Stops trading if daily P&L drops below configured limit
- **Large drawdowns** - Stops trading if account drawdown from peak exceeds threshold
- **Uncontrolled losses** - Automatically closes all positions when limits are breached

### Key Features

-  **Multi-Symbol Aware**: Monitors total P&L across all trading symbols
-  **Automatic Position Closure**: Closes all open positions when limits breached
-  **Service Shutdown**: Stops all trading services automatically
-  **Daily Reset**: Automatically resets daily P&L at configured time
-  **Drawdown Tracking**: Monitors maximum drawdown from peak balance
-  **Manual Controls**: Manual stop/resume functionality
-  **Comprehensive Metrics**: Detailed reporting and monitoring

---

## Quick Start

### 1. Enable Account Stop Loss

Edit [config/services.yaml](../config/services.yaml):

```yaml
risk:
  account_stop_loss:
    enabled: true
    daily_loss_limit: 1000.0  # Stop trading if lose $1000 in a day
    max_drawdown_pct: 10.0  # Stop if account drops 10% from peak
    close_positions_on_breach: true
    stop_trading_on_breach: true
```

### 2. Run the System

The account stop loss is automatically initialized when you start trading:

```bash
python app/main_multi_symbol.py
```

### 3. Monitor Status

The system logs account metrics:

```
Account Metrics: Balance=$9,500.00, Daily P&L=-$500.00, Drawdown=5.00%, Status=active
```

When limit is breached:

```
================================================================================
ACCOUNT STOP LOSS BREACHED!
Daily loss limit breached: -$1,050.00 < -$1,000.00
Current balance: $8,950.00
Starting balance: $10,000.00
Peak balance: $10,000.00
================================================================================
Closing all open positions...
Stopping all trading services...
```

---

## Configuration

### Complete Configuration Options

```yaml
risk:
  account_stop_loss:
    # Enable/disable account stop loss monitoring
    enabled: true

    # Daily Loss Limit
    # Maximum loss allowed in a single trading day (absolute value)
    # Example: 1000.0 means stop trading if lose $1,000 today
    daily_loss_limit: 1000.0

    # Max Drawdown Percentage
    # Maximum drawdown from peak balance (percentage, 0-100)
    # Example: 10.0 means stop trading if account drops 10% from peak
    max_drawdown_pct: 10.0

    # Close All Positions on Breach
    # If true, automatically closes all open positions when limit hit
    close_positions_on_breach: true

    # Stop Trading on Breach
    # If true, stops all trading services when limit hit
    stop_trading_on_breach: true

    # Cooldown Period
    # Minutes to wait before allowing trading again after breach
    # Set to 0 to disable cooldown
    cooldown_period_minutes: 60

    # Daily Reset Time
    # Time of day to reset daily P&L (HH:MM:SS format)
    # Daily loss limit is calculated from this reset point
    daily_reset_time: "00:00:00"

    # Timezone Offset
    # Timezone offset for reset time (e.g., "+03:00" for UTC+3)
    timezone_offset: "+00:00"
```

### Environment Variable Overrides

You can override settings via environment variables:

```bash
# In .env file
RISK_DAILY_LOSS_LIMIT=2000.0
RISK_MAX_DRAWDOWN_PCT=15.0
```

---

## How It Works

### Daily Loss Monitoring

The system tracks your daily P&L from the configured reset time:

```
Starting Balance (at reset): $10,000
Current Balance: $9,200
Daily P&L: -$800
Daily Loss Limit: -$1,000
Status:  Trading allowed ($200 remaining before limit)
```

When daily loss exceeds the limit:

```
Daily P&L: -$1,050
Status:  Daily loss limit breached - trading stopped
```

### Drawdown Monitoring

The system tracks your maximum drawdown from peak balance:

```
Peak Balance: $10,500
Current Balance: $9,500
Drawdown: 9.5%
Max Drawdown Limit: 10.0%
Status:  Trading allowed (0.5% margin remaining)
```

When drawdown exceeds the limit:

```
Drawdown: 10.5%
Status:  Max drawdown breached - trading stopped
```

### Automatic Actions on Breach

When a limit is breached, the system automatically:

1. **Logs the breach** with detailed account metrics
2. **Closes all open positions** (if `close_positions_on_breach: true`)
3. **Stops trading services** (if `stop_trading_on_breach: true`)
4. **Prevents new trades** until reset or manual resumption

---

## Multi-Symbol Behavior

The account stop loss monitors **all symbols together**:

```
XAUUSD: Daily P&L = -$400
BTCUSD: Daily P&L = -$300
EURUSD: Daily P&L = -$400
---------------------------
Total Daily P&L: -$1,100   Limit breached!
```

**What happens:**
- All XAUUSD positions closed
- All BTCUSD positions closed
- All EURUSD positions closed
- All trading services for all symbols stopped

---

## Daily Reset

The system automatically resets daily P&L at the configured time:

```yaml
daily_reset_time: "00:00:00"  # Midnight
timezone_offset: "+03:00"  # UTC+3
```

**Reset behavior:**
- Daily P&L reset to $0
- Daily loss limit becomes active again
- If breached status was `DAILY_LOSS_BREACHED`, status returns to `ACTIVE`
- Drawdown limit remains in effect (not reset daily)

---

## Manual Controls

### Programmatic Control

```python
from app.risk.account_stop_loss import AccountStopLossManager, AccountStopLossConfig

# Create manager
config = AccountStopLossConfig(
    daily_loss_limit=1000.0,
    max_drawdown_pct=10.0
)
manager = AccountStopLossManager(config, client, logger)
manager.initialize(10000.0)

# Update account metrics
manager.update_account_metrics(
    current_balance=9500.0,
    open_positions_count=3,
    total_exposure=15000.0
)

# Check if trading allowed
if manager.is_trading_allowed():
    # Execute trade
    pass
else:
    reason = manager.get_stop_reason()
    print(f"Trading stopped: {reason}")

# Manual stop
manager.manual_stop("Emergency stop requested")

# Manual resume
manager.manual_resume()

# Get metrics
metrics = manager.get_metrics_summary()
print(f"Daily P&L: ${metrics['daily_pnl']:+,.2f}")
print(f"Drawdown: {metrics['current_drawdown_pct']:.2f}%")
```

---

## Metrics and Monitoring

### Get Current Status

```python
metrics = orchestrator.get_all_metrics()
account_metrics = metrics['account_stop_loss']

print(f"Status: {account_metrics['status']}")
print(f"Daily P&L: ${account_metrics['daily_pnl']:+,.2f}")
print(f"Drawdown: {account_metrics['current_drawdown_pct']:.2f}%")
print(f"Daily Loss Remaining: ${account_metrics['daily_loss_remaining']:,.2f}")
```

### Available Metrics

```python
{
    'status': 'active',  # active, daily_loss_breached, drawdown_breached, manually_stopped
    'is_trading_allowed': True,
    'current_balance': 9500.0,
    'starting_balance': 10000.0,
    'peak_balance': 10000.0,
    'daily_pnl': -500.0,
    'daily_pnl_pct': -5.0,
    'current_drawdown_pct': 5.0,
    'daily_loss_limit': 1000.0,
    'max_drawdown_pct': 10.0,
    'daily_loss_remaining': 500.0,
    'drawdown_remaining_pct': 5.0,
    'breach_time': None,  # ISO timestamp if breached
    'breach_reason': None,  # Reason if breached
    'metrics_count': 1250  # Number of metric snapshots collected
}
```

---

## Example Scenarios

### Scenario 1: Daily Loss Limit Hit

**Setup:**
- Starting balance: $10,000
- Daily loss limit: $500

**Timeline:**
```
10:00 - Trade 1: -$200 (Balance: $9,800, Daily P&L: -$200) 
11:00 - Trade 2: -$150 (Balance: $9,650, Daily P&L: -$350) 
12:00 - Trade 3: -$200 (Balance: $9,450, Daily P&L: -$550) 

ACCOUNT STOP LOSS BREACHED!
Daily loss limit breached: -$550 < -$500
Closing 3 open positions...
Stopping all trading services...
```

**Result:**
- All positions closed
- Trading stopped for the day
- Resumes automatically at midnight (next day)

### Scenario 2: Max Drawdown Hit

**Setup:**
- Peak balance: $12,000
- Max drawdown: 15%
- Current balance: $10,200

**Calculation:**
```
Drawdown = (($12,000 - $10,200) / $12,000) × 100 = 15.0% 

ACCOUNT STOP LOSS BREACHED!
Max drawdown breached: 15.0% >= 15.0%
```

**Result:**
- All positions closed immediately
- Trading stopped
- Requires manual resumption (drawdown doesn't auto-reset)

### Scenario 3: Multiple Symbols

**Setup:**
- Daily loss limit: $1,000
- Trading: XAUUSD, BTCUSD, EURUSD

**Trades:**
```
XAUUSD: -$300
BTCUSD: -$400
EURUSD: -$350
------------------
Total: -$1,050 

ACCOUNT STOP LOSS BREACHED!
Closing 2 XAUUSD positions...
Closing 1 BTCUSD position...
Closing 1 EURUSD position...
Stopping all trading services for all symbols...
```

---

## Best Practices

### 1. Set Conservative Limits

Start with conservative limits and adjust based on your risk tolerance:

```yaml
# Conservative (recommended for new systems)
daily_loss_limit: 500.0  # 5% of $10k account
max_drawdown_pct: 10.0

# Moderate
daily_loss_limit: 1000.0  # 10% of $10k account
max_drawdown_pct: 15.0

# Aggressive (use with caution)
daily_loss_limit: 2000.0  # 20% of $10k account
max_drawdown_pct: 20.0
```

### 2. Account for Multiple Symbols

When trading multiple symbols, account for combined exposure:

```yaml
# Trading 3 symbols with $10k account
daily_loss_limit: 1000.0  # Total across all symbols

# NOT per symbol - this is account-level!
```

### 3. Monitor Regularly

Check account metrics frequently:

```python
# In trading loop
if iteration % 10 == 0:  # Every 10 iterations
    metrics = orchestrator.get_all_metrics()['account_stop_loss']
    logger.info(f"Account Status: {metrics['status']}")
    logger.info(f"Daily P&L: ${metrics['daily_pnl']:+,.2f}")
    logger.info(f"Loss Remaining: ${metrics['daily_loss_remaining']:,.2f}")
```

### 4. Test in Demo First

Always test account stop loss in a demo environment first:

```yaml
# Demo testing
daily_loss_limit: 100.0  # Low limit for testing
close_positions_on_breach: true
stop_trading_on_breach: true
```

### 5. Set Up Alerts

Integrate with alerting systems:

```python
if not account_stop_loss.is_trading_allowed():
    reason = account_stop_loss.get_stop_reason()
    send_slack_alert(f"🚨 TRADING STOPPED: {reason}")
    send_email_alert("Account Stop Loss Triggered", reason)
```

---

## Troubleshooting

### Issue: Trading Won't Start

**Cause:** Account stop loss breached and not reset

**Solution:**
```python
# Check status
status = account_stop_loss.get_status()
print(status)  # DAILY_LOSS_BREACHED or DRAWDOWN_BREACHED

# If daily loss - wait for daily reset, or manually resume
account_stop_loss.manual_resume()

# If drawdown - requires manual intervention
account_stop_loss.reset_limits()  # Use with caution!
```

### Issue: Positions Not Closing

**Cause:** `close_positions_on_breach: false`

**Solution:** Enable position closure:
```yaml
account_stop_loss:
  close_positions_on_breach: true
```

### Issue: False Triggers

**Cause:** Limits too tight or balance tracking issues

**Solution:**
- Increase limits
- Check balance fetching logic
- Verify starting balance initialization

---

## FAQ

**Q: Is the daily loss limit per symbol or account-wide?**
A: **Account-wide**. The system monitors total P&L across all symbols.

**Q: What happens to existing positions when stop loss triggers?**
A: If `close_positions_on_breach: true`, all positions across all symbols are closed immediately.

**Q: Can I override the stop loss temporarily?**
A: Yes, use `manual_resume()` or disable via config `enabled: false`.

**Q: Does the system restart automatically after daily reset?**
A: Yes, if the breach was `DAILY_LOSS_BREACHED`. Drawdown breaches require manual reset.

**Q: How often is the account checked?**
A: Every `account_check_interval` seconds (default: 10 seconds).

**Q: Can I have different limits for different symbols?**
A: No, this is account-level. For per-symbol limits, use position sizing and risk management in EntryManager.

---

## Next Steps

- [Multi-Symbol Trading Guide](MULTI_SYMBOL_GUIDE.md)
- [Risk Management Documentation](../app/entry_manager/README.md)
- [Configuration Reference](../config/services.yaml)
