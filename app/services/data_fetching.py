"""
Data Fetching Service.

This service wraps the DataSourceManager and publishes data events.
It is responsible for:
- Fetching streaming data for configured symbols/timeframes
- Detecting new candle formation
- Publishing DataFetchedEvent and NewCandleEvent
- Handling data fetch errors gracefully
"""

import logging
from typing import Dict, Optional, Any, List

import pandas as pd

from app.services.base import EventDrivenService, ServiceStatus, HealthStatus
from app.infrastructure.event_bus import EventBus
from app.events.data_events import DataFetchedEvent, NewCandleEvent, DataFetchErrorEvent
from app.data.data_manger import DataSourceManager
from app.data_source import has_new_candle


class DataFetchingService(EventDrivenService):
    """
    Service for fetching market data and publishing data events.

    This service wraps the DataSourceManager and is responsible for:
    - Fetching streaming data for multiple timeframes
    - Detecting new candles using has_new_candle()
    - Publishing DataFetchedEvent when data is retrieved
    - Publishing NewCandleEvent when new candle is detected
    - Publishing DataFetchErrorEvent when errors occur
    - Tracking last known bars for each timeframe

    Configuration:
        symbol: Trading symbol (e.g., "EURUSD")
        timeframes: List of timeframes to monitor (e.g., ["1", "5", "15"])
        candle_index: Bar index for new candle detection (default: 1)
        nbr_bars: Number of bars to fetch for streaming data (default: 3)

    Example:
        ```python
        data_source = DataSourceManager(mode="live", client=client, date_helper=date_helper)

        service = DataFetchingService(
            event_bus=event_bus,
            data_source=data_source,
            config={
                "symbol": "EURUSD",
                "timeframes": ["1", "5", "15"],
                "candle_index": 1,
                "nbr_bars": 3
            }
        )

        service.start()

        # Fetch data for all timeframes
        success_count = service.fetch_streaming_data()
        ```
    """

    def __init__(
        self,
        event_bus: EventBus,
        data_source: DataSourceManager,
        logger: Optional[logging.Logger] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize DataFetchingService.

        Args:
            event_bus: EventBus for publishing events
            data_source: DataSourceManager for fetching data
            logger: Optional logger
            config: Service configuration with keys:
                - symbol: Trading symbol (required)
                - timeframes: List of timeframes (required)
                - candle_index: Bar index for candle detection (default: 1)
                - nbr_bars: Number of bars to fetch (default: 3)
        """
        super().__init__(
            service_name="DataFetchingService",
            event_bus=event_bus,
            logger=logger,
            config=config,
        )

        self.data_source = data_source

        # Validate required config
        if not config:
            raise ValueError("DataFetchingService requires configuration")

        if "symbol" not in config:
            raise ValueError("Configuration must include 'symbol'")

        if "timeframes" not in config or not config["timeframes"]:
            raise ValueError("Configuration must include non-empty 'timeframes' list")

        # Configuration
        self.symbol = config["symbol"]
        self.timeframes: List[str] = config["timeframes"]
        self.candle_index = config.get("candle_index", 1)
        self.nbr_bars = config.get("nbr_bars", 3)

        # State: Track last known bar for each timeframe
        self.last_known_bars: Dict[str, Optional[pd.Series]] = {
            tf: None for tf in self.timeframes
        }

        # Metrics
        self._metrics["data_fetches"] = 0
        self._metrics["new_candles_detected"] = 0
        self._metrics["fetch_errors"] = 0

        self.logger.info(
            f"DataFetchingService initialized for {self.symbol} "
            f"with {len(self.timeframes)} timeframes: {self.timeframes}"
        )

    def start(self) -> None:
        """
        Start the DataFetchingService.

        This service does not subscribe to any events.
        It is typically called by an orchestrator to fetch data.
        """
        self.logger.info(f"Starting {self.service_name}...")

        # DataFetchingService doesn't subscribe to events
        # It's called directly by the orchestrator

        # Reinitialize last_known_bars for all timeframes
        # This is important when restarting the service
        self.last_known_bars = {tf: None for tf in self.timeframes}

        self._set_status(ServiceStatus.RUNNING)
        self.logger.info(f"{self.service_name} started successfully")

    def stop(self) -> None:
        """
        Stop the DataFetchingService gracefully.
        """
        self.logger.info(f"Stopping {self.service_name}...")

        # Unsubscribe from all events
        self.unsubscribe_all()

        # Clear state
        self.last_known_bars.clear()

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
            and self._metrics["fetch_errors"] < 10  # Less than 10 consecutive errors
        )

        return HealthStatus(
            service_name=self.service_name,
            status=self._status,
            is_healthy=is_healthy,
            uptime_seconds=self.get_uptime_seconds(),
            last_error=self._last_error,
            metrics=self.get_metrics(),
        )

    def fetch_streaming_data(self) -> int:
        """
        Fetch streaming data for all configured timeframes.

        For each timeframe:
        1. Fetch streaming data using data_source
        2. Publish DataFetchedEvent
        3. Check if new candle has formed
        4. If new candle, publish NewCandleEvent and update last_known_bar

        Returns:
            Number of successful fetches
        """
        if self._status != ServiceStatus.RUNNING:
            self.logger.warning(f"Cannot fetch data: service status is {self._status.value}")
            return 0

        success_count = 0

        for tf in self.timeframes:
            try:
                self.logger.info(f"🔄 [FETCH START] {self.symbol} {tf} - Requesting {self.nbr_bars} bars...")

                # Fetch streaming data
                df_stream = self.data_source.get_stream_data(
                    symbol=self.symbol,
                    timeframe=tf,
                    nbr_bars=self.nbr_bars,
                )

                # Validate data
                if df_stream.empty:
                    self.logger.warning(f"❌ [FETCH FAILED] {self.symbol} {tf} - Empty data received")
                    self._publish_fetch_error(tf, "Empty DataFrame received", None)
                    continue

                success_count += 1
                self._metrics["data_fetches"] += 1

                # Log fetched data details
                latest_bar = df_stream.iloc[-1]
                self.logger.info(
                    f"✅ [FETCH SUCCESS] {self.symbol} {tf} - Received {len(df_stream)} bars | "
                    f"Latest: time={latest_bar.name}, open={latest_bar['open']:.5f}, "
                    f"high={latest_bar['high']:.5f}, low={latest_bar['low']:.5f}, "
                    f"close={latest_bar['close']:.5f}, volume={latest_bar.get('tick_volume', 'N/A')}"
                )

                # Publish DataFetchedEvent
                data_event = DataFetchedEvent(
                    symbol=self.symbol,
                    timeframe=tf,
                    bars=df_stream,
                    num_bars=len(df_stream),
                )
                self.publish_event(data_event)
                self.logger.debug(f"📤 [EVENT] DataFetchedEvent published for {self.symbol} {tf}")

                # Check for new candle
                if has_new_candle(df_stream, self.last_known_bars[tf], self.candle_index):
                    # Get the new candle bar
                    new_bar = df_stream.iloc[-self.candle_index]

                    # Log old vs new candle comparison
                    old_bar = self.last_known_bars[tf]
                    if old_bar is not None:
                        self.logger.info(
                            f"🆕 [NEW CANDLE] {self.symbol} {tf} | "
                            f"Old: time={old_bar.name}, close={old_bar['close']:.5f} → "
                            f"New: time={new_bar.name}, close={new_bar['close']:.5f}"
                        )
                    else:
                        self.logger.info(
                            f"🆕 [NEW CANDLE] {self.symbol} {tf} | "
                            f"First candle: time={new_bar.name}, close={new_bar['close']:.5f}"
                        )

                    # Update last known bar
                    self.last_known_bars[tf] = new_bar

                    # Publish NewCandleEvent
                    candle_event = NewCandleEvent(
                        symbol=self.symbol,
                        timeframe=tf,
                        bar=new_bar,
                    )
                    self.publish_event(candle_event)
                    self.logger.debug(f"📤 [EVENT] NewCandleEvent published for {self.symbol} {tf}")

                    self._metrics["new_candles_detected"] += 1
                else:
                    self.logger.debug(f"⏸️  [NO NEW CANDLE] {self.symbol} {tf} - Same as previous")

            except Exception as e:
                self.logger.error(
                    f"Error fetching data for {self.symbol} {tf}: {e}",
                    exc_info=True
                )
                self._publish_fetch_error(tf, str(e), e)
                self._handle_error(e, f"fetch_streaming_data for {tf}")

        return success_count

    def fetch_single_timeframe(self, timeframe: str) -> bool:
        """
        Fetch streaming data for a single timeframe.

        This is useful for testing or when you need to fetch
        a specific timeframe without looping through all.

        Args:
            timeframe: Timeframe to fetch (must be in self.timeframes)

        Returns:
            True if successful, False otherwise
        """
        if timeframe not in self.timeframes:
            self.logger.error(
                f"Timeframe {timeframe} not in configured timeframes: {self.timeframes}"
            )
            return False

        if self._status != ServiceStatus.RUNNING:
            self.logger.warning(f"Cannot fetch data: service status is {self._status.value}")
            return False

        try:
            # Fetch streaming data
            df_stream = self.data_source.get_stream_data(
                symbol=self.symbol,
                timeframe=timeframe,
                nbr_bars=self.nbr_bars,
            )

            if df_stream.empty:
                self.logger.warning(f"Empty data received for {self.symbol} {timeframe}")
                self._publish_fetch_error(timeframe, "Empty DataFrame received", None)
                return False

            self._metrics["data_fetches"] += 1

            # Publish DataFetchedEvent
            data_event = DataFetchedEvent(
                symbol=self.symbol,
                timeframe=timeframe,
                bars=df_stream,
                num_bars=len(df_stream),
            )
            self.publish_event(data_event)

            # Check for new candle
            if has_new_candle(df_stream, self.last_known_bars[timeframe], self.candle_index):
                new_bar = df_stream.iloc[-self.candle_index]
                self.last_known_bars[timeframe] = new_bar

                candle_event = NewCandleEvent(
                    symbol=self.symbol,
                    timeframe=timeframe,
                    bar=new_bar,
                )
                self.publish_event(candle_event)

                self._metrics["new_candles_detected"] += 1

                self.logger.info(
                    f"New candle detected: {self.symbol} {timeframe} "
                    f"close={candle_event.get_close():.5f}"
                )

            return True

        except Exception as e:
            self.logger.error(
                f"Error fetching data for {self.symbol} {timeframe}: {e}",
                exc_info=True
            )
            self._publish_fetch_error(timeframe, str(e), e)
            self._handle_error(e, f"fetch_single_timeframe {timeframe}")
            return False

    def reset_last_known_bars(self, timeframe: Optional[str] = None) -> None:
        """
        Reset last known bars for a timeframe or all timeframes.

        This is useful for testing or when you need to force
        new candle detection.

        Args:
            timeframe: Specific timeframe to reset, or None for all
        """
        if timeframe is None:
            # Reset all
            self.last_known_bars = {tf: None for tf in self.timeframes}
            self.logger.info("Reset last known bars for all timeframes")
        elif timeframe in self.timeframes:
            self.last_known_bars[timeframe] = None
            self.logger.info(f"Reset last known bar for {timeframe}")
        else:
            self.logger.warning(
                f"Cannot reset {timeframe}: not in configured timeframes"
            )

    def _publish_fetch_error(
        self,
        timeframe: str,
        error_msg: str,
        exception: Optional[Exception],
    ) -> None:
        """
        Publish a DataFetchErrorEvent.

        Args:
            timeframe: Timeframe that failed
            error_msg: Error message
            exception: Optional exception object
        """
        try:
            error_event = DataFetchErrorEvent(
                symbol=self.symbol,
                timeframe=timeframe,
                error=error_msg,
                exception=exception,
            )
            self.publish_event(error_event)
            self._metrics["fetch_errors"] += 1

        except Exception as e:
            self.logger.error(f"Failed to publish DataFetchErrorEvent: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get service metrics including data-specific metrics.

        Returns:
            Dictionary with metrics
        """
        base_metrics = super().get_metrics()

        # Add data-specific metrics
        return {
            **base_metrics,
            "timeframes_count": len(self.timeframes),
            "data_fetches": self._metrics["data_fetches"],
            "new_candles_detected": self._metrics["new_candles_detected"],
            "fetch_errors": self._metrics["fetch_errors"],
        }
