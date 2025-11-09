# Position Monitor Setup Guide

## Overview

The **PositionMonitorService** has been created to handle multi-target take profit (TP) management. This service monitors open positions and automatically executes partial closes when TP levels are hit.

## Files Created

### 1. Position Events
**File**: [app/events/position_events.py](../app/events/position_events.py)

Events for position monitoring:
- `PositionOpenedEvent` - Published when a position opens
- `TPLevelHitEvent` - Published when price hits a TP level
- `PositionPartiallyClosedEvent` - Published when a portion is closed
- `PositionFullyClosedEvent` - Published when position fully closes
- `StopLossMovedEvent` - Published when SL is moved (e.g., to breakeven)

### 2. Position Monitor Service
**File**: [app/services/position_monitor.py](../app/services/position_monitor.py)

Main service that:
- Tracks open positions with TP targets
- Monitors current prices against TP levels
- Executes partial closes when TPs are hit
- Moves stop loss to breakeven after first TP

### 3. Trades Executed Event
**File**: [app/events/trade_events.py](../app/events/trade_events.py) (updated)

Added `TradesExecutedEvent` to carry TP metadata from trade execution to position monitoring.

---

## Integration Steps

To fully integrate the Position Monitor Service into your trading system, follow these steps:

### Step 1: Update LiveTrader to Publish TradesExecutedEvent

The LiveTrader (or wherever orders are executed) needs to publish `TradesExecutedEvent` after successful order placement.

**Location**: `app/trader/live_trader.py` (or similar)

**Add after successful order execution**:

```python
from app.events.trade_events import TradesExecutedEvent

# After orders are executed successfully
if successful_orders:
    # Extract TP targets from risk_entry_result
    tp_targets = []
    if risk_entry_result.take_profit and risk_entry_result.take_profit.type == 'multi_target':
        tp_targets = [
            {
                "level": target.level,
                "percent": target.percent,
                "move_stop": target.move_stop
            }
            for target in risk_entry_result.take_profit.targets
        ]

    # Publish event
    self.event_bus.publish(
        TradesExecutedEvent(
            symbol=symbol,
            direction="long" if direction == "BUY" else "short",
            total_volume=total_volume_executed,
            order_count=len(successful_orders),
            strategy_name=risk_entry_result.strategy_name,
            metadata={
                "tp_targets": tp_targets,
                "tickets": [order["ticket"] for order in successful_orders],
                "group_id": risk_entry_result.group_id
            }
        )
    )
```

### Step 2: Add PositionMonitorService to Multi-Symbol Orchestrator

**File**: `app/infrastructure/multi_symbol_orchestrator.py`

**Add to service creation** (in `_create_services_for_symbol` method):

```python
# 5. PositionMonitorService
self.logger.info(f"  Creating PositionMonitorService for {symbol}...")
position_monitor_config = {
    "symbol": symbol,
    "check_interval": 1,  # Check every second
    "enable_tp_management": True,
    "enable_sl_management": True
}

from app.services.position_monitor import PositionMonitorService

position_monitor_service = PositionMonitorService(
    event_bus=self.event_bus,
    client=client,
    config=position_monitor_config,
    logger=logging.getLogger(f'position-monitor-{symbol.lower()}')
)
self.services[symbol]['position_monitor'] = position_monitor_service
```

**Update service order**:

```python
# Update in __init__
self.service_order = [
    "data_fetching",
    "indicator_calculation",
    "strategy_evaluation",
    "trade_execution",
    "position_monitor"  # Add this
]
```

**Add position checking to trading loop** (in `run` method):

```python
# In the main trading loop, after fetching data
for symbol in self.symbols:
    # ... existing data fetching code ...

    # Check positions for TP management
    position_monitor = self.services[symbol].get('position_monitor')
    if position_monitor and position_monitor.get_status() == ServiceStatus.RUNNING:
        try:
            position_monitor.check_positions()
        except Exception as e:
            self.logger.error(f"Error checking positions for {symbol}: {e}", exc_info=True)
```

### Step 3: Add MT5 Client Methods for Position Management

The Position Monitor requires these MT5 client methods:

**File**: `app/clients/mt5/api/positions.py`

**Add if not present**:

```python
def close_position_partial(self, ticket: int, volume: float) -> Dict[str, Any]:
    """
    Close a portion of a position.

    Args:
        ticket: Position ticket
        volume: Volume to close (lots)

    Returns:
        Response indicating success or failure
    """
    return self.post(f"positions/{ticket}/close_partial", json_data={"volume": volume})


def modify_position(self, ticket: int, stop_loss: Optional[float] = None,
                   take_profit: Optional[float] = None) -> Dict[str, Any]:
    """
    Modify position SL/TP.

    Args:
        ticket: Position ticket
        stop_loss: New stop loss level
        take_profit: New take profit level

    Returns:
        Response indicating success or failure
    """
    data = {}
    if stop_loss is not None:
        data["sl"] = stop_loss
    if take_profit is not None:
        data["tp"] = take_profit

    return self.post(f"positions/{ticket}/modify", json_data=data)
```

---

## How It Works

### Multi-Target TP Flow

1. **Order Execution**:
   - LiveTrader executes orders with TP targets
   - Publishes `TradesExecutedEvent` with TP metadata

2. **Position Tracking**:
   - PositionMonitorService receives event
   - Creates `PositionTracker` for each position
   - Stores TP targets: `[{level: 107473.71, percent: 80, move_stop: True}, ...]`

3. **Price Monitoring**:
   - Every second, `check_positions()` is called
   - Compares current price vs next TP level
   - For long: `current_price >= tp_level`
   - For short: `current_price <= tp_level`

4. **TP Hit**:
   - Publishes `TPLevelHitEvent`
   - Executes partial close via `close_position_partial()`
   - Publishes `PositionPartiallyClosedEvent`

5. **Stop Loss Management**:
   - If `move_stop=True` for that TP level
   - Moves SL to breakeven (entry price)
   - Publishes `StopLossMovedEvent`

6. **Next TP**:
   - Continues monitoring for next TP level
   - Repeats until all TPs hit or position closed

### Example Scenario

**Position**: BTCUSD Long @ 102,397.17, Volume: 0.10 lots

**TP Targets**:
1. TP1: 107,473.71 (80%, move_stop=True)
2. TP2: 117,709.30 (20%, move_stop=False)

**Flow**:
```
Price reaches 107,473.71:
  → Close 80% (0.08 lots)
  → Move SL to 102,397.17 (breakeven)
  → Remaining: 0.02 lots with SL at entry

Price reaches 117,709.30:
  → Close 20% (0.02 lots)
  → Position fully closed
```

---

## Configuration

### Service Configuration

```yaml
position_monitor:
  check_interval: 1  # Check positions every N seconds
  enable_tp_management: true  # Enable multi-target TP
  enable_sl_management: true  # Enable SL movement
```

### Strategy TP Configuration

Your strategy already generates multi-target TPs. Example from logs:

```python
TakeProfitResult(
    type='multi_target',
    targets=[
        TPLevel(level=107473.71, value=5.0, percent=80.0, move_stop=True),
        TPLevel(level=117709.30, value=15.0, percent=20.0, move_stop=False)
    ]
)
```

---

## Testing

### Manual Testing

1. **Start System**: Run `python app/main_multi_symbol.py`
2. **Wait for Entry**: Let strategy generate entry signal
3. **Monitor Logs**: Watch for position tracking messages
4. **Simulate Price Movement**: Manually move price to TP levels (if demo/test)
5. **Verify TP Execution**: Check partial closes in logs

### Expected Log Output

```
 [POSITION TRACKED] Ticket: 344503305, Symbol: BTCUSD, Direction: long, Volume: 0.1, TP Targets: 2
🎯 [TP HIT] Ticket: 344503305, TP1: 107473.71, Current: 107475.50
📤 [PARTIAL CLOSE] Ticket: 344503305, Closing 0.08 lots (80%)
 [PARTIAL CLOSE SUCCESS] Profit: $410.22, Remaining: 0.02 lots
🔒 [MOVE SL] Ticket: 344503305, Old SL: 89385.02, New SL: 102397.17 (Breakeven)
 [SL MOVED] Stop loss moved to breakeven
```

---

## Metrics

The PositionMonitorService tracks:
- `positions_monitored`: Total positions tracked
- `tp_levels_hit`: Number of TP levels hit
- `partial_closes_executed`: Number of partial closes
- `stop_losses_moved`: Number of SL movements

Access via:
```python
metrics = orchestrator.get_all_metrics()
position_metrics = metrics['services']['BTCUSD']['position_monitor']
```

---

## Troubleshooting

### Issue: TP Not Executing

**Check**:
1. Is `TradesExecutedEvent` being published? (Check logs)
2. Are TP targets in event metadata?
3. Is PositionMonitorService running? (`service.get_status()`)
4. Is `check_positions()` being called? (Add debug logs)

### Issue: Partial Close Fails

**Check**:
1. Does broker support partial closes?
2. Is volume normalized correctly?
3. Check broker error code in logs

### Issue: SL Not Moving

**Check**:
1. Is `enable_sl_management=True`?
2. Is `move_stop=True` in TP target?
3. Check broker allows SL modification

---

## Next Steps

1.  Position Monitor Service created
2.  Events created
3.  Update LiveTrader to publish `TradesExecutedEvent`
4.  Add PositionMonitorService to orchestrator
5.  Add MT5 client methods
6.  Test with live/demo account

---

## Summary

The Position Monitor infrastructure is **90% complete**. You just need to:

1. **Publish the event** when orders execute (Step 1)
2. **Add the service** to orchestrator (Step 2)
3. **Add MT5 methods** for partial close/modify (Step 3)

Once these 3 steps are done, your multi-target TP will execute automatically! 
