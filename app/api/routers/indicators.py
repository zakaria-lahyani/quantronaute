"""
Indicator monitoring endpoints.

Provides API endpoints for accessing current indicator values.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_api_service, get_current_user
from app.api.service import APIService

router = APIRouter()


@router.get("/{symbol}")
async def get_symbol_indicators(
    symbol: str,
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get all indicator values for a specific symbol across all timeframes.

    **Authentication**: Required (JWT Bearer token)

    **Path Parameters**:
    - `symbol`: Trading symbol (e.g., XAUUSD, EURUSD)

    **Response**:
    ```json
    {
      "symbol": "XAUUSD",
      "timestamp": "2025-11-17T10:30:00Z",
      "timeframes": {
        "M1": {
          "close": 2650.25,
          "sma_50": 2648.10,
          "ema_21": 2649.50,
          "rsi_14": 58.3,
          "atr_14": 1.25
        },
        "H1": {
          "close": 2650.25,
          "sma_50": 2645.00,
          "ema_21": 2647.80,
          "rsi_14": 62.1,
          "atr_14": 3.50
        }
      }
    }
    ```

    If indicator service not available:
    ```json
    {
      "error": "Indicator data not available",
      "reason": "Orchestrator not connected or symbol not configured",
      "symbol": "XAUUSD"
    }
    ```
    """
    from datetime import datetime, timezone

    indicators = api_service.get_all_indicators_for_symbol(symbol.upper())

    if indicators is None:
        return {
            "error": "Indicator data not available",
            "reason": "Orchestrator not connected or symbol not configured",
            "symbol": symbol.upper()
        }

    return {
        "symbol": symbol.upper(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "timeframes": indicators
    }


@router.get("/{symbol}/{timeframe}")
async def get_symbol_timeframe_indicators(
    symbol: str,
    timeframe: str,
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get indicator values for a specific symbol and timeframe.

    **Authentication**: Required (JWT Bearer token)

    **Path Parameters**:
    - `symbol`: Trading symbol (e.g., XAUUSD, EURUSD)
    - `timeframe`: Timeframe (e.g., M1, M5, M15, H1, H4, D1)

    **Response**:
    ```json
    {
      "symbol": "XAUUSD",
      "timeframe": "H1",
      "timestamp": "2025-11-17T10:30:00Z",
      "indicators": {
        "close": 2650.25,
        "sma_50": 2645.00,
        "ema_21": 2647.80,
        "rsi_14": 62.1,
        "atr_14": 3.50
      }
    }
    ```
    """
    from datetime import datetime, timezone

    indicators = api_service.get_latest_indicators(symbol.upper(), timeframe.upper())

    if indicators is None:
        return {
            "error": "Indicator data not available",
            "reason": "Orchestrator not connected or symbol/timeframe not configured",
            "symbol": symbol.upper(),
            "timeframe": timeframe.upper()
        }

    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe.upper(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "indicators": indicators
    }


@router.get("/{symbol}/{timeframe}/{indicator}")
async def get_specific_indicator(
    symbol: str,
    timeframe: str,
    indicator: str,
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get a specific indicator value.

    **Authentication**: Required (JWT Bearer token)

    **Path Parameters**:
    - `symbol`: Trading symbol (e.g., XAUUSD, EURUSD)
    - `timeframe`: Timeframe (e.g., M1, M5, M15, H1, H4, D1)
    - `indicator`: Indicator name (e.g., sma_50, ema_21, rsi_14, atr_14)

    **Response**:
    ```json
    {
      "symbol": "XAUUSD",
      "timeframe": "H1",
      "indicator": "rsi_14",
      "value": 62.1,
      "timestamp": "2025-11-17T10:30:00Z"
    }
    ```
    """
    from datetime import datetime, timezone

    indicators = api_service.get_latest_indicators(symbol.upper(), timeframe.upper())

    if indicators is None:
        return {
            "error": "Indicator data not available",
            "reason": "Orchestrator not connected or symbol/timeframe not configured",
            "symbol": symbol.upper(),
            "timeframe": timeframe.upper(),
            "indicator": indicator.lower()
        }

    # Try to find the indicator (case-insensitive)
    indicator_lower = indicator.lower()
    indicator_value = None

    for key, value in indicators.items():
        if key.lower() == indicator_lower:
            indicator_value = value
            break

    if indicator_value is None:
        return {
            "error": "Indicator not found",
            "reason": f"Indicator '{indicator}' not available in calculated indicators",
            "symbol": symbol.upper(),
            "timeframe": timeframe.upper(),
            "indicator": indicator.lower(),
            "available_indicators": list(indicators.keys())
        }

    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe.upper(),
        "indicator": indicator.lower(),
        "value": indicator_value,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/config/{symbol}")
async def get_indicator_config(
    symbol: str,
    api_service: APIService = Depends(get_api_service),
    user: dict = Depends(get_current_user)
):
    """
    Get indicator configuration for a symbol.

    **Authentication**: Required (JWT Bearer token)

    **Path Parameters**:
    - `symbol`: Trading symbol (e.g., XAUUSD, EURUSD)

    **Response**:
    ```json
    {
      "status": "not_implemented",
      "message": "Indicator configuration retrieval not yet implemented",
      "symbol": "XAUUSD"
    }
    ```

    **Future Implementation**:
    - Return configured indicators from strategy YAML
    - Include indicator parameters (periods, etc.)
    - Show which timeframes are monitored
    """
    return {
        "status": "not_implemented",
        "message": "Indicator configuration retrieval not yet implemented",
        "symbol": symbol.upper()
    }
