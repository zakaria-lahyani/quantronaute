from indicators.indicator_manager import IndicatorManager
from indicators.processors.recent_row_processor import RecentRowsProcessor

from typing import Dict

class HistoricalDataProcessor:
    DEFAULT_MAX_ROWS = 7
    def __init__(self, recent_rows_manager: RecentRowsProcessor, max_rows: int = DEFAULT_MAX_ROWS):
        self.recent_rows_manager = recent_rows_manager
        self.max_rows = max_rows

    def initialize_from_historical(self, managers: Dict[str, IndicatorManager]) -> None:
        """Initialize recent rows from historical data"""
        for tf, manager in managers.items():
            self._initialize_timeframe(tf, manager)

    def _initialize_timeframe(self, tf: str, manager: IndicatorManager) -> None:
        """Initialize recent rows for a single timeframe"""
        last_rows = manager.historical_data.tail(self.max_rows)

        for _, row in last_rows.iterrows():
            self.recent_rows_manager.add_or_update_row(tf, row)

