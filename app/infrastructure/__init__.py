"""
Infrastructure layer for the trading system.

This package contains core infrastructure components:
- EventBus: Event publishing and subscription
- TradingOrchestrator: Service lifecycle management
- Configuration: System configuration and loading
"""

from app.infrastructure.event_bus import EventBus
from app.infrastructure.orchestrator import TradingOrchestrator, OrchestratorStatus
from app.infrastructure.config import (
    SystemConfig,
    ConfigLoader,
    ServicesConfig,
    EventBusConfig,
    OrchestratorConfig,
    LoggingConfig,
    TradingConfig,
    RiskConfig,
)
from app.infrastructure.logging import (
    LoggingManager,
    CorrelationContext,
    get_logger,
    JsonFormatter,
    TextFormatter,
)

__all__ = [
    "EventBus",
    "TradingOrchestrator",
    "OrchestratorStatus",
    "SystemConfig",
    "ConfigLoader",
    "ServicesConfig",
    "EventBusConfig",
    "OrchestratorConfig",
    "LoggingConfig",
    "TradingConfig",
    "RiskConfig",
    "LoggingManager",
    "CorrelationContext",
    "get_logger",
    "JsonFormatter",
    "TextFormatter",
]
