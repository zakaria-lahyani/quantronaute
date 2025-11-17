"""
Account monitoring endpoints.

Provides API endpoints for monitoring account status and metrics.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_api_service, get_current_user
from app.api.service import APIService

router = APIRouter()


@router.get("/summary")
async def get_account_summary(
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get account summary including balance, equity, margin, and profit.

    **Authentication**: Required (JWT Bearer token)

    **Response**:
    ```json
    {
      "status": "not_implemented",
      "message": "Account monitoring not yet implemented",
      "note": "Will provide balance, equity, margin, profit, and position count"
    }
    ```

    **Future Implementation**:
    - Query MT5Client for account information
    - Return balance, equity, margin, profit
    - Cache for 5 seconds to reduce broker API load
    """
    return {
        "status": "not_implemented",
        "message": "Account monitoring not yet implemented",
        "note": "Will provide balance, equity, margin, profit, and position count"
    }


@router.get("/balance")
async def get_account_balance(
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get account balance.

    **Authentication**: Required (JWT Bearer token)

    **Response**:
    ```json
    {
      "status": "not_implemented",
      "message": "Account balance monitoring not yet implemented"
    }
    ```
    """
    return {
        "status": "not_implemented",
        "message": "Account balance monitoring not yet implemented"
    }


@router.get("/equity")
async def get_account_equity(
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get account equity.

    **Authentication**: Required (JWT Bearer token)

    **Response**:
    ```json
    {
      "status": "not_implemented",
      "message": "Account equity monitoring not yet implemented"
    }
    ```
    """
    return {
        "status": "not_implemented",
        "message": "Account equity monitoring not yet implemented"
    }


@router.get("/margin")
async def get_margin_info(
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get margin information.

    **Authentication**: Required (JWT Bearer token)

    **Response**:
    ```json
    {
      "status": "not_implemented",
      "message": "Margin monitoring not yet implemented"
    }
    ```
    """
    return {
        "status": "not_implemented",
        "message": "Margin monitoring not yet implemented"
    }
