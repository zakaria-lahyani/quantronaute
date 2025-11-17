"""
Automation control endpoints.

Provides API endpoints for enabling/disabling automated trading.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def get_automation_status():
    """Get current automation status."""
    # TODO: Implement in Task 3.0
    return {"status": "not_implemented"}


@router.post("/enable")
async def enable_automation():
    """Enable automated trading."""
    # TODO: Implement in Task 3.0
    return {"status": "not_implemented"}


@router.post("/disable")
async def disable_automation():
    """Disable automated trading."""
    # TODO: Implement in Task 3.0
    return {"status": "not_implemented"}
