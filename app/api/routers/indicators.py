"""
Indicator monitoring endpoints.

Provides API endpoints for accessing current indicator values.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_indicators():
    """Get current indicator values for all symbols."""
    # TODO: Implement in Task 6.0
    return {"status": "not_implemented"}


@router.get("/{symbol}")
async def get_symbol_indicators(symbol: str):
    """Get indicator values for a specific symbol."""
    # TODO: Implement in Task 6.0
    return {"status": "not_implemented"}
