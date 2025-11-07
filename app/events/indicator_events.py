"""
Indicator-related events.

These events are published by IndicatorCalculationService when indicators
and regime data are calculated.
"""

from collections import deque
from dataclasses import dataclass
from typing import Optional, Dict, Any

import pandas as pd

from app.events.base import Event


@dataclass(frozen=True)
class IndicatorsCalculatedEvent(Event):
    """
    Published when indicators and regime are calculated for a new candle.

    This event contains enriched data with all indicator values and regime information.

    Attributes:
        symbol: Trading symbol
        timeframe: Timeframe
        enriched_data: Dictionary containing the enriched bar data with indicators
        recent_rows: Dictionary of recent rows for all timeframes (for strategy evaluation)
    """
    symbol: str
    timeframe: str
    enriched_data: Dict[str, Any]
    recent_rows: Dict[str, deque]

    def get_indicator_value(self, indicator_name: str) -> Optional[float]:
        """
        Get a specific indicator value from enriched data.

        Args:
            indicator_name: Name of the indicator (e.g., "ema_20", "rsi")

        Returns:
            Indicator value or None if not found
        """
        return self.enriched_data.get(indicator_name)

    def get_regime(self) -> Optional[str]:
        """
        Get the regime from enriched data.

        Returns:
            Regime string (e.g., "bull_high") or None
        """
        return self.enriched_data.get('regime')

    def get_regime_confidence(self) -> Optional[float]:
        """
        Get the regime confidence score.

        Returns:
            Confidence score (0-1) or None
        """
        return self.enriched_data.get('regime_confidence')


@dataclass(frozen=True)
class RegimeChangedEvent(Event):
    """
    Published when the market regime changes.

    This event is useful for strategies that need to adapt to regime changes.

    Attributes:
        symbol: Trading symbol
        timeframe: Timeframe
        old_regime: Previous regime
        new_regime: New regime
        confidence: Confidence score for the new regime
        is_transition: Whether this is a transition period
    """
    symbol: str
    timeframe: str
    old_regime: str
    new_regime: str
    confidence: float
    is_transition: bool = False


@dataclass(frozen=True)
class IndicatorCalculationErrorEvent(Event):
    """
    Published when indicator calculation fails.

    Attributes:
        symbol: Trading symbol
        timeframe: Timeframe
        error: Error message
        exception: Optional exception object
    """
    symbol: str
    timeframe: str
    error: str
    exception: Optional[Exception] = None
