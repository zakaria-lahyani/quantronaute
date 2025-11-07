"""
Event system for the trading application.

This package provides event-driven communication between services.
All events inherit from the base Event class and are immutable.
"""

from app.events.base import Event, EventHandler
from app.events.data_events import (
    DataFetchedEvent,
    NewCandleEvent,
    DataFetchErrorEvent,
)
from app.events.indicator_events import (
    IndicatorsCalculatedEvent,
    RegimeChangedEvent,
    IndicatorCalculationErrorEvent,
)
from app.events.strategy_events import (
    EntrySignalEvent,
    ExitSignalEvent,
    TradesReadyEvent,
    StrategyActivatedEvent,
    StrategyDeactivatedEvent,
    StrategyEvaluationErrorEvent,
)
from app.events.trade_events import (
    OrderPlacedEvent,
    OrderRejectedEvent,
    PositionClosedEvent,
    RiskLimitBreachedEvent,
    TradingAuthorizedEvent,
    TradingBlockedEvent,
)

__all__ = [
    # Base
    "Event",
    "EventHandler",
    # Data events
    "DataFetchedEvent",
    "NewCandleEvent",
    "DataFetchErrorEvent",
    # Indicator events
    "IndicatorsCalculatedEvent",
    "RegimeChangedEvent",
    "IndicatorCalculationErrorEvent",
    # Strategy events
    "EntrySignalEvent",
    "ExitSignalEvent",
    "TradesReadyEvent",
    "StrategyActivatedEvent",
    "StrategyDeactivatedEvent",
    "StrategyEvaluationErrorEvent",
    # Trade events
    "OrderPlacedEvent",
    "OrderRejectedEvent",
    "PositionClosedEvent",
    "RiskLimitBreachedEvent",
    "TradingAuthorizedEvent",
    "TradingBlockedEvent",
]
