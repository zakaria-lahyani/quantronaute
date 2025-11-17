"""
Strategy monitoring endpoints.

Provides API endpoints for real-time strategy condition evaluation.
This is a NEW feature that shows why strategies triggered or didn't trigger.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/conditions")
async def get_strategy_conditions():
    """Get real-time evaluation of strategy conditions."""
    # TODO: Implement in Task 7.0
    return {"status": "not_implemented"}


@router.get("/conditions/{symbol}")
async def get_symbol_strategy_conditions(symbol: str):
    """Get strategy condition evaluation for a specific symbol."""
    # TODO: Implement in Task 7.0
    return {"status": "not_implemented"}
