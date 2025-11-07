"""
Service layer for the trading system.

This package contains event-driven services that wrap existing packages
and communicate through the EventBus.
"""

from app.services.base import EventDrivenService, HealthStatus
from app.services.data_fetching import DataFetchingService
from app.services.indicator_calculation import IndicatorCalculationService
from app.services.strategy_evaluation import StrategyEvaluationService
from app.services.trade_execution import TradeExecutionService

__all__ = [
    "EventDrivenService",
    "HealthStatus",
    "DataFetchingService",
    "IndicatorCalculationService",
    "StrategyEvaluationService",
    "TradeExecutionService",
]
