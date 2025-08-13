import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from tests.indicators.reader import load_test_data

from app.indicators.indicator_factory import IndicatorFactory
from app.indicators.indicator_manager import IndicatorManager
from app.indicators.indicator_processor import IndicatorProcessor
from app.indicators.processors.historical_data_processor import HistoricalDataProcessor
from app.indicators.processors.recent_row_processor import RecentRowsProcessor

FILENAME = "history.csv"


@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)


@pytest.fixture
def sample_config():
    return {
        'rsi_14': {'period': 14, 'signal_period': 9},
        'sma_20': {'period': 20},
        'ema_50': {'period': 50},
        'bb_20': {'window': 20, 'num_std_dev': 2},
        'macd_default': {'fast': 12, 'slow': 26, 'signal': 9},
        'atr_14': {'window': 14},
        'adx_14': {'period': 14},
        'supertrend_10': {'period': 10, 'multiplier': 3}
    }


class TestIndicatorIntegration:
    
    def test_end_to_end_indicator_processing(self, loaded_data, sample_config):
        df = loaded_data.copy()
        
        # Create indicator manager
        manager = IndicatorManager(sample_config)
        
        # Process historical data
        processed_df = manager.process_df(df)
        
        # Check that all indicators were added
        expected_columns = [
            'rsi_14', 'signal_rsi_14',
            'sma_20',
            'ema_50',
            'bb_20_upper', 'bb_20_middle', 'bb_20_lower', 'bb_20_percent_b',
            'macd_default', 'macd_default_signal', 'macd_default_hist',
            'atr_14',
            'adx_14', 'adx_14_plus_di', 'adx_14_minus_di',
            'supertrend_10', 'trend_supertrend_10'
        ]
        
        for col in expected_columns:
            assert col in processed_df.columns, f"Missing column: {col}"
        
        # Verify data integrity
        assert len(processed_df) == len(df)
        
        # Check that original columns are preserved
        for col in df.columns:
            assert col in processed_df.columns
            assert processed_df[col].equals(df[col])
    
    def test_incremental_updates_match_batch(self, loaded_data, sample_config):
        df = loaded_data.copy()
        
        # Batch processing
        manager_batch = IndicatorManager(sample_config)
        batch_result = manager_batch.process_df(df)
        
        # Incremental processing
        manager_inc = IndicatorManager(sample_config)
        
        # Process row by row
        incremental_results = []
        for idx, row in df.iterrows():
            result = manager_inc.process_row(row)
            incremental_results.append(result)
        
        inc_df = pd.DataFrame(incremental_results)
        
        # Compare results for indicators that should match
        # (Some indicators need warmup period, so we check after initial rows)
        start_idx = 50  # Skip initial warmup period
        
        for col in batch_result.columns:
            if col in df.columns:
                continue  # Skip original columns
            
            batch_vals = batch_result[col].values[start_idx:]
            inc_vals = inc_df[col].values[start_idx:]
            
            # Filter out NaN values for comparison
            valid_idx = ~np.isnan(batch_vals) & ~np.isnan(inc_vals)
            
            if np.any(valid_idx):
                assert np.allclose(
                    batch_vals[valid_idx], 
                    inc_vals[valid_idx],
                    rtol=1e-5,
                    atol=1e-8
                ), f"Mismatch in column {col}"
    
    def test_indicator_processor_with_historical_data(self, loaded_data):
        df = loaded_data.copy()
        
        # Create processor with historical data processor
        processor = IndicatorProcessor(HistoricalDataProcessor())
        
        # Simple config
        config = {
            'rsi_14': {'period': 14, 'signal_period': 9},
            'sma_20': {'period': 20}
        }
        
        # Process data
        result = processor.process(df, config)
        
        # Check result
        assert 'rsi_14' in result.columns
        assert 'signal_rsi_14' in result.columns
        assert 'sma_20' in result.columns
        
        # Verify NaN handling
        # RSI should have NaN for first 14 rows
        assert np.all(np.isnan(result['rsi_14'].values[:14]))
        assert not np.all(np.isnan(result['rsi_14'].values[15:]))
        
        # SMA should have NaN for first 19 rows
        assert np.all(np.isnan(result['sma_20'].values[:19]))
        assert not np.all(np.isnan(result['sma_20'].values[20:]))
    
    def test_indicator_processor_with_recent_row(self, loaded_data):
        df = loaded_data.copy()
        
        # Create processor with recent row processor
        processor = IndicatorProcessor(RecentRowsProcessor())
        
        # Simple config
        config = {
            'rsi_14': {'period': 14, 'signal_period': 9},
            'ema_20': {'period': 20}
        }
        
        # Take last row as recent data
        recent_row = df.iloc[-1]
        
        # Process data
        result = processor.process(recent_row, config)
        
        # Check result is a dict/Series
        assert isinstance(result, (dict, pd.Series))
        
        # Check that indicator columns are present
        assert 'rsi_14' in result
        assert 'signal_rsi_14' in result
        assert 'ema_20' in result
    
    def test_indicator_factory_creates_correct_handlers(self, sample_config):
        factory = IndicatorFactory(sample_config)
        handlers = factory.create_handlers()
        
        # Check all indicators were created
        assert len(handlers) == len(sample_config)
        
        # Check specific handler properties
        assert 'rsi_14' in handlers
        assert handlers['rsi_14'].name == 'rsi_14'
        
        # Check that parameters were passed correctly
        rsi_handler = handlers['rsi_14']
        assert hasattr(rsi_handler.indicator, 'period')
        assert rsi_handler.indicator.period == 14
    
    def test_complex_indicator_dependencies(self, loaded_data):
        df = loaded_data.copy()
        
        # Config with indicators that might have dependencies
        config = {
            'ichimoku_default': {
                'tenkan_period': 9,
                'kijun_period': 26,
                'senkou_b_period': 52,
                'chikou_shift': 26
            },
            'stochrsi_default': {},
            'keltner_20': {
                'ema_window': 20,
                'atr_window': 10,
                'multiplier': 2
            }
        }
        
        manager = IndicatorManager(config)
        result = manager.process_df(df)
        
        # Check Ichimoku outputs
        ichimoku_cols = [
            'ichimoku_default_tenkan',
            'ichimoku_default_kijun',
            'ichimoku_default_senkou_a',
            'ichimoku_default_senkou_b',
            'ichimoku_default_chikou',
            'ichimoku_default_cloud'
        ]
        for col in ichimoku_cols:
            assert col in result.columns
        
        # Check Stochastic RSI outputs
        assert 'stochrsi_default_k' in result.columns
        assert 'stochrsi_default_d' in result.columns
        
        # Check Keltner Channel outputs
        keltner_cols = [
            'keltner_20_upper',
            'keltner_20_middle',
            'keltner_20_lower',
            'keltner_20_percent_b'
        ]
        for col in keltner_cols:
            assert col in result.columns
    
    def test_indicator_manager_handles_missing_data(self):
        # Create DataFrame with missing values
        df = pd.DataFrame({
            'high': [105, 110, np.nan, 108, 112],
            'low': [95, 100, 98, np.nan, 102],
            'close': [100, 105, 103, 106, 110],
            'tick_volume': [1000, 1500, 1200, 1300, 1400]
        })
        
        config = {
            'sma_3': {'period': 3},
            'atr_3': {'window': 3}
        }
        
        manager = IndicatorManager(config)
        
        # Should handle missing data gracefully
        result = manager.process_df(df)
        
        assert 'sma_3' in result.columns
        assert 'atr_3' in result.columns
        
        # SMA should work on close prices
        assert not np.isnan(result['sma_3'].iloc[-1])
        
        # ATR might have NaN due to missing high/low
        # But shouldn't crash
        assert len(result) == len(df)
    
    def test_indicator_manager_preserves_row_order(self, loaded_data):
        df = loaded_data.copy()
        
        # Add index to track order
        df['original_index'] = range(len(df))
        
        config = {
            'rsi_14': {'period': 14, 'signal_period': 9},
            'bb_20': {'window': 20, 'num_std_dev': 2}
        }
        
        manager = IndicatorManager(config)
        result = manager.process_df(df)
        
        # Check order is preserved
        assert np.array_equal(
            result['original_index'].values,
            df['original_index'].values
        )
    
    def test_indicator_updates_are_stateful(self, loaded_data):
        df = loaded_data.copy()
        
        config = {
            'ema_10': {'period': 10},
            'rsi_14': {'period': 14, 'signal_period': 9}
        }
        
        manager = IndicatorManager(config)
        
        # Process first half of data
        first_half = df.iloc[:len(df)//2]
        for _, row in first_half.iterrows():
            manager.process_row(row)
        
        # Process second half - should continue from previous state
        second_half = df.iloc[len(df)//2:]
        results = []
        for _, row in second_half.iterrows():
            result = manager.process_row(row)
            results.append(result)
        
        # The EMA should be continuous (not restart)
        # Check that we get non-NaN values immediately
        assert not np.isnan(results[0]['ema_10'])
        
        # Compare with fresh calculation
        manager_fresh = IndicatorManager(config)
        fresh_result = manager_fresh.process_df(df)
        
        # The stateful processing should match batch for later values
        start_idx = len(df)//2 + 20  # Give some buffer
        for i in range(start_idx - len(df)//2, len(results)):
            actual_idx = len(df)//2 + i
            if actual_idx < len(df):
                assert np.isclose(
                    results[i]['ema_10'],
                    fresh_result['ema_10'].iloc[actual_idx],
                    rtol=1e-5
                )


class TestIndicatorErrorHandling:
    
    def test_invalid_indicator_type(self):
        config = {
            'invalid_indicator': {'param': 123}
        }
        
        factory = IndicatorFactory(config)
        handlers = factory.create_handlers()
        
        # Should skip invalid indicator
        assert 'invalid_indicator' not in handlers
        assert len(handlers) == 0
    
    def test_missing_required_columns(self):
        # DataFrame missing required columns
        df = pd.DataFrame({
            'close': [100, 105, 103, 106, 110]
            # Missing 'high', 'low', 'tick_volume'
        })
        
        config = {
            'atr_14': {'window': 14},  # Requires high, low, close
            'obv_14': {'period': 14},  # Requires close, tick_volume
            'sma_3': {'period': 3}  # Only requires close
        }
        
        manager = IndicatorManager(config)
        
        # Should process what it can
        result = manager.process_df(df)
        
        # SMA should work
        assert 'sma_3' in result.columns
        assert not np.all(np.isnan(result['sma_3']))
        
        # ATR and OBV might not work due to missing columns
        # But shouldn't crash the entire process
        assert len(result) == len(df)
    
    def test_extreme_parameter_values(self, loaded_data):
        df = loaded_data.copy()
        
        # Test with extreme parameters
        config = {
            'sma_1': {'period': 1},  # Minimum period
            'sma_1000': {'period': 1000},  # Very large period
            'bb_2': {'window': 2, 'num_std_dev': 0.5},  # Small window
            'rsi_2': {'period': 2, 'signal_period': 1}  # Very short RSI
        }
        
        manager = IndicatorManager(config)
        
        # Should handle extreme values without crashing
        result = manager.process_df(df)
        
        assert 'sma_1' in result.columns
        assert 'sma_1000' in result.columns
        assert 'bb_2_upper' in result.columns
        assert 'rsi_2' in result.columns
        
        # SMA with period 1 should equal close
        assert np.allclose(
            result['sma_1'].values[~np.isnan(result['sma_1'])],
            df['close'].values[~np.isnan(result['sma_1'])],
            rtol=1e-10
        )
        
        # SMA with period 1000 should be mostly NaN (not enough data)
        if len(df) < 1000:
            assert np.all(np.isnan(result['sma_1000'].values[:999]))