"""
Signal trigger endpoints (Manual Trading).

Provides API endpoints to trigger entry and exit signals manually.

These endpoints publish EntrySignalEvent and ExitSignalEvent (from strategy_events.py)
with strategy_name="manual". The signals flow through the EXACT same pipeline as
automated strategy signals:
  1. TradeExecutionService receives the signal
  2. EntryManager calculates position sizing, SL, TP based on manual.yaml config
  3. Risk validation is performed
  4. Orders are executed through MT5Client with configured scaling

The only difference from automated trading: the signal source is "API request"
instead of "strategy evaluation". All other logic is identical.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_api_service, get_current_user
from app.api.service import APIService
from app.api.models.requests import TriggerEntrySignalRequest, TriggerExitSignalRequest

router = APIRouter()


@router.post("/entry")
async def trigger_entry_signal(
    request: TriggerEntrySignalRequest,
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Trigger a manual entry signal (BUY or SELL).

    Publishes EntrySignalEvent with strategy_name="manual" to the EventBus.
    The system then handles everything exactly as if a strategy generated the signal:
    - Position sizing based on risk config (from manual.yaml)
    - SL calculation (monetary, ATR-based, fixed, etc.)
    - TP calculation with scaling if configured
    - Risk validation (daily loss limits, max positions, etc.)
    - Order execution with configured scaling (multiple entries if configured)

    **Authentication**: Required (JWT Bearer token)

    **Request Body**:
    ```json
    {
      "symbol": "XAUUSD",
      "direction": "long"
    }
    ```

    **Response**:
    ```json
    {
      "status": "success",
      "message": "Manual entry signal triggered",
      "symbol": "XAUUSD",
      "direction": "long",
      "strategy": "manual",
      "triggered_by": "admin"
    }
    ```

    **Example**:
    ```bash
    curl -X POST http://localhost:8080/signals/entry \
      -H "Authorization: Bearer YOUR_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"symbol": "XAUUSD", "direction": "long"}'
    ```

    **Note**: The system uses the manual.yaml configuration for this symbol
    to determine position sizing, SL, TP, and scaling parameters.
    """
    # Validate direction
    if request.direction.lower() not in ["long", "short"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid direction: {request.direction}. Must be 'long' or 'short'"
        )

    # Trigger the entry signal via APIService
    api_service.trigger_entry_signal(
        symbol=request.symbol,
        direction=request.direction,
        entry_price=None  # Let the system get current market price
    )

    return {
        "status": "success",
        "message": "Manual entry signal triggered",
        "symbol": request.symbol.upper(),
        "direction": request.direction.lower(),
        "strategy": "manual",
        "triggered_by": user.get("sub", "unknown")
    }


@router.post("/exit")
async def trigger_exit_signal(
    request: TriggerExitSignalRequest,
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Trigger a manual exit signal.

    Publishes ExitSignalEvent with strategy_name="manual" to the EventBus.
    This closes positions using the standard exit logic.

    **Authentication**: Required (JWT Bearer token)

    **Request Body**:
    ```json
    {
      "symbol": "XAUUSD",
      "direction": "long",
      "reason": "manual"
    }
    ```

    **Response**:
    ```json
    {
      "status": "success",
      "message": "Manual exit signal triggered",
      "symbol": "XAUUSD",
      "direction": "long",
      "reason": "manual",
      "triggered_by": "admin"
    }
    ```

    **Example**:
    ```bash
    curl -X POST http://localhost:8080/signals/exit \
      -H "Authorization: Bearer YOUR_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"symbol": "XAUUSD", "direction": "long", "reason": "take_profit"}'
    ```
    """
    # Validate direction
    if request.direction.lower() not in ["long", "short"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid direction: {request.direction}. Must be 'long' or 'short'"
        )

    # Trigger the exit signal via APIService
    api_service.trigger_exit_signal(
        symbol=request.symbol,
        direction=request.direction,
        reason=request.reason
    )

    return {
        "status": "success",
        "message": "Manual exit signal triggered",
        "symbol": request.symbol.upper(),
        "direction": request.direction.lower(),
        "reason": request.reason,
        "triggered_by": user.get("sub", "unknown")
    }


@router.get("/")
async def list_orders(
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    List all pending orders.

    **Note**: In the current system, manual signals are executed immediately
    at market price. This endpoint is a placeholder for future functionality
    to list pending limit/stop orders.

    **Authentication**: Required (JWT Bearer token)

    **Response**:
    ```json
    {
      "status": "not_implemented",
      "message": "Order listing not yet implemented",
      "note": "Manual signals execute immediately at market"
    }
    ```
    """
    return {
        "status": "not_implemented",
        "message": "Order listing not yet implemented",
        "note": "Manual signals execute immediately at market"
    }


@router.delete("/{ticket}")
async def cancel_order(
    ticket: int,
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Cancel a pending order by ticket number.

    **Authentication**: Required (JWT Bearer token)

    **Response**:
    ```json
    {
      "status": "not_implemented",
      "message": "Order cancellation not yet implemented"
    }
    ```
    """
    return {
        "status": "not_implemented",
        "message": "Order cancellation not yet implemented",
        "ticket": ticket
    }
