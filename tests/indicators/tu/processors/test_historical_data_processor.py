import pandas as pd
import pytest
from unittest.mock import MagicMock

from app.indicators.indicator_manager import IndicatorManager
from app.indicators.processors.recent_row_processor import RecentRowsProcessor
from app.indicators.processors.historical_data_processor import HistoricalDataProcessor


@pytest.fixture
def sample_historical_data():
    return pd.DataFrame({
        'time': pd.date_range('2023-01-01 00:00:00', periods=10, freq='1min'),
        'open': range(10),
        'high': range(10),
        'low': range(10),
        'close': range(10),
        'volume': [100] * 10
    })


def test_initialize_from_historical(sample_historical_data):
    # Mock the IndicatorManager with sample historical data
    manager_1m = MagicMock(spec=IndicatorManager)
    manager_1m.historical_data = sample_historical_data.copy()

    manager_5m = MagicMock(spec=IndicatorManager)
    manager_5m.historical_data = sample_historical_data.copy()

    # Set up the recent rows processor
    recent_rows_processor = RecentRowsProcessor(timeframes=['1m', '5m'], max_rows=10)

    # Inject into HistoricalDataProcessor
    processor = HistoricalDataProcessor(recent_rows_processor)

    # Create the managers dict
    managers = {
        '1m': manager_1m,
        '5m': manager_5m,
    }

    # Run the method
    processor.initialize_from_historical(managers)

    # Check that the most recent 7 rows were added to each timeframe
    assert recent_rows_processor.get_row_count('1m') == 7
    assert recent_rows_processor.get_row_count('5m') == 7

    latest_1m = recent_rows_processor.get_latest_row('1m')
    latest_5m = recent_rows_processor.get_latest_row('5m')

    # Check that the latest row matches the last row of the historical data
    expected_latest = sample_historical_data.tail(1).iloc[0]
    pd.testing.assert_series_equal(latest_1m[expected_latest.index], expected_latest, check_names=False)
    pd.testing.assert_series_equal(latest_5m[expected_latest.index], expected_latest, check_names=False)
