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
      "balance": 10000.50,
      "equity": 10250.75,
      "margin": 500.00,
      "margin_free": 9750.75,
      "margin_level": 2050.15,
      "profit": 250.25,
      "currency": "USD",
      "leverage": 100
    }
    ```

    If MT5Client not available:
    ```json
    {
      "error": "Account data not available",
      "reason": "MT5Client not connected to API service"
    }
    ```
    """
    summary = api_service.get_account_summary()

    if summary is None:
        return {
            "error": "Account data not available",
            "reason": "MT5Client not connected to API service"
        }

    return summary


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
      "balance": 10000.50
    }
    ```
    """
    balance = api_service.get_account_balance()

    if balance is None:
        return {
            "error": "Balance data not available",
            "reason": "MT5Client not connected to API service"
        }

    return {"balance": balance}


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
      "equity": 10250.75
    }
    ```
    """
    equity_data = api_service.get_account_equity()

    if equity_data is None:
        return {
            "error": "Equity data not available",
            "reason": "MT5Client not connected to API service"
        }

    return equity_data


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
      "margin": 500.00,
      "margin_free": 9750.75,
      "margin_level": 2050.15
    }
    ```
    """
    margin_data = api_service.get_margin_info()

    if margin_data is None:
        return {
            "error": "Margin data not available",
            "reason": "MT5Client not connected to API service"
        }

    return margin_data
