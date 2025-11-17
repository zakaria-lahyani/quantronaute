# Automation Control System

## Overview

The Automation Control System enables runtime control of automated trading without stopping the trading bot. This allows you to pause new position entries while keeping existing stop-loss and take-profit orders active, providing emergency control during volatile market conditions or news events.

**Key Features:**
- Toggle automated trading on/off at runtime
- File-based control interface (Phase 1 - temporary)
- State persistence across application restarts
- Event-driven architecture integration
- Selective blocking: stops new entries, preserves existing SL/TP orders
- Real-time state monitoring and logging

---

## Quick Start

### Basic Usage

1. **Check Current Status:**
   ```bash
   # Write QUERY command to toggle file
   echo "QUERY" > config/toggle_automation.txt

   # Check automation log
   tail -f logs/automation_actions.log
   ```

2. **Disable Automated Trading:**
   ```bash
   # Stop new position entries (SL/TP orders remain active)
   echo "DISABLE" > config/toggle_automation.txt
   ```

3. **Re-enable Automated Trading:**
   ```bash
   # Resume normal automated trading
   echo "ENABLE" > config/toggle_automation.txt
   ```

---

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Event-Driven Flow                        │
└─────────────────────────────────────────────────────────────┘

1. File-Based Control (Phase 1)
   ┌──────────────────────┐
   │ toggle_automation.txt│ ← User writes command (ENABLE/DISABLE/QUERY)
   └──────────┬───────────┘
              │ (polled every 5s)
              ▼
   ┌──────────────────────┐
   │ AutomationFileWatcher│ ← Monitors file for changes
   └──────────┬───────────┘
              │ publishes
              ▼
   ┌──────────────────────┐
   │ ToggleAutomationEvent│ ← Event with action (ENABLE/DISABLE/QUERY)
   └──────────┬───────────┘
              │ received by
              ▼
2. State Management
   ┌──────────────────────────┐
   │ AutomationStateManager   │ ← Manages automation state
   │ - Updates state          │
   │ - Persists to JSON       │
   │ - Creates backups        │
   └──────────┬───────────────┘
              │ publishes
              ▼
   ┌──────────────────────────┐
   │ AutomationStateChanged   │ ← Event with new state
   │ Event                    │
   └──────────┬───────────────┘
              │ received by
              ▼
3. Service Gating
   ┌──────────────────────────┐       ┌──────────────────────────┐
   │ StrategyEvaluationService│       │ TradeExecutionService    │
   │ - Suppresses entry signals│      │ - Rejects entry trades   │
   │ - Allows exit signals    │       │ - Allows exit trades     │
   └──────────────────────────┘       └──────────────────────────┘
```

### Component Responsibilities

1. **AutomationFileWatcher** ([app/infrastructure/automation_file_watcher.py:1](app/infrastructure/automation_file_watcher.py:1))
   - Polls `toggle_automation.txt` every 5 seconds (configurable)
   - Parses commands: ENABLE, DISABLE, QUERY
   - Publishes `ToggleAutomationEvent`
   - Logs all actions with timestamps
   - Implements log rotation (10MB max, 5 files)

2. **AutomationStateManager** ([app/infrastructure/automation_state_manager.py:1](app/infrastructure/automation_state_manager.py:1))
   - Subscribes to `ToggleAutomationEvent`
   - Maintains automation state in memory
   - Persists state to `automation_state.json`
   - Publishes `AutomationStateChangedEvent`
   - Implements atomic file writes with backup rotation
   - Thread-safe state updates

3. **StrategyEvaluationService** ([app/services/strategy_evaluation.py:1](app/services/strategy_evaluation.py:1))
   - Subscribes to `AutomationStateChangedEvent`
   - When automation disabled:
     - Suppresses entry signal publication
     - Continues publishing exit signals
     - Tracks suppressed signals in metrics

4. **TradeExecutionService** ([app/services/trade_execution.py:1](app/services/trade_execution.py:1))
   - Subscribes to `AutomationStateChangedEvent`
   - When automation disabled:
     - Rejects entry trade execution
     - Allows exit trade execution
     - Preserves existing SL/TP orders
     - Publishes `OrderRejectedEvent` for rejected entries
     - Tracks rejections in metrics

---

## Configuration

### Environment Variables

Add these to your `.env.broker` file:

```bash
# ============================================================================
# AUTOMATION CONTROL
# ============================================================================

# Enable/disable automated trading at startup (true/false, 1/0, yes/no, on/off)
# When disabled, no new positions will be opened automatically, but existing
# SL/TP orders remain active. Defaults to 'true' if not specified.
AUTOMATION_ENABLED=true

# Path to JSON file for persisting automation state across restarts
# This file stores whether automation is enabled/disabled
# Default: config/automation_state.json
AUTOMATION_STATE_FILE=config/automation_state.json

# Path to text file for manual toggle control (temporary Phase 1 interface)
# Write "ENABLE", "DISABLE", or "QUERY" to this file to control automation
# Default: config/toggle_automation.txt
AUTOMATION_TOGGLE_FILE=config/toggle_automation.txt

# Enable/disable the file watcher for toggle file monitoring
# Set to 'false' to disable file-based control (e.g., when using API in Phase 2)
# Default: true
AUTOMATION_FILE_WATCHER_ENABLED=true

# File watcher polling interval in seconds (1-60)
# How often the system checks the toggle file for commands
# Lower values = faster response, higher CPU usage
# Default: 5
AUTOMATION_FILE_WATCHER_INTERVAL=5
```

### Docker Configuration

If using Docker, ensure volume mappings for config files:

```yaml
volumes:
  - ./config:/app/config
  - ./logs:/app/logs
```

---

## Command Reference

### Toggle Commands

Write these commands to `config/toggle_automation.txt`:

| Command | Action | Response Time | Description |
|---------|--------|---------------|-------------|
| `ENABLE` | Enable automation | ~5 seconds | Resumes automated trading |
| `DISABLE` | Disable automation | ~5 seconds | Stops new entries, keeps SL/TP active |
| `QUERY` | Query current state | ~5 seconds | Logs current automation status |

**Notes:**
- Commands are case-insensitive (e.g., `enable`, `ENABLE`, `Enable` all work)
- Leading/trailing whitespace is automatically trimmed
- Invalid commands are logged but ignored
- Response time depends on `AUTOMATION_FILE_WATCHER_INTERVAL`

### Examples

```bash
# Disable automation during high-impact news
echo "DISABLE" > config/toggle_automation.txt

# Wait for news event to pass...

# Re-enable automation
echo "ENABLE" > config/toggle_automation.txt

# Check current status
echo "QUERY" > config/toggle_automation.txt
tail -1 logs/automation_actions.log
```

---

## Monitoring and Logging

### Automation Action Log

Location: `logs/automation_actions.log`

**Log Format:**
```
YYYY-MM-DD HH:MM:SS - STATUS - Message
```

**Example Entries:**
```
2025-11-17 14:23:45 - SUCCESS - Command 'DISABLE' processed successfully
2025-11-17 14:23:45 - INFO - Automation state changed: enabled=False, reason='user_request'
2025-11-17 14:25:12 - SUCCESS - Command 'ENABLE' processed successfully
2025-11-17 14:25:12 - INFO - Automation state changed: enabled=True, reason='user_request'
2025-11-17 14:30:00 - SUCCESS - Command 'QUERY' processed successfully
2025-11-17 14:30:00 - INFO - Current automation state: enabled=True
2025-11-17 14:35:22 - ERROR - Invalid command: 'INVALID_COMMAND'
```

### State Persistence File

Location: `config/automation_state.json`

**Format:**
```json
{
  "enabled": true,
  "last_changed": "2025-11-17T14:25:12.123456",
  "reason": "user_request",
  "requested_by": "file_watcher",
  "saved_at": "2025-11-17T14:25:12.456789"
}
```

**Backup Files:**
- `automation_state.json.bak.1` (most recent)
- `automation_state.json.bak.2`
- `automation_state.json.bak.3`
- `automation_state.json.bak.4`
- `automation_state.json.bak.5` (oldest)

### Application Logs

**StrategyEvaluationService logs:**
```
⚠️  [ENTRY SUPPRESSED] breakout_strategy | long XAUUSD - Automation disabled
```

**TradeExecutionService logs:**
```
⚠️  [TRADE EXECUTION REJECTED] XAUUSD | 1 entry trades rejected - Automation disabled | Exits (2) will still be processed
```

**AutomationStateManager logs:**
```
🤖 [AUTOMATION] XAUUSD | State changed: True -> False | Reason: user_request
```

### Metrics

Access via orchestrator metrics endpoint or logs:

**StrategyEvaluationService metrics:**
```json
{
  "entry_signals_generated": 150,
  "entry_signals_suppressed": 23,
  "exit_signals_generated": 45
}
```

**TradeExecutionService metrics:**
```json
{
  "trades_executed": 127,
  "trades_rejected_automation": 23,
  "orders_placed": 127,
  "orders_rejected": 23
}
```

---

## Behavior Details

### What Happens When Automation is Disabled?

**✅ Continues Working:**
- Existing open positions remain active
- Stop-loss orders continue to work
- Take-profit orders continue to work
- Trailing stops continue to update
- Exit signals are processed normally
- Position monitoring continues
- Risk management continues

**❌ Blocked:**
- New entry signal generation (suppressed at StrategyEvaluationService)
- New entry trade execution (rejected at TradeExecutionService)
- Automated position opening
- Scaled entry additions

**📊 Tracking:**
- Suppressed entry signals counted in `entry_signals_suppressed` metric
- Rejected trades counted in `trades_rejected_automation` metric
- All state changes logged with timestamps
- `OrderRejectedEvent` published for each rejected entry

### What Happens When Automation is Re-enabled?

1. **State Change:**
   - `AutomationStateChangedEvent` published immediately
   - All services update their internal state
   - State persisted to `automation_state.json`

2. **Signal Processing Resumes:**
   - Next strategy evaluation will generate entry signals normally
   - No backfilling of missed signals (by design)
   - Fresh market analysis on next tick

3. **Trade Execution Resumes:**
   - Entry trades accepted normally
   - No special handling required

---

## Use Cases

### Emergency Market Conditions

**Scenario:** High-impact news event causing extreme volatility

```bash
# Before news event
echo "DISABLE" > config/toggle_automation.txt

# Monitor existing positions
# SL/TP orders remain active for protection

# After volatility settles (30+ minutes later)
echo "ENABLE" > config/toggle_automation.txt
```

### End of Trading Session

**Scenario:** Prevent new positions near market close

```bash
# 30 minutes before close
echo "DISABLE" > config/toggle_automation.txt

# Existing positions will close via SL/TP or exit signals
# No new entries will be opened

# Next trading day
echo "ENABLE" > config/toggle_automation.txt
```

### Testing and Debugging

**Scenario:** Test strategy changes without live trading

```bash
# Disable automation
echo "DISABLE" > config/toggle_automation.txt

# Make strategy changes
# Restart application

# Verify changes in logs without opening new positions

# Re-enable when ready
echo "ENABLE" > config/toggle_automation.txt
```

### Reaching Daily Loss Limit

**Scenario:** Approaching or exceeding daily loss limit

```bash
# Disable automation to prevent new trades
echo "DISABLE" > config/toggle_automation.txt

# Review open positions
# Allow existing SL/TP to manage risk

# Next trading day (after limit reset)
echo "ENABLE" > config/toggle_automation.txt
```

---

## Troubleshooting

### Command Not Working

**Symptoms:**
- No response after writing command to file
- Automation state doesn't change

**Solutions:**

1. **Check file watcher is enabled:**
   ```bash
   # In .env.broker
   AUTOMATION_FILE_WATCHER_ENABLED=true
   ```

2. **Verify file path:**
   ```bash
   # Default path
   config/toggle_automation.txt

   # Check environment variable
   grep AUTOMATION_TOGGLE_FILE .env.broker
   ```

3. **Wait for polling interval:**
   - Default: 5 seconds
   - Check: `AUTOMATION_FILE_WATCHER_INTERVAL`
   - Max wait time = interval + processing time

4. **Check logs:**
   ```bash
   tail -f logs/automation_actions.log
   ```

5. **Verify file permissions:**
   ```bash
   ls -l config/toggle_automation.txt
   # Should be readable/writable
   ```

### State Not Persisting

**Symptoms:**
- Automation state resets after restart
- State file not updating

**Solutions:**

1. **Check state file path:**
   ```bash
   grep AUTOMATION_STATE_FILE .env.broker
   ```

2. **Verify file permissions:**
   ```bash
   ls -l config/automation_state.json
   # Should be readable/writable
   ```

3. **Check disk space:**
   ```bash
   df -h
   ```

4. **Review application logs:**
   ```bash
   grep "automation" logs/application.log
   ```

### Entries Still Being Created

**Symptoms:**
- New positions opened despite DISABLE command
- Automation appears disabled in logs

**Solutions:**

1. **Verify command was processed:**
   ```bash
   tail -f logs/automation_actions.log
   # Should show: "SUCCESS - Command 'DISABLE' processed successfully"
   ```

2. **Check all symbols:**
   - Each symbol's services receive the state change
   - Check logs for each symbol:
   ```bash
   grep "AUTOMATION" logs/application.log | grep XAUUSD
   grep "AUTOMATION" logs/application.log | grep BTCUSD
   ```

3. **Verify exit vs. entry:**
   - Exit trades continue when automation disabled
   - Check if trades are closing positions (exit) or opening new ones (entry)

4. **Check metrics:**
   ```bash
   # Look for entry_signals_suppressed > 0
   # Look for trades_rejected_automation > 0
   ```

### High CPU Usage

**Symptoms:**
- Increased CPU usage
- System slowdown

**Solutions:**

1. **Increase polling interval:**
   ```bash
   # In .env.broker
   AUTOMATION_FILE_WATCHER_INTERVAL=10  # Increase from 5 to 10 seconds
   ```

2. **Disable file watcher if using API (Phase 2):**
   ```bash
   AUTOMATION_FILE_WATCHER_ENABLED=false
   ```

---

## Best Practices

### 1. Regular Status Checks

```bash
# Create monitoring script
cat > scripts/check_automation.sh << 'EOF'
#!/bin/bash
echo "QUERY" > config/toggle_automation.txt
sleep 6  # Wait for polling + processing
tail -5 logs/automation_actions.log
EOF

chmod +x scripts/check_automation.sh
```

### 2. Pre-News Event Checklist

```bash
# 1. Disable automation
echo "DISABLE" > config/toggle_automation.txt

# 2. Verify state
sleep 6
tail -1 logs/automation_actions.log

# 3. Monitor existing positions
# (use your trading dashboard)

# 4. After event, re-enable
echo "ENABLE" > config/toggle_automation.txt
```

### 3. Safe Restart Procedure

```bash
# 1. Disable automation before maintenance
echo "DISABLE" > config/toggle_automation.txt

# 2. Wait for confirmation
sleep 6
tail -1 logs/automation_actions.log

# 3. Perform maintenance/restart
docker-compose restart

# 4. Verify system health
docker-compose logs -f --tail=50

# 5. Re-enable when ready
echo "ENABLE" > config/toggle_automation.txt
```

### 4. Daily Routine

```bash
# Morning startup
echo "ENABLE" > config/toggle_automation.txt

# Before market close
echo "DISABLE" > config/toggle_automation.txt
```

### 5. Backup State Files

```bash
# Backup automation state regularly
cp config/automation_state.json backups/automation_state_$(date +%Y%m%d_%H%M%S).json
```

---

## Future Enhancements (Phase 2)

**Planned for future releases:**

1. **REST API Interface:**
   - `POST /api/automation/enable`
   - `POST /api/automation/disable`
   - `GET /api/automation/status`

2. **Web Dashboard:**
   - Toggle button in UI
   - Real-time status display
   - Historical state changes

3. **Advanced Features:**
   - Symbol-specific automation control
   - Time-based automation schedules
   - Conditional automation rules
   - Multiple authorization levels

4. **Notifications:**
   - Email alerts on state changes
   - Telegram bot integration
   - SMS notifications (critical events)

---

## Technical Reference

### Events

**ToggleAutomationEvent:**
```python
@dataclass(frozen=True, kw_only=True)
class ToggleAutomationEvent(Event):
    action: AutomationAction  # ENABLE, DISABLE, QUERY
    reason: str
    requested_by: str = "system"
```

**AutomationStateChangedEvent:**
```python
@dataclass(frozen=True, kw_only=True)
class AutomationStateChangedEvent(Event):
    enabled: bool
    previous_state: Optional[bool] = None
    reason: str = "system_initialization"
    changed_at: datetime = None
```

### State File Schema

```json
{
  "enabled": boolean,
  "last_changed": "ISO-8601 timestamp",
  "reason": string,
  "requested_by": string,
  "saved_at": "ISO-8601 timestamp"
}
```

### Log Rotation

- **Automation log:** 10MB max, 5 backup files
- **Format:** `automation_actions.log`, `automation_actions.log.1`, etc.
- **Automatic:** Rotates when 10MB reached

---

## Support

### Questions or Issues?

1. **Check logs:** `logs/automation_actions.log` and `logs/application.log`
2. **Review metrics:** Check service metrics for suppression/rejection counts
3. **Verify configuration:** Ensure all environment variables are set correctly
4. **Test manually:** Use QUERY command to verify file watcher is working

### Related Documentation

- [Event System](./events.md) - Event-driven architecture details
- [Services](./services.md) - Service responsibilities and configuration
- [Configuration](./configuration.md) - Environment variable reference
- [Deployment](./deployment.md) - Docker deployment guide

---

**Document Version:** 1.0
**Last Updated:** 2025-11-17
**Feature Status:** Phase 1 (File-Based Control) - Production Ready
