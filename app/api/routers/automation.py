"""
Automation control endpoints.

Provides API endpoints for enabling/disabling automated trading.
This replaces the file-based toggle system with a proper REST API.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_api_service, get_current_user
from app.api.service import APIService

router = APIRouter()


@router.post("/enable")
async def enable_automation(
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Enable automated trading.

    Publishes AutomationEnabledEvent to activate automated strategies.
    Manual trading via API will continue to work.

    **Authentication**: Required (JWT Bearer token)

    **Response**:
    ```json
    {
      "status": "success",
      "message": "Automated trading enabled",
      "enabled_by": "admin"
    }
    ```

    **Example**:
    ```bash
    curl -X POST http://localhost:8080/automation/enable \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    api_service.enable_automation()

    return {
        "status": "success",
        "message": "Automated trading enabled",
        "enabled_by": user.get("sub", "unknown")
    }


@router.post("/disable")
async def disable_automation(
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Disable automated trading.

    Publishes AutomationDisabledEvent to deactivate automated strategies.
    Manual trading via API will continue to work.

    **Authentication**: Required (JWT Bearer token)

    **Response**:
    ```json
    {
      "status": "success",
      "message": "Automated trading disabled",
      "disabled_by": "admin"
    }
    ```

    **Example**:
    ```bash
    curl -X POST http://localhost:8080/automation/disable \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    api_service.disable_automation()

    return {
        "status": "success",
        "message": "Automated trading disabled",
        "disabled_by": user.get("sub", "unknown")
    }


@router.get("/status")
async def get_automation_status(
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get current automation status.

    Queries the automation controller for the current state.

    **Authentication**: Required (JWT Bearer token)

    **Response**:
    ```json
    {
      "status": "queried",
      "message": "Automation status query published",
      "note": "Check AutomationStatusEvent on EventBus for actual status"
    }
    ```

    **Note**: This endpoint publishes a query event. The actual status
    will be published as an AutomationStatusEvent on the EventBus.
    For synchronous status, use `/system/status` endpoint.

    **Example**:
    ```bash
    curl http://localhost:8080/automation/status \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    api_service.query_automation_status()

    return {
        "status": "queried",
        "message": "Automation status query published",
        "note": "Check AutomationStatusEvent on EventBus for actual status"
    }
