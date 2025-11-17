"""
Account monitoring endpoints.

Provides API endpoints for monitoring account status and metrics.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_account_info():
    """Get current account information."""
    # TODO: Implement in Task 9.0
    return {"status": "not_implemented"}


@router.get("/balance")
async def get_account_balance():
    """Get account balance details."""
    # TODO: Implement in Task 9.0
    return {"status": "not_implemented"}


@router.get("/equity")
async def get_account_equity():
    """Get account equity details."""
    # TODO: Implement in Task 9.0
    return {"status": "not_implemented"}
