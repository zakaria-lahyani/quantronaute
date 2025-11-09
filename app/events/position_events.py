"""
Position Monitoring Events.

Events published by the Position Monitor Service for tracking and managing
open positions, including multi-target take profit execution.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class PositionOpenedEvent:
    """
    Event published when a new position is opened.

    This event is triggered when pending orders are filled and become positions.
    """

    symbol: str
    ticket: int
    order_type: str  # 'BUY' or 'SELL'
    volume: float
    open_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    magic: int
    group_id: Optional[str]  # Group ID for scaled entries
    open_time: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TPLevelHitEvent:
    """
    Event published when price reaches a take profit level.

    This triggers partial position closure at the specified TP level.
    """

    symbol: str
    ticket: int
    tp_level: float
    current_price: float
    percent_to_close: float  # Percentage of position to close (0-100)
    move_stop: bool  # Whether to move stop loss after this TP
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PositionPartiallyClosedEvent:
    """
    Event published when a portion of a position is closed.

    This happens when multi-target TP levels are hit.
    """

    symbol: str
    original_ticket: int
    closed_volume: float
    remaining_volume: float
    close_price: float
    profit: float
    tp_level: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PositionFullyClosedEvent:
    """
    Event published when a position is completely closed.
    """

    symbol: str
    ticket: int
    close_price: float
    profit: float
    close_reason: str  # 'tp', 'sl', 'manual', 'be_moved'
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class StopLossMovedEvent:
    """
    Event published when stop loss is moved (e.g., to breakeven after TP1).
    """

    symbol: str
    ticket: int
    old_stop_loss: Optional[float]
    new_stop_loss: float
    reason: str  # 'tp_hit', 'trailing', 'manual'
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
