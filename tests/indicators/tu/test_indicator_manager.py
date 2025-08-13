"""
IndicatorManager Test Suite
==========================

This test suite validates the IndicatorManager class, which orchestrates the computation
of multiple technical indicators over historical or live market data.

Expected Behavior Overview:
--------------------------

1. INITIALIZATION:
   - Creates handlers via IndicatorFactory from configuration
   - Preserves original historical data (immutable)
   - Chooses computation mode: bulk (vectorized) or warmup (row-by-row)
   - Processes all indicators and stores results in historical_data

2. BULK MODE (is_bulk=True):
   - Uses handler.bulk_compute() for vectorized processing
   - Faster for large datasets
   - Each handler processes entire DataFrame at once

3. WARMUP MODE (is_bulk=False):
   - Uses handler.compute() for row-by-row processing
   - More flexible, mimics live processing
   - Each handler processes one row at a time

4. LIVE PROCESSING:
   - compute_indicators() processes single rows for streaming data
   - Always uses handler.compute() regardless of initialization mode
   - Input row remains unmodified

5. ERROR HANDLING:
   - Follows "crash-hard" philosophy
   - Factory errors crash the application
   - Handler computation errors crash the application
   - No graceful fallbacks or NaN padding

6. DATA INTEGRITY:
   - Original data is never modified
   - Input parameters are preserved
   - Copies are made before processing
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from app.indicators.indicator_manager import IndicatorManager


class TestIndicatorManager:
    """
    Comprehensive test suite for IndicatorManager.

    Tests cover all major use cases including initialization modes,
    computation methods, error handling, and data integrity.
    """

    @pytest.fixture
    def sample_historical_data(self):
        """
        Sample historical market data for testing.

        Expected Behavior:
        - Contains standard OHLCV data with tick_volume
        - 5 rows of data for testing row-by-row processing
        - All required fields for common indicators

        Returns:
            pd.DataFrame: Market data with columns [open, high, low, close, volume, tick_volume]
        """
        return pd.DataFrame({
            'open': [100.0, 102.0, 101.0, 103.0, 105.0],
            'high': [105.0, 107.0, 106.0, 108.0, 110.0],
            'low': [95.0, 97.0, 96.0, 98.0, 100.0],
            'close': [102.0, 104.0, 103.0, 105.0, 107.0],
            'volume': [1000, 1100, 1200, 1300, 1400],
            'tick_volume': [1500, 1600, 1700, 1800, 1900]
        })

    @pytest.fixture
    def sample_config(self):
        """
        Sample indicator configuration for testing.

        Expected Behavior:
        - Contains 3 different indicator types (SMA, EMA, MACD)
        - Tests single-output (SMA, EMA) and multi-output (MACD) indicators
        - Uses realistic parameter values

        Returns:
            dict: Configuration mapping indicator names to their parameters
        """
        return {
            'sma_20': {'type': 'sma', 'period': 20},
            'ema_12': {'type': 'ema', 'period': 12},
            'macd_default': {'type': 'macd', 'fast': 12, 'slow': 26, 'signal': 9}
        }

    @pytest.fixture
    def mock_handlers(self):
        """
        Mock handlers that simulate real indicator behavior.

        Expected Behavior:
        - SMA handler: Adds single 'sma_20' column with fixed values
        - EMA handler: Adds single 'ema_12' column with fixed values
        - MACD handler: Adds three columns (macd, signal, histogram)
        - compute() methods return modified row with new columns
        - bulk_compute() methods return modified DataFrame with new columns

        Returns:
            dict: Mapping of handler names to mock handler objects
        """
        sma_handler = Mock()
        sma_handler.compute.side_effect = lambda row: self._add_to_row(row, 'sma_20', 102.5)
        sma_handler.bulk_compute.side_effect = lambda df: self._add_to_df(df, 'sma_20', [102.1, 102.2, 102.3, 102.4, 102.5])

        ema_handler = Mock()
        ema_handler.compute.side_effect = lambda row: self._add_to_row(row, 'ema_12', 103.2)
        ema_handler.bulk_compute.side_effect = lambda df: self._add_to_df(df, 'ema_12', [103.1, 103.2, 103.3, 103.4, 103.5])

        macd_handler = Mock()
        macd_handler.compute.side_effect = lambda row: self._add_multiple_to_row(
            row, {'macd_default': 1.5, 'macd_default_signal': 1.2, 'macd_default_hist': 0.3}
        )
        macd_handler.bulk_compute.side_effect = lambda df: self._add_multiple_to_df(
            df, {
                'macd_default': [1.1, 1.2, 1.3, 1.4, 1.5],
                'macd_default_signal': [1.0, 1.1, 1.2, 1.3, 1.4],
                'macd_default_hist': [0.1, 0.1, 0.1, 0.1, 0.1]
            }
        )

        return {
            'sma_20': sma_handler,
            'ema_12': ema_handler,
            'macd_default': macd_handler
        }

    def _add_to_row(self, row, col_name, value):
        """
        Helper to add single column to row.

        Expected Behavior:
        - Creates copy of input row (preserves original)
        - Adds new column with specified value
        - Returns modified copy
        """
        row = row.copy()
        row[col_name] = value
        return row

    def _add_to_df(self, df, col_name, values):
        """
        Helper to add single column to DataFrame.

        Expected Behavior:
        - Creates copy of input DataFrame (preserves original)
        - Adds new column with specified values
        - Returns modified copy
        """
        df = df.copy()
        df[col_name] = values
        return df

    def _add_multiple_to_row(self, row, columns_dict):
        """
        Helper to add multiple columns to row.

        Expected Behavior:
        - Creates copy of input row (preserves original)
        - Adds all columns from dictionary
        - Returns modified copy
        """
        row = row.copy()
        for col_name, value in columns_dict.items():
            row[col_name] = value
        return row

    def _add_multiple_to_df(self, df, columns_dict):
        """
        Helper to add multiple columns to DataFrame.

        Expected Behavior:
        - Creates copy of input DataFrame (preserves original)
        - Adds all columns from dictionary
        - Returns modified copy
        """
        df = df.copy()
        for col_name, values in columns_dict.items():
            df[col_name] = values
        return df

    @patch('indicators.indicator_manager.IndicatorFactory')
    def test_initialization_bulk_mode(self, mock_factory, sample_historical_data, sample_config, mock_handlers):
        """
        Test initialization with bulk computation mode.

        Expected Behavior:
        - IndicatorFactory is called with provided config
        - Handlers are created and stored
        - Original data is preserved in original_historical
        - bulk_compute() is called on each handler (not compute())
        - historical_data contains all indicator columns
        - Bulk mode is faster for large datasets
        """
        # Setup mock factory
        mock_factory_instance = Mock()
        mock_factory_instance.create_handlers.return_value = mock_handlers
        mock_factory.return_value = mock_factory_instance

        # Initialize manager in bulk mode
        manager = IndicatorManager(sample_historical_data, sample_config, is_bulk=True)

        # Verify factory was called correctly
        mock_factory.assert_called_once_with(sample_config)
        mock_factory_instance.create_handlers.assert_called_once()

        # Verify original data is preserved
        pd.testing.assert_frame_equal(manager.original_historical, sample_historical_data)

        # Verify handlers are stored
        assert manager.handlers == mock_handlers

        # Verify bulk computation was used
        for handler in mock_handlers.values():
            handler.bulk_compute.assert_called_once()
            handler.compute.assert_not_called()

        # Verify historical data has indicator columns
        assert 'sma_20' in manager.historical_data.columns
        assert 'ema_12' in manager.historical_data.columns
        assert 'macd_default' in manager.historical_data.columns

    @patch('indicators.indicator_manager.IndicatorFactory')
    def test_initialization_warmup_mode(self, mock_factory, sample_historical_data, sample_config, mock_handlers):
        """
        Test initialization with warmup (row-by-row) computation mode.

        Expected Behavior:
        - IndicatorFactory is called with provided config
        - Handlers are created and stored
        - compute() is called on each handler for each row
        - bulk_compute() is never called
        - historical_data contains all indicator columns
        - Warmup mode mimics live processing behavior
        """
        # Setup mock factory
        mock_factory_instance = Mock()
        mock_factory_instance.create_handlers.return_value = mock_handlers
        mock_factory.return_value = mock_factory_instance

        # Initialize manager in warmup mode
        manager = IndicatorManager(sample_historical_data, sample_config, is_bulk=False)

        # Verify factory was called correctly
        mock_factory.assert_called_once_with(sample_config)

        # Verify warmup computation was used
        for handler in mock_handlers.values():
            # Each handler should be called once per row (5 rows)
            assert handler.compute.call_count == 5
            handler.bulk_compute.assert_not_called()

        # Verify historical data has indicator columns
        assert 'sma_20' in manager.historical_data.columns
        assert 'ema_12' in manager.historical_data.columns
        assert 'macd_default' in manager.historical_data.columns

    @patch('indicators.indicator_manager.IndicatorFactory')
    def test_bulk_compute_method(self, mock_factory, sample_historical_data, sample_config, mock_handlers):
        """
        Test bulk_compute method directly.

        Expected Behavior:
        - Calls bulk_compute() on each handler exactly once
        - Returns DataFrame with all original columns preserved
        - Returns DataFrame with all indicator columns added
        - Original data values remain unchanged
        - Method can be called independently of initialization mode
        """
        # Setup mock factory
        mock_factory_instance = Mock()
        mock_factory_instance.create_handlers.return_value = mock_handlers
        mock_factory.return_value = mock_factory_instance

        # Initialize manager (doesn't matter which mode for this test)
        manager = IndicatorManager(sample_historical_data, sample_config, is_bulk=True)

        # Reset mock calls from initialization
        for handler in mock_handlers.values():
            handler.reset_mock()

        # Call bulk_compute directly
        result = manager.bulk_compute()

        # Verify each handler's bulk_compute was called once
        for handler in mock_handlers.values():
            handler.bulk_compute.assert_called_once()

        # Verify result has all expected columns
        expected_columns = list(sample_historical_data.columns) + ['sma_20', 'ema_12', 'macd_default', 'macd_default_signal', 'macd_default_hist']
        for col in expected_columns:
            assert col in result.columns

        # Verify original data columns are preserved
        for col in sample_historical_data.columns:
            pd.testing.assert_series_equal(result[col], sample_historical_data[col], check_names=False)

    @patch('indicators.indicator_manager.IndicatorFactory')
    def test_warmup_historical_method(self, mock_factory, sample_historical_data, sample_config, mock_handlers):
        """
        Test warmup_historical method directly.

        Expected Behavior:
        - Processes data row by row using handler.compute()
        - Each handler is called once per row in the dataset
        - Returns DataFrame with same number of rows as input
        - Returns DataFrame with all indicator columns added
        - Method simulates live processing on historical data
        """
        # Setup mock factory
        mock_factory_instance = Mock()
        mock_factory_instance.create_handlers.return_value = mock_handlers
        mock_factory.return_value = mock_factory_instance

        # Initialize manager
        manager = IndicatorManager(sample_historical_data, sample_config, is_bulk=True)

        # Reset mock calls from initialization
        for handler in mock_handlers.values():
            handler.reset_mock()

        # Call warmup_historical directly
        result = manager.warmup_historical()

        # Verify each handler's compute was called for each row
        for handler in mock_handlers.values():
            assert handler.compute.call_count == len(sample_historical_data)

        # Verify result structure
        assert len(result) == len(sample_historical_data)
        assert 'sma_20' in result.columns
        assert 'ema_12' in result.columns
        assert 'macd_default' in result.columns

    @patch('indicators.indicator_manager.IndicatorFactory')
    def test_get_historical_data(self, mock_factory, sample_historical_data, sample_config, mock_handlers):
        """
        Test get_historical_data method.

        Expected Behavior:
        - Returns the processed historical_data DataFrame
        - Contains all original market data columns
        - Contains all computed indicator columns
        - Is identical to manager.historical_data
        - Provides read-only access to processed data
        """
        # Setup mock factory
        mock_factory_instance = Mock()
        mock_factory_instance.create_handlers.return_value = mock_handlers
        mock_factory.return_value = mock_factory_instance

        # Initialize manager
        manager = IndicatorManager(sample_historical_data, sample_config, is_bulk=True)

        # Get historical data
        result = manager.get_historical_data()

        # Verify it returns the processed historical data
        pd.testing.assert_frame_equal(result, manager.historical_data)

        # Verify it has indicator columns
        assert 'sma_20' in result.columns
        assert 'ema_12' in result.columns
        assert 'macd_default' in result.columns

    @patch('indicators.indicator_manager.IndicatorFactory')
    def test_compute_indicators_single_row(self, mock_factory, sample_historical_data, sample_config, mock_handlers):
        """
        Test compute_indicators method for single row processing.

        Expected Behavior:
        - Processes single row through all handlers using compute()
        - Each handler is called exactly once
        - Returns row with all indicator values added
        - Used for live/streaming data processing
        - Independent of initialization mode (always uses compute())
        - Input row remains unmodified
        """
        # Setup mock factory
        mock_factory_instance = Mock()
        mock_factory_instance.create_handlers.return_value = mock_handlers
        mock_factory.return_value = mock_factory_instance

        # Initialize manager
        manager = IndicatorManager(sample_historical_data, sample_config, is_bulk=True)

        # Reset mock calls from initialization
        for handler in mock_handlers.values():
            handler.reset_mock()

        # Create a new row for live processing
        new_row = pd.Series({
            'open': 108.0,
            'high': 112.0,
            'low': 106.0,
            'close': 110.0,
            'volume': 1500,
            'tick_volume': 2000
        })

        # Compute indicators for the new row
        result = manager.compute_indicators(new_row)

        # Verify each handler's compute was called once
        for handler in mock_handlers.values():
            handler.compute.assert_called_once()

        # Verify result has indicator values
        assert 'sma_20' in result
        assert 'ema_12' in result
        assert 'macd_default' in result
        assert result['sma_20'] == 102.5
        assert result['ema_12'] == 103.2
        assert result['macd_default'] == 1.5

    @patch('indicators.indicator_manager.IndicatorFactory')
    def test_original_data_preservation(self, mock_factory, sample_historical_data, sample_config, mock_handlers):
        """
        Test that original historical data is preserved and not modified.

        Expected Behavior:
        - original_historical contains exact copy of input data
        - Input data parameter is never modified
        - original_historical is separate from historical_data
        - Data integrity is maintained throughout processing
        - Immutability principle is enforced
        """
        # Setup mock factory
        mock_factory_instance = Mock()
        mock_factory_instance.create_handlers.return_value = mock_handlers
        mock_factory.return_value = mock_factory_instance

        # Store original data for comparison
        original_copy = sample_historical_data.copy()

        # Initialize manager
        manager = IndicatorManager(sample_historical_data, sample_config, is_bulk=True)

        # Verify original data is preserved
        pd.testing.assert_frame_equal(manager.original_historical, original_copy)

        # Verify input data wasn't modified
        pd.testing.assert_frame_equal(sample_historical_data, original_copy)

        # Verify original_historical is separate from historical_data
        assert not manager.original_historical.equals(manager.historical_data)

    @patch('indicators.indicator_manager.IndicatorFactory')
    def test_empty_config(self, mock_factory, sample_historical_data):
        """
        Test behavior with empty configuration.

        Expected Behavior:
        - No handlers are created
        - historical_data equals original_historical (no processing)
        - No indicator columns are added
        - Manager initializes successfully
        - Gracefully handles edge case of no indicators
        """
        # Setup mock factory with empty handlers
        mock_factory_instance = Mock()
        mock_factory_instance.create_handlers.return_value = {}
        mock_factory.return_value = mock_factory_instance

        # Initialize manager with empty config
        manager = IndicatorManager(sample_historical_data, {}, is_bulk=True)

        # Verify no handlers
        assert len(manager.handlers) == 0

        # Verify historical data equals original (no indicators added)
        pd.testing.assert_frame_equal(manager.historical_data, sample_historical_data)

    @patch('indicators.indicator_manager.IndicatorFactory')
    def test_single_indicator_config(self, mock_factory, sample_historical_data, mock_handlers):
        """
        Test with single indicator configuration.

        Expected Behavior:
        - Only one handler is created and stored
        - Only specified indicator column is added
        - Other indicator columns are not present
        - Demonstrates selective indicator processing
        - Validates minimal configuration handling
        """
        # Setup mock factory with single handler
        single_handler = {'sma_20': mock_handlers['sma_20']}
        mock_factory_instance = Mock()
        mock_factory_instance.create_handlers.return_value = single_handler
        mock_factory.return_value = mock_factory_instance

        # Initialize manager
        manager = IndicatorManager(sample_historical_data, {'sma_20': {'type': 'sma', 'period': 20}}, is_bulk=True)

        # Verify only one handler
        assert len(manager.handlers) == 1
        assert 'sma_20' in manager.handlers

        # Verify only SMA column added
        assert 'sma_20' in manager.historical_data.columns
        assert 'ema_12' not in manager.historical_data.columns
        assert 'macd_default' not in manager.historical_data.columns

    @patch('indicators.indicator_manager.IndicatorFactory')
    def test_bulk_vs_warmup_consistency(self, mock_factory, sample_historical_data, sample_config, mock_handlers):
        """
        Test that bulk and warmup modes produce consistent results.

        Expected Behavior:
        - Both modes create same column structure
        - Both modes process same number of rows
        - Column names are identical between modes
        - Data structure consistency regardless of processing method
        - Validates that both approaches are equivalent in output format
        """
        # Setup mock factory
        mock_factory_instance = Mock()
        mock_factory_instance.create_handlers.return_value = mock_handlers
        mock_factory.return_value = mock_factory_instance

        # Create two managers with different modes
        manager_bulk = IndicatorManager(sample_historical_data, sample_config, is_bulk=True)

        # Reset mocks for second manager
        for key, handler in mock_handlers.items():
            handler.reset_mock()
            # Re-setup the side effects for each handler by key
            if key == 'sma_20':
                handler.compute.side_effect = lambda row: self._add_to_row(row, 'sma_20', 102.5)
                handler.bulk_compute.side_effect = lambda df: self._add_to_df(df, 'sma_20',
                                                                              [102.1, 102.2, 102.3, 102.4, 102.5])
            elif key == 'ema_12':
                handler.compute.side_effect = lambda row: self._add_to_row(row, 'ema_12', 103.2)
                handler.bulk_compute.side_effect = lambda df: self._add_to_df(df, 'ema_12',
                                                                              [103.1, 103.2, 103.3, 103.4, 103.5])
            elif key == 'macd_default':
                handler.compute.side_effect = lambda row: self._add_multiple_to_row(
                    row, {'macd_default': 1.5, 'macd_default_signal': 1.2, 'macd_default_hist': 0.3}
                )
                handler.bulk_compute.side_effect = lambda df: self._add_multiple_to_df(
                    df, {
                        'macd_default': [1.1, 1.2, 1.3, 1.4, 1.5],
                        'macd_default_signal': [1.0, 1.1, 1.2, 1.3, 1.4],
                        'macd_default_hist': [0.1, 0.1, 0.1, 0.1, 0.1]
                    }
                )

        manager_warmup = IndicatorManager(sample_historical_data, sample_config, is_bulk=False)

        # Compare results (should be similar structure, though values might differ due to mocking)
        bulk_columns = set(manager_bulk.historical_data.columns)
        warmup_columns = set(manager_warmup.historical_data.columns)

        # Both should have the same columns
        assert bulk_columns == warmup_columns

        # Both should have same number of rows
        assert len(manager_bulk.historical_data) == len(manager_warmup.historical_data)

    @patch('indicators.indicator_manager.IndicatorFactory')
    def test_error_handling_in_factory(self, mock_factory, sample_historical_data, sample_config):
        """
        Test error handling when IndicatorFactory fails.

        Expected Behavior:
        - Exception is raised immediately (crash-hard philosophy)
        - No graceful fallback or error recovery
        - Application terminates with clear error message
        - Validates fail-fast approach to initialization errors
        - Ensures data quality by preventing partial initialization
        """
        # Setup mock factory to raise exception
        mock_factory.side_effect = Exception("Factory initialization failed")

        # Should raise the exception (no graceful handling)
        with pytest.raises(Exception, match="Factory initialization failed"):
            IndicatorManager(sample_historical_data, sample_config, is_bulk=True)

    @patch('indicators.indicator_manager.IndicatorFactory')
    def test_handler_computation_errors(self, mock_factory, sample_historical_data, sample_config):
        """
        Test behavior when handlers raise errors during computation.

        Expected Behavior:
        - Exception is raised immediately (crash-hard philosophy)
        - No graceful fallback or NaN padding
        - Application terminates with clear error message
        - Validates fail-fast approach to computation errors
        - Ensures data quality by preventing partial results
        """
        # Setup mock factory with failing handler
        failing_handler = Mock()
        failing_handler.bulk_compute.side_effect = Exception("Handler computation failed")

        mock_factory_instance = Mock()
        mock_factory_instance.create_handlers.return_value = {'failing_indicator': failing_handler}
        mock_factory.return_value = mock_factory_instance

        # Should raise the exception (no graceful handling based on your crash-hard approach)
        with pytest.raises(Exception, match="Handler computation failed"):
            IndicatorManager(sample_historical_data, sample_config, is_bulk=True)

    @patch('indicators.indicator_manager.IndicatorFactory')
    def test_compute_indicators_preserves_input(self, mock_factory, sample_historical_data, sample_config, mock_handlers):
        """
        Test that compute_indicators doesn't modify the input row.

        Expected Behavior:
        - Input row remains completely unchanged
        - Result contains all original row data plus indicators
        - Immutability principle is enforced for method parameters
        - Safe for use in streaming/live processing scenarios
        - Validates data integrity in single-row processing
        """
        # Setup mock factory
        mock_factory_instance = Mock()
        mock_factory_instance.create_handlers.return_value = mock_handlers
        mock_factory.return_value = mock_factory_instance

        # Initialize manager
        manager = IndicatorManager(sample_historical_data, sample_config, is_bulk=True)

        # Create test row
        test_row = pd.Series({
            'open': 108.0,
            'high': 112.0,
            'low': 106.0,
            'close': 110.0,
            'volume': 1500,
            'tick_volume': 2000
        })
        original_row = test_row.copy()

        # Compute indicators
        result = manager.compute_indicators(test_row)

        # Verify input row wasn't modified
        pd.testing.assert_series_equal(test_row, original_row)

        # Verify result is different (has indicator columns)
        assert len(result) > len(test_row)

