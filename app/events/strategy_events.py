"""
Strategy-related events.

These events are published by StrategyEvaluationService when strategies
are evaluated and signals are generated.
"""

from dataclasses import dataclass
from typing import Optional, Any

from app.events.base import Event


@dataclass(frozen=True)
class EntrySignalEvent(Event):
    """
    Published when a strategy generates an entry signal.

    This event triggers trade execution with risk management.

    Attributes:
        strategy_name: Name of the strategy that generated the signal
        symbol: Trading symbol
        direction: Trade direction ("long" or "short")
        entry_price: Current market price (for logging/reference)
    """
    strategy_name: str
    symbol: str
    direction: str
    entry_price: Optional[float] = None

    def is_long(self) -> bool:
        """Check if this is a long entry signal."""
        return self.direction.lower() == "long"

    def is_short(self) -> bool:
        """Check if this is a short entry signal."""
        return self.direction.lower() == "short"


@dataclass(frozen=True)
class ExitSignalEvent(Event):
    """
    Published when a strategy generates an exit signal.

    This event triggers position closure.

    Attributes:
        strategy_name: Name of the strategy that generated the signal
        symbol: Trading symbol
        direction: Trade direction to exit ("long" or "short")
        reason: Reason for exit (e.g., "stop_loss", "take_profit", "signal")
    """
    strategy_name: str
    symbol: str
    direction: str
    reason: str = "signal"


@dataclass(frozen=True)
class StrategyActivatedEvent(Event):
    """
    Published when a strategy becomes active.

    Strategies can be activated/deactivated based on schedule or conditions.

    Attributes:
        strategy_name: Name of the strategy
        symbol: Trading symbol
    """
    strategy_name: str
    symbol: str


@dataclass(frozen=True)
class StrategyDeactivatedEvent(Event):
    """
    Published when a strategy becomes inactive.

    Attributes:
        strategy_name: Name of the strategy
        symbol: Trading symbol
        reason: Reason for deactivation (e.g., "schedule", "condition")
    """
    strategy_name: str
    symbol: str
    reason: str


@dataclass(frozen=True)
class TradesReadyEvent(Event):
    """
    Published when trade decisions are ready for execution.

    This event carries the complete Trades object with all entry/exit decisions
    ready to be executed by TradeExecutionService.

    Attributes:
        symbol: Trading symbol
        trades: Trades object with entries and exits
        num_entries: Number of entry decisions
        num_exits: Number of exit decisions
    """
    symbol: str
    trades: Any  # Trades type from app.strategy_builder.data.dtos
    num_entries: int
    num_exits: int


@dataclass(frozen=True)
class StrategyEvaluationErrorEvent(Event):
    """
    Published when strategy evaluation fails.

    Attributes:
        strategy_name: Name of the strategy
        symbol: Trading symbol
        error: Error message
        exception: Optional exception object
    """
    strategy_name: str
    symbol: str
    error: str
    exception: Optional[Exception] = None
