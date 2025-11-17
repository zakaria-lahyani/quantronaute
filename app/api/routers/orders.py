"""
Signal trigger endpoints (Manual Trading).

Provides API endpoints to trigger entry and exit signals manually.

These endpoints publish EntrySignalEvent and ExitSignalEvent (from strategy_events.py)
with strategy_name="manual". The signals flow through the EXACT same pipeline as
automated strategy signals:
  1. TradeExecutionService receives the signal
  2. EntryManager calculates position sizing, SL, TP based on config
  3. Risk validation is performed
  4. Orders are executed through MT5Client with configured scaling

The only difference from automated trading: the signal source is "API request"
instead of "strategy evaluation". All other logic is identical.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/entry")
async def trigger_entry_signal():
    """
    Trigger a manual entry signal (BUY or SELL).

    Publishes EntrySignalEvent with strategy_name="manual" to the EventBus.
    The system then handles everything exactly as if a strategy generated the signal:
    - Position sizing based on risk config
    - SL calculation (ATR-based, fixed, trailing, etc.)
    - TP calculation with scaling if configured
    - Risk validation (daily loss limits, max positions, etc.)
    - Order execution with configured scaling (multiple entries if configured)

    Request body:
    {
      "symbol": "XAUUSD",
      "direction": "long"
    }

    The system does the rest!
    """
    # TODO: Implement in Task 5.0
    return {"status": "not_implemented"}


@router.post("/exit")
async def trigger_exit_signal():
    """
    Trigger a manual exit signal.

    Publishes ExitSignalEvent with strategy_name="manual" to the EventBus.
    This closes positions using the standard exit logic.

    Request body:
    {
      "symbol": "XAUUSD",
      "direction": "long",  // which direction to exit
      "reason": "manual"     // optional
    }
    """
    # TODO: Implement in Task 5.0
    return {"status": "not_implemented"}


@router.get("/")
async def list_orders():
    """
    List all pending orders.

    Note: In the current system, orders are typically executed immediately
    at market price. This endpoint lists any pending limit/stop orders if
    the broker has them.
    """
    # TODO: Implement in Task 5.0
    return {"status": "not_implemented"}


@router.delete("/{ticket}")
async def cancel_order(ticket: int):
    """Cancel a pending order by ticket number."""
    # TODO: Implement in Task 5.0
    return {"status": "not_implemented"}
