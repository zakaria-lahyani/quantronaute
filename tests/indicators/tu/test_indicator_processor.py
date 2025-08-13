import pytest
import pandas as pd

from app.indicators.indicator_processor import IndicatorProcessor

@pytest.fixture
def sample_configs():
    return {
        '1m': {'sma_3': {'period': 3}, 'rsi_2': {'period': 2}},
        '5m': {'sma_2': {'period': 2}}
    }

@pytest.fixture
def sample_historicals():
    # Create a simple DataFrame for each timeframe
    df_1m = pd.DataFrame({
        'time': pd.date_range('2023-01-01 09:00', periods=10, freq='1min'),
        'open': range(10, 20),
        'high': range(11, 21),
        'low': range(9, 19),
        'close': range(10, 20),
        'volume': [1000 + i*10 for i in range(10)]
    })
    df_5m = pd.DataFrame({
        'time': pd.date_range('2023-01-01 09:00', periods=5, freq='5min'),
        'open': range(20, 25),
        'high': range(21, 26),
        'low': range(19, 24),
        'close': range(20, 25),
        'volume': [2000 + i*20 for i in range(5)]
    })
    return {'1m': df_1m, '5m': df_5m}

def test_indicator_processor_e2e(sample_configs, sample_historicals):
    # Initialize processor with real classes and data
    processor = IndicatorProcessor(sample_configs, sample_historicals, is_bulk=False)

    # Process a new row for 1m
    new_row = pd.Series({
        'time': pd.Timestamp('2023-01-01 09:10'),
        'open': 20,
        'high': 21,
        'low': 19,
        'close': 20,
        'volume': 1100
    })
    result = processor.process_new_row('1m', new_row)

    # Check that indicators are present
    # assert 'sma_3' in result.index
    assert 'rsi_2' in result.index

    # Check that the values are floats (or NaN if not enough data)
    # assert isinstance(result['sma_3'], float) or pd.isna(result['sma_3'])
    assert isinstance(result['rsi_2'], float) or pd.isna(result['rsi_2'])

    # Get recent rows and check indicators are present
    recent = processor.get_recent_rows('1m')
    assert 'sma_3' in recent.columns
    assert 'rsi_2' in recent.columns

    # Multi-timeframe processing
    mtf_data = {
        '1m': new_row,
        '5m': pd.Series({
            'time': pd.Timestamp('2023-01-01 09:10'),
            'open': 25,
            'high': 26,
            'low': 24,
            'close': 25,
            'volume': 2100
        })
    }
    mtf_result = processor.process_new_row_mtf(mtf_data)
    assert '1m' in mtf_result and '5m' in mtf_result
    assert 'sma_3' in mtf_result['1m'].index
    assert 'sma_2' in mtf_result['5m'].index

    # Optionally: test get_historical_data, get_indicator_config, etc.
    hist = processor.get_historical_indicator_data('1m')
    assert isinstance(hist, pd.DataFrame)


    empty_row = pd.Series({
        'time': pd.Timestamp('2023-01-01 08:00'),
        'open': 0, 'high': 0, 'low': 0, 'close': 0, 'volume': 0
    })
    result2 = processor.process_new_row('1m', empty_row)
    assert 'sma_3' in result2.index