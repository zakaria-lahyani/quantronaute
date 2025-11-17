"""
Order management endpoints.

Provides API endpoints for smart order placement (one-click trading).
All orders use the trading system's logic for sizing, SL/TP calculation, and risk validation.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/")
async def place_smart_order():
    """
    Place a smart order (one-click trading).

    Specify only symbol and direction - the system handles everything else:
    - Calculates position size based on risk config
    - Determines SL based on ATR or configured method
    - Calculates TP targets (with scaling if configured)
    - Validates against risk limits
    - Executes with proper order scaling
    """
    # TODO: Implement in Task 5.0
    return {"status": "not_implemented"}


@router.delete("/{order_id}")
async def cancel_order(order_id: int):
    """Cancel a pending order."""
    # TODO: Implement in Task 5.0
    return {"status": "not_implemented"}
