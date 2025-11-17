"""
Order management endpoints.

Provides API endpoints for placing and managing orders.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/")
async def place_order():
    """Place a new order."""
    # TODO: Implement in Task 5.0
    return {"status": "not_implemented"}


@router.delete("/{order_id}")
async def cancel_order(order_id: int):
    """Cancel a pending order."""
    # TODO: Implement in Task 5.0
    return {"status": "not_implemented"}
