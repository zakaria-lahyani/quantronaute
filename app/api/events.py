"""
API command events.

This module defines events published by the API to request operations
from the trading system. These events follow the correlation ID pattern
for request-response tracking.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from app.events.base import Event


@dataclass(frozen=True, kw_only=True)
class APICommandEvent(Event):
    """
    Base class for API command events.

    All API commands include a correlation_id for matching with response events.
    """
    correlation_id: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())


@dataclass(frozen=True, kw_only=True)
class ClosePositionCommandEvent(APICommandEvent):
    """
    Command to close a position.

    Attributes:
        correlation_id: Unique ID to match with response
        position_id: Position ticket to close
        volume: Optional partial close volume
        reason: Reason for closing
    """
    position_id: int
    volume: Optional[float] = None
    reason: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class ModifyPositionCommandEvent(APICommandEvent):
    """
    Command to modify position SL/TP.

    Attributes:
        correlation_id: Unique ID to match with response
        position_id: Position ticket to modify
        stop_loss: New stop loss price
        take_profit: New take profit price
    """
    position_id: int
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass(frozen=True, kw_only=True)
class PlaceOrderCommandEvent(APICommandEvent):
    """
    Command to place a new order.

    Attributes:
        correlation_id: Unique ID to match with response
        symbol: Trading symbol
        direction: Trade direction
        volume: Position size
        entry_price: Entry price
        stop_loss: Stop loss price
        take_profit: Take profit price
        strategy_name: Strategy name for tracking
    """
    symbol: str
    direction: str
    volume: float
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    strategy_name: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class QueryIndicatorsCommandEvent(APICommandEvent):
    """
    Command to query current indicator values.

    Attributes:
        correlation_id: Unique ID to match with response
        symbol: Trading symbol to query
        timeframe: Timeframe to query
    """
    symbol: str
    timeframe: str


@dataclass(frozen=True, kw_only=True)
class QueryStrategyConditionsCommandEvent(APICommandEvent):
    """
    Command to query strategy condition evaluation (NEW feature).

    Attributes:
        correlation_id: Unique ID to match with response
        symbol: Trading symbol to evaluate
        strategy_name: Strategy to evaluate
    """
    symbol: str
    strategy_name: Optional[str] = None


# TODO: Add more command events for other API operations
