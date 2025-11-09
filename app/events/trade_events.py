"""
Trade execution events.

These events are published by TradeExecutionService when trades are executed,
positions are closed, or risk limits are breached.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from app.events.base import Event


@dataclass(frozen=True)
class OrderPlacedEvent(Event):
    """
    Published when an order is successfully placed.

    Attributes:
        order_id: Broker-assigned order ID
        symbol: Trading symbol
        direction: Trade direction ("long" or "short")
        volume: Position size in lots
        entry_price: Order entry price
        stop_loss: Stop loss price
        take_profit: Take profit price (or list for multi-target)
        strategy_name: Name of the strategy
        magic_number: Magic number for tracking
    """
    order_id: int
    symbol: str
    direction: str
    volume: float
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    strategy_name: Optional[str] = None
    magic_number: Optional[int] = None


@dataclass(frozen=True)
class OrderRejectedEvent(Event):
    """
    Published when an order is rejected.

    Attributes:
        symbol: Trading symbol
        direction: Trade direction
        reason: Reason for rejection
        strategy_name: Name of the strategy
        error_code: Optional broker error code
    """
    symbol: str
    direction: str
    reason: str
    strategy_name: Optional[str] = None
    error_code: Optional[int] = None


@dataclass(frozen=True)
class PositionClosedEvent(Event):
    """
    Published when a position is closed.

    Attributes:
        position_id: Position ticket number
        symbol: Trading symbol
        direction: Trade direction
        volume: Position size that was closed
        profit: Profit/loss from the position
        close_price: Price at which position was closed
        strategy_name: Name of the strategy
        reason: Reason for closing (e.g., "exit_signal", "stop_loss", "take_profit")
    """
    position_id: int
    symbol: str
    direction: str
    volume: float
    profit: float
    close_price: float
    strategy_name: Optional[str] = None
    reason: str = "exit_signal"


@dataclass(frozen=True)
class RiskLimitBreachedEvent(Event):
    """
    Published when a risk limit is breached.

    This event indicates that trading should be stopped or restricted.

    Attributes:
        limit_type: Type of limit breached (e.g., "daily_loss", "max_positions")
        current_value: Current value that breached the limit
        limit_value: The limit threshold
        symbol: Optional trading symbol
    """
    limit_type: str
    current_value: float
    limit_value: float
    symbol: Optional[str] = None


@dataclass(frozen=True)
class TradingAuthorizedEvent(Event):
    """
    Published when trading is authorized.

    This indicates all checks passed and trading can proceed.

    Attributes:
        symbol: Trading symbol
        reason: Reason for authorization
    """
    symbol: str
    reason: str = "all_checks_passed"


@dataclass(frozen=True)
class TradingBlockedEvent(Event):
    """
    Published when trading is blocked.

    This indicates trading should not proceed due to restrictions or risk limits.

    Attributes:
        symbol: Trading symbol
        reasons: List of reasons for blocking
    """
    symbol: str
    reasons: List[str]


@dataclass(frozen=True)
class TradesExecutedEvent(Event):
    """
    Published when trades are successfully executed.

    This event contains metadata about executed trades including TP targets
    for position monitoring.

    Attributes:
        symbol: Trading symbol
        direction: Trade direction ("long" or "short")
        total_volume: Total volume executed
        order_count: Number of orders executed
        strategy_name: Name of the strategy
        metadata: Additional metadata including:
            - tp_targets: List of TP levels for position monitoring
            - tickets: List of order tickets
            - group_id: Group ID for scaled entries
    """
    symbol: str
    direction: str
    total_volume: float
    order_count: int
    strategy_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
