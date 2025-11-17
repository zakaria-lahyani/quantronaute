"""
Position management endpoints.

Provides API endpoints for monitoring and managing open positions.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_api_service, get_current_user
from app.api.service import APIService

router = APIRouter()


# ========================================================================
# POSITION HISTORY ENDPOINTS (must come before /{symbol} route)
# ========================================================================

@router.get("/history")
async def get_closed_positions(
    start: Optional[str] = Query(None, description="Start datetime (ISO format, e.g., 2025-01-01T00:00:00)"),
    end: Optional[str] = Query(None, description="End datetime (ISO format, e.g., 2025-01-31T23:59:59)"),
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get all closed positions from history.

    **Authentication**: Required (JWT Bearer token)

    **Query Parameters**:
    - `start`: Optional start datetime in ISO format (e.g., 2025-01-01T00:00:00)
    - `end`: Optional end datetime in ISO format (e.g., 2025-01-31T23:59:59)

    **Response**:
    ```json
    {
      "positions": [
        {
          "ticket": 123456,
          "symbol": "XAUUSD",
          "type": 0,
          "volume": 0.1,
          "price_open": 2650.25,
          "price_close": 2655.80,
          "profit": 55.50,
          "swap": -2.50,
          "commission": -5.00,
          "time_open": "2025-11-17T08:30:00Z",
          "time_close": "2025-11-17T10:15:00Z",
          "magic": 12345,
          "comment": "manual"
        }
      ],
      "total_positions": 1,
      "total_profit": 48.00,
      "date_range": {
        "start": "2025-01-01T00:00:00",
        "end": "2025-01-31T23:59:59"
      }
    }
    ```

    If MT5Client not available:
    ```json
    {
      "error": "History data not available",
      "reason": "MT5Client not connected to API service"
    }
    ```
    """
    positions = api_service.get_closed_positions(start=start, end=end)

    if positions is None:
        return {
            "error": "History data not available",
            "reason": "MT5Client not connected to API service"
        }

    # Calculate summary metrics
    total_profit = sum(pos.get("profit", 0) for pos in positions)

    response = {
        "positions": positions,
        "total_positions": len(positions),
        "total_profit": total_profit
    }

    if start or end:
        response["date_range"] = {"start": start, "end": end}

    return response


@router.get("/statistics")
async def get_trading_statistics(
    start: Optional[str] = Query(None, description="Start datetime (ISO format)"),
    end: Optional[str] = Query(None, description="End datetime (ISO format)"),
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get trading statistics from closed positions.

    **Authentication**: Required (JWT Bearer token)

    **Query Parameters**:
    - `start`: Optional start datetime in ISO format
    - `end`: Optional end datetime in ISO format

    **Response**:
    ```json
    {
      "total_trades": 50,
      "profitable_trades": 32,
      "losing_trades": 18,
      "win_rate": 64.0,
      "total_profit": 5250.50,
      "total_loss": 2100.25,
      "net_profit": 3150.25,
      "average_profit": 164.08,
      "average_loss": 116.68,
      "profit_factor": 2.50,
      "date_range": {
        "start": "2025-01-01T00:00:00",
        "end": "2025-01-31T23:59:59"
      }
    }
    ```

    If MT5Client not available:
    ```json
    {
      "error": "Trading statistics not available",
      "reason": "MT5Client not connected to API service"
    }
    ```
    """
    statistics = api_service.get_trading_statistics(start=start, end=end)

    if statistics is None:
        return {
            "error": "Trading statistics not available",
            "reason": "MT5Client not connected to API service"
        }

    if start or end:
        statistics["date_range"] = {"start": start, "end": end}

    return statistics


# ========================================================================
# OPEN POSITIONS ENDPOINTS
# ========================================================================

@router.get("/")
async def get_positions(
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get all open positions.

    **Authentication**: Required (JWT Bearer token)

    **Response**:
    ```json
    {
      "positions": [
        {
          "ticket": 123456,
          "symbol": "XAUUSD",
          "type": 0,
          "volume": 0.1,
          "price_open": 2650.25,
          "price_current": 2655.80,
          "profit": 55.50,
          "swap": -2.50,
          "commission": -5.00,
          "sl": 2640.00,
          "tp": 2670.00,
          "time": "2025-11-17T08:30:00Z",
          "magic": 12345,
          "comment": "manual"
        }
      ],
      "total_positions": 1,
      "total_profit": 48.00
    }
    ```

    If MT5Client not available:
    ```json
    {
      "error": "Position data not available",
      "reason": "MT5Client not connected to API service"
    }
    ```
    """
    positions = api_service.get_open_positions()

    if positions is None:
        return {
            "error": "Position data not available",
            "reason": "MT5Client not connected to API service"
        }

    # Calculate summary metrics
    total_profit = sum(pos.get("profit", 0) for pos in positions)

    return {
        "positions": positions,
        "total_positions": len(positions),
        "total_profit": total_profit
    }


@router.get("/{symbol}")
async def get_positions_by_symbol(
    symbol: str,
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get all open positions for a specific symbol.

    **Authentication**: Required (JWT Bearer token)

    **Path Parameters**:
    - `symbol`: Trading symbol (e.g., XAUUSD, EURUSD)

    **Response**:
    ```json
    {
      "symbol": "XAUUSD",
      "positions": [...],
      "total_positions": 2,
      "total_profit": 150.25
    }
    ```

    If MT5Client not available:
    ```json
    {
      "error": "Position data not available",
      "reason": "MT5Client not connected to API service",
      "symbol": "XAUUSD"
    }
    ```
    """
    positions = api_service.get_positions_by_symbol(symbol)

    if positions is None:
        return {
            "error": "Position data not available",
            "reason": "MT5Client not connected to API service",
            "symbol": symbol.upper()
        }

    # Calculate summary metrics
    total_profit = sum(pos.get("profit", 0) for pos in positions)

    return {
        "symbol": symbol.upper(),
        "positions": positions,
        "total_positions": len(positions),
        "total_profit": total_profit
    }


@router.get("/ticket/{ticket}")
async def get_position(
    ticket: int,
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get specific position details by ticket number.

    **Authentication**: Required (JWT Bearer token)

    **Path Parameters**:
    - `ticket`: Position ticket number

    **Response**:
    ```json
    {
      "ticket": 123456,
      "symbol": "XAUUSD",
      "type": 0,
      "volume": 0.1,
      "price_open": 2650.25,
      "price_current": 2655.80,
      "profit": 55.50,
      "swap": -2.50,
      "commission": -5.00,
      "sl": 2640.00,
      "tp": 2670.00,
      "time": "2025-11-17T08:30:00Z",
      "magic": 12345,
      "comment": "manual"
    }
    ```

    If position not found:
    ```json
    {
      "error": "Position not found",
      "ticket": 12345
    }
    ```
    """
    position = api_service.get_position_by_ticket(ticket)

    if position is None:
        return {
            "error": "Position not found",
            "ticket": ticket
        }

    return position


@router.post("/{ticket}/close")
async def close_position(
    ticket: int,
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Close a specific position.

    **Authentication**: Required (JWT Bearer token)

    **Path Parameters**:
    - `ticket`: Position ticket number to close

    **Response**:
    ```json
    {
      "status": "not_implemented",
      "message": "Position closing not yet implemented",
      "ticket": 12345
    }
    ```

    **Future Implementation**:
    - Publish ClosePositionCommandEvent
    - Wait for OrderClosedEvent response
    - Return success/failure with details
    """
    return {
        "status": "not_implemented",
        "message": "Position closing not yet implemented",
        "ticket": ticket
    }


@router.post("/{ticket}/modify")
async def modify_position(
    ticket: int,
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Modify position SL/TP.

    **Authentication**: Required (JWT Bearer token)

    **Path Parameters**:
    - `ticket`: Position ticket number to modify

    **Request Body** (future):
    ```json
    {
      "stop_loss": 2640.0,
      "take_profit": 2670.0
    }
    ```

    **Response**:
    ```json
    {
      "status": "not_implemented",
      "message": "Position modification not yet implemented",
      "ticket": 12345
    }
    ```

    **Future Implementation**:
    - Publish ModifyPositionCommandEvent
    - Wait for PositionModifiedEvent response
    - Return success/failure with new SL/TP values
    """
    return {
        "status": "not_implemented",
        "message": "Position modification not yet implemented",
        "ticket": ticket
    }


@router.post("/close-all")
async def close_all_positions(
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Close all open positions (optionally filtered by symbol).

    **Authentication**: Required (JWT Bearer token)

    **Request Body** (future, optional):
    ```json
    {
      "symbol": "XAUUSD"
    }
    ```

    **Response**:
    ```json
    {
      "status": "not_implemented",
      "message": "Mass position closing not yet implemented"
    }
    ```

    **Future Implementation**:
    - Query all open positions
    - Publish ClosePositionCommandEvent for each
    - Return summary of closed positions
    """
    return {
        "status": "not_implemented",
        "message": "Mass position closing not yet implemented"
    }


@router.get("/history/{symbol}")
async def get_closed_positions_by_symbol(
    symbol: str,
    start: Optional[str] = Query(None, description="Start datetime (ISO format)"),
    end: Optional[str] = Query(None, description="End datetime (ISO format)"),
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get closed positions filtered by symbol.

    **Authentication**: Required (JWT Bearer token)

    **Path Parameters**:
    - `symbol`: Trading symbol (e.g., XAUUSD, EURUSD)

    **Query Parameters**:
    - `start`: Optional start datetime in ISO format
    - `end`: Optional end datetime in ISO format

    **Response**:
    ```json
    {
      "symbol": "XAUUSD",
      "positions": [...],
      "total_positions": 5,
      "total_profit": 250.75,
      "date_range": {
        "start": "2025-01-01T00:00:00",
        "end": "2025-01-31T23:59:59"
      }
    }
    ```

    If MT5Client not available:
    ```json
    {
      "error": "History data not available",
      "reason": "MT5Client not connected to API service",
      "symbol": "XAUUSD"
    }
    ```
    """
    positions = api_service.get_closed_positions_by_symbol(symbol, start=start, end=end)

    if positions is None:
        return {
            "error": "History data not available",
            "reason": "MT5Client not connected to API service",
            "symbol": symbol.upper()
        }

    # Calculate summary metrics
    total_profit = sum(pos.get("profit", 0) for pos in positions)

    response = {
        "symbol": symbol.upper(),
        "positions": positions,
        "total_positions": len(positions),
        "total_profit": total_profit
    }

    if start or end:
        response["date_range"] = {"start": start, "end": end}

    return response


@router.get("/history/ticket/{ticket}")
async def get_closed_position_by_ticket(
    ticket: int,
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get a specific closed position by ticket number.

    **Authentication**: Required (JWT Bearer token)

    **Path Parameters**:
    - `ticket`: Position ticket number

    **Response**:
    ```json
    {
      "ticket": 123456,
      "symbol": "XAUUSD",
      "type": 0,
      "volume": 0.1,
      "price_open": 2650.25,
      "price_close": 2655.80,
      "profit": 55.50,
      "swap": -2.50,
      "commission": -5.00,
      "time_open": "2025-11-17T08:30:00Z",
      "time_close": "2025-11-17T10:15:00Z",
      "magic": 12345,
      "comment": "manual"
    }
    ```

    If position not found:
    ```json
    {
      "error": "Closed position not found",
      "ticket": 12345
    }
    ```
    """
    position = api_service.get_closed_position_by_ticket(ticket)

    if position is None:
        return {
            "error": "Closed position not found",
            "ticket": ticket
        }

    return position
