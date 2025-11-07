"""
Indicator Calculation Service.

This service wraps the IndicatorProcessor and RegimeManager and publishes indicator events.
It is responsible for:
- Subscribing to NewCandleEvent
- Updating regime detection for new candles
- Calculating indicators with regime data
- Publishing IndicatorsCalculatedEvent
- Publishing RegimeChangedEvent when regime changes
- Handling calculation errors gracefully
"""

import logging
from typing import Dict, Optional, Any
from collections import deque

import pandas as pd

from app.services.base import EventDrivenService, ServiceStatus, HealthStatus
from app.infrastructure.event_bus import EventBus
from app.events.data_events import NewCandleEvent
from app.events.indicator_events import (
    IndicatorsCalculatedEvent,
    RegimeChangedEvent,
    IndicatorCalculationErrorEvent,
)
from app.indicators.indicator_processor import IndicatorProcessor
from app.regime.regime_manager import RegimeManager


class IndicatorCalculationService(EventDrivenService):
    """
    Service for calculating indicators and detecting regime changes.

    This service wraps the IndicatorProcessor and RegimeManager and is responsible for:
    - Subscribing to NewCandleEvent
    - Updating regime detection when new candle arrives
    - Processing new candle through indicator calculation
    - Publishing IndicatorsCalculatedEvent when calculation succeeds
    - Publishing RegimeChangedEvent when regime changes
    - Publishing IndicatorCalculationErrorEvent when errors occur
    - Tracking calculation metrics

    Configuration:
        symbol: Trading symbol (e.g., "EURUSD") - for event filtering
        timeframes: List of timeframes to process (e.g., ["1", "5", "15"])
        track_regime_changes: Whether to publish RegimeChangedEvent (default: True)

    Example:
        ```python
        indicator_processor = IndicatorProcessor(
            configs=indicator_config,
            historicals=historicals,
            is_bulk=False
        )

        regime_manager = RegimeManager(
            warmup_bars=500,
            persist_n=2,
            transition_bars=3,
            bb_threshold_len=200
        )
        regime_manager.setup(timeframes, historicals)

        service = IndicatorCalculationService(
            event_bus=event_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config={
                "symbol": "EURUSD",
                "timeframes": ["1", "5", "15"],
                "track_regime_changes": True
            }
        )

        service.start()
        # Service now listens for NewCandleEvent and processes automatically
        ```
    """

    def __init__(
        self,
        event_bus: EventBus,
        indicator_processor: IndicatorProcessor,
        regime_manager: RegimeManager,
        logger: Optional[logging.Logger] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize IndicatorCalculationService.

        Args:
            event_bus: EventBus for publishing/subscribing events
            indicator_processor: IndicatorProcessor for calculating indicators
            regime_manager: RegimeManager for regime detection
            logger: Optional logger
            config: Service configuration with keys:
                - symbol: Trading symbol (required)
                - timeframes: List of timeframes (required)
                - track_regime_changes: Track regime changes (default: True)
        """
        super().__init__(
            service_name="IndicatorCalculationService",
            event_bus=event_bus,
            logger=logger,
            config=config,
        )

        self.indicator_processor = indicator_processor
        self.regime_manager = regime_manager

        # Validate required config
        if not config:
            raise ValueError("IndicatorCalculationService requires configuration")

        if "symbol" not in config:
            raise ValueError("Configuration must include 'symbol'")

        if "timeframes" not in config or not config["timeframes"]:
            raise ValueError("Configuration must include non-empty 'timeframes' list")

        # Configuration
        self.symbol = config["symbol"]
        self.timeframes: list[str] = config["timeframes"]
        self.track_regime_changes = config.get("track_regime_changes", True)

        # State: Track last known regime for each timeframe
        self.last_known_regimes: Dict[str, Optional[str]] = {
            tf: None for tf in self.timeframes
        }

        # Metrics
        self._metrics["indicators_calculated"] = 0
        self._metrics["regime_changes_detected"] = 0
        self._metrics["calculation_errors"] = 0

        self.logger.info(
            f"IndicatorCalculationService initialized for {self.symbol} "
            f"with {len(self.timeframes)} timeframes: {self.timeframes}"
        )

    def start(self) -> None:
        """
        Start the IndicatorCalculationService.

        Subscribes to NewCandleEvent for all configured timeframes.
        """
        self.logger.info(f"Starting {self.service_name}...")

        # Subscribe to NewCandleEvent
        self.subscribe_to_event(NewCandleEvent, self._on_new_candle)

        self._set_status(ServiceStatus.RUNNING)
        self.logger.info(f"{self.service_name} started successfully")

    def stop(self) -> None:
        """
        Stop the IndicatorCalculationService gracefully.
        """
        self.logger.info(f"Stopping {self.service_name}...")

        # Unsubscribe from all events
        self.unsubscribe_all()

        # Clear state
        self.last_known_regimes.clear()

        self._set_status(ServiceStatus.STOPPED)
        self.logger.info(f"{self.service_name} stopped")

    def health_check(self) -> HealthStatus:
        """
        Check service health.

        Returns:
            HealthStatus indicating current health
        """
        is_healthy = (
            self._status == ServiceStatus.RUNNING
            and self._metrics["calculation_errors"] < 10  # Less than 10 consecutive errors
        )

        return HealthStatus(
            service_name=self.service_name,
            status=self._status,
            is_healthy=is_healthy,
            uptime_seconds=self.get_uptime_seconds(),
            last_error=self._last_error,
            metrics=self.get_metrics(),
        )

    def _on_new_candle(self, event: NewCandleEvent) -> None:
        """
        Handle NewCandleEvent.

        When a new candle arrives:
        1. Filter by symbol and timeframe
        2. Update regime detection
        3. Calculate indicators with regime data
        4. Publish IndicatorsCalculatedEvent
        5. Publish RegimeChangedEvent if regime changed

        Args:
            event: NewCandleEvent with new candle data
        """
        self._metrics["events_received"] += 1

        # Filter by symbol
        if event.symbol != self.symbol:
            self.logger.debug(
                f"Ignoring NewCandleEvent for {event.symbol} (configured for {self.symbol})"
            )
            return

        # Filter by timeframe
        if event.timeframe not in self.timeframes:
            self.logger.debug(
                f"Ignoring NewCandleEvent for timeframe {event.timeframe} "
                f"(configured for {self.timeframes})"
            )
            return

        # Process the new candle
        try:
            self._process_new_candle(event.timeframe, event.bar)

        except Exception as e:
            self.logger.error(
                f"Error processing new candle for {event.symbol} {event.timeframe}: {e}",
                exc_info=True,
            )
            self._publish_calculation_error(event.timeframe, str(e), e)
            self._handle_error(e, f"_on_new_candle for {event.timeframe}")

    def _process_new_candle(self, timeframe: str, bar: pd.Series) -> None:
        """
        Process a new candle through regime detection and indicator calculation.

        Args:
            timeframe: Timeframe identifier
            bar: New candle bar as pandas Series
        """
        self.logger.info(
            f"📊 [INDICATOR START] {self.symbol} {timeframe} | "
            f"Bar: time={bar.name}, close={bar['close']:.5f}"
        )

        # Step 1: Update regime detection
        regime_data = self.regime_manager.update(timeframe, bar)

        # Check if regime changed
        previous_regime = self.last_known_regimes[timeframe]
        current_regime = regime_data.get("regime")

        regime_changed = (
            previous_regime is not None
            and current_regime != previous_regime
            and self.track_regime_changes
        )

        if current_regime:
            self.last_known_regimes[timeframe] = current_regime

        # Log regime info
        self.logger.info(
            f"🎯 [REGIME] {self.symbol} {timeframe} | "
            f"regime={current_regime}, confidence={regime_data.get('regime_confidence', 'N/A')}, "
            f"is_transition={regime_data.get('is_transition', False)}, "
            f"changed={regime_changed} (prev={previous_regime})"
        )

        # Step 2: Calculate indicators with regime data
        processed_row = self.indicator_processor.process_new_row(
            timeframe, bar, regime_data
        )

        # Step 3: Get recent rows for enriched data
        recent_rows = self.indicator_processor.get_recent_rows()

        self._metrics["indicators_calculated"] += 1

        # Log indicator calculation result
        tf_recent = recent_rows.get(timeframe)
        num_recent = len(tf_recent) if tf_recent else 0
        self.logger.info(
            f"✅ [INDICATOR SUCCESS] {self.symbol} {timeframe} | "
            f"Recent rows available: {num_recent}, regime={current_regime}"
        )

        # Step 4: Publish IndicatorsCalculatedEvent
        indicators_event = IndicatorsCalculatedEvent(
            symbol=self.symbol,
            timeframe=timeframe,
            enriched_data={
                "regime": regime_data.get("regime"),
                "regime_confidence": regime_data.get("regime_confidence"),
                "is_transition": regime_data.get("is_transition"),
            },
            recent_rows=recent_rows,
        )
        self.publish_event(indicators_event)

        # Step 5: Publish RegimeChangedEvent if regime changed
        if regime_changed:
            self._publish_regime_change(
                timeframe,
                previous_regime,
                current_regime,
                regime_data.get("regime_confidence", 0.0),
                regime_data.get("is_transition", False),
            )

    def _publish_regime_change(
        self,
        timeframe: str,
        old_regime: str,
        new_regime: str,
        confidence: float,
        is_transition: bool,
    ) -> None:
        """
        Publish RegimeChangedEvent.

        Args:
            timeframe: Timeframe identifier
            old_regime: Previous regime
            new_regime: New regime
            confidence: Regime confidence (0-1)
            is_transition: Whether in transition
        """
        try:
            regime_event = RegimeChangedEvent(
                symbol=self.symbol,
                timeframe=timeframe,
                old_regime=old_regime,
                new_regime=new_regime,
                confidence=confidence,
                is_transition=is_transition,
            )
            self.publish_event(regime_event)

            self._metrics["regime_changes_detected"] += 1

            self.logger.info(
                f"Regime change detected: {self.symbol} {timeframe} "
                f"{old_regime} -> {new_regime} (confidence: {confidence:.2%})"
            )

        except Exception as e:
            self.logger.error(f"Failed to publish RegimeChangedEvent: {e}")

    def _publish_calculation_error(
        self,
        timeframe: str,
        error_msg: str,
        exception: Optional[Exception],
    ) -> None:
        """
        Publish IndicatorCalculationErrorEvent.

        Args:
            timeframe: Timeframe that failed
            error_msg: Error message
            exception: Optional exception object
        """
        try:
            error_event = IndicatorCalculationErrorEvent(
                symbol=self.symbol,
                timeframe=timeframe,
                error=error_msg,
                exception=exception,
            )
            self.publish_event(error_event)
            self._metrics["calculation_errors"] += 1

        except Exception as e:
            self.logger.error(f"Failed to publish IndicatorCalculationErrorEvent: {e}")

    def get_recent_rows(self) -> Dict[str, deque]:
        """
        Get recent rows with indicators from the processor.

        Returns:
            Dictionary mapping timeframe to deque of recent rows
        """
        return self.indicator_processor.get_recent_rows()

    def get_latest_row(self, timeframe: str) -> Optional[pd.Series]:
        """
        Get the latest processed row for a timeframe.

        Args:
            timeframe: Timeframe identifier

        Returns:
            Latest row with indicators, or None
        """
        if timeframe not in self.timeframes:
            self.logger.warning(
                f"Timeframe {timeframe} not in configured timeframes: {self.timeframes}"
            )
            return None

        return self.indicator_processor.get_latest_row(timeframe)

    def get_current_regime(self, timeframe: str) -> Optional[str]:
        """
        Get current regime for a timeframe.

        Args:
            timeframe: Timeframe identifier

        Returns:
            Current regime name, or None
        """
        if timeframe not in self.timeframes:
            self.logger.warning(
                f"Timeframe {timeframe} not in configured timeframes: {self.timeframes}"
            )
            return None

        return self.last_known_regimes.get(timeframe)

    def get_all_regimes(self) -> Dict[str, Optional[str]]:
        """
        Get current regimes for all timeframes.

        Returns:
            Dictionary mapping timeframe to regime
        """
        return self.last_known_regimes.copy()

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get service metrics including indicator-specific metrics.

        Returns:
            Dictionary with metrics
        """
        base_metrics = super().get_metrics()

        # Add indicator-specific metrics
        return {
            **base_metrics,
            "timeframes_count": len(self.timeframes),
            "indicators_calculated": self._metrics["indicators_calculated"],
            "regime_changes_detected": self._metrics["regime_changes_detected"],
            "calculation_errors": self._metrics["calculation_errors"],
        }
