"""
API command events.

This module defines events published by the API to request operations
from the trading system.

IMPORTANT: For manual trading (entry/exit signals), the API reuses
the existing EntrySignalEvent and ExitSignalEvent from strategy_events.py.
This ensures manual trades flow through the exact same pipeline as
automated trades, with identical risk management, sizing, and execution logic.
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


# NOTE: For manual entry/exit signals, the API directly publishes
# EntrySignalEvent and ExitSignalEvent from app.events.strategy_events
# instead of custom API command events. This ensures manual trades
# flow through the identical pipeline as automated strategy trades.
#
# Example:
#   event_bus.publish(EntrySignalEvent(
#       strategy_name="manual",
#       symbol="XAUUSD",
#       direction="long",
#       entry_price=2650.25
#   ))
#
# This signal is then handled by TradeExecutionService, which:
# - Uses EntryManager for position sizing and risk validation
# - Calculates SL/TP based on configuration
# - Applies position scaling if configured
# - Executes trades through MT5Client
#
# The only difference: strategy_name="manual" instead of "strategy_xyz"


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
