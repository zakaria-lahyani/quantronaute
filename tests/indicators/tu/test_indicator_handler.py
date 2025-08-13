"""
IndicatorHandler Test Suite
==========================

This test suite validates the IndicatorHandler class, which serves as a wrapper around
individual technical indicator implementations, providing a unified interface for both
single-row and bulk processing of market data.

Expected Behavior Overview:
--------------------------

1. INITIALIZATION:
   - Extracts base indicator name from full name (e.g., 'macd_1h' -> 'macd')
   - Loads configuration for supported indicators
   - Stores reference to underlying indicator implementation
   - Determines if indicator is supported based on configuration

2. INDICATOR PROCESSING MODES:
   - Single Row (compute): Processes one market data row at a time
   - Bulk Processing (bulk_compute): Processes entire DataFrame vectorized
   - Input Handling: Different indicators require different input patterns
   - Output Handling: Supports single and multiple output indicators

3. INPUT PATTERNS:
   - Close Only: Most indicators use only close price (SMA, EMA, RSI)
   - Multi-Input: Some indicators need high/low/close (ATR, Bollinger Bands)
   - Full Row: Complex indicators need entire row (URSI)
   - Bulk Inputs: Vectorized versions for DataFrame processing

4. OUTPUT PATTERNS:
   - Single Output: One column added (SMA -> 'sma_1h')
   - Multiple Outputs: Multiple columns with suffixes (MACD -> 'macd_1h', 'macd_1h_signal', 'macd_1h_hist')
   - Output Padding: Missing outputs filled with NaN
   - Column Naming: Consistent naming convention with base name + suffixes

5. ERROR HANDLING:
   - Crash-Hard Philosophy: Errors propagate immediately, no graceful fallbacks
   - Missing Fields: KeyError raised for missing required data fields
   - Indicator Failures: Underlying indicator errors bubble up
   - Unsupported Indicators: Return data unchanged (no processing)

6. DATA INTEGRITY:
   - Immutability: Input data never modified, always work on copies
   - Preservation: Original row/DataFrame structure maintained
   - Consistency: Same results regardless of processing mode (single vs bulk)

7. CONFIGURATION SYSTEM:
   - Dynamic Configuration: New indicators can be added at runtime
   - Input Mapping: Defines how to extract inputs from market data
   - Output Mapping: Defines column names for indicator outputs
   - Validation: Checks if indicator is supported before processing
"""

import pytest
import pandas as pd
from unittest.mock import Mock
from app.indicators.indicator_handler import IndicatorHandler


class TestIndicatorHandler:
    """
    Comprehensive test suite for the refactored IndicatorHandler.

    Tests cover all aspects of indicator processing including initialization,
    single-row and bulk processing, error handling, and data integrity.
    """

    @pytest.fixture
    def sample_row(self):
        """
        Sample market data row for testing single-row processing.

        Expected Behavior:
        - Contains all standard OHLCV fields required by indicators
        - Includes tick_volume for indicators that need it
        - Represents a single time period of market data
        - Used to test compute() method functionality

        Returns:
            pd.Series: Single row of market data with all required fields
        """
        return pd.Series({
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 102.0,
            'volume': 1000.0,
            'tick_volume': 1500.0
        })

    @pytest.fixture
    def sample_df(self):
        """
        Sample market data DataFrame for testing bulk processing.

        Expected Behavior:
        - Contains multiple rows of OHLCV data
        - All required fields present for indicator computation
        - Represents time series of market data
        - Used to test bulk_compute() method functionality

        Returns:
            pd.DataFrame: Multiple rows of market data for bulk processing
        """
        return pd.DataFrame({
            'open': [100.0, 102.0, 101.0, 103.0],
            'high': [105.0, 107.0, 106.0, 108.0],
            'low': [95.0, 97.0, 96.0, 98.0],
            'close': [102.0, 104.0, 103.0, 105.0],
            'volume': [1000, 1100, 1200, 1300],
            'tick_volume': [1500, 1600, 1700, 1800]
        })

    def test_initialization(self):
        """
        Test proper initialization of IndicatorHandler.

        Expected Behavior:
        - Extracts base name from full indicator name (e.g., 'macd_1h' -> 'macd')
        - Stores reference to underlying indicator implementation
        - Loads configuration for the indicator type
        - Correctly identifies supported indicators
        - Sets up all necessary attributes for processing
        """
        mock_indicator = Mock()
        handler = IndicatorHandler('macd_1h', mock_indicator)

        assert handler.name == 'macd_1h'
        assert handler.base_name == 'macd'
        assert handler.indicator == mock_indicator
        assert handler.config is not None
        assert handler.is_supported()

    def test_initialization_unsupported_indicator(self):
        """
        Test initialization with unsupported indicator.

        Expected Behavior:
        - Accepts any indicator name during initialization
        - Extracts base name correctly even for unknown indicators
        - Sets config to None for unsupported indicators
        - is_supported() returns False for unknown indicators
        - Handler can still be created but won't process data
        """
        mock_indicator = Mock()
        handler = IndicatorHandler('unknown_1h', mock_indicator)

        assert handler.name == 'unknown_1h'
        assert handler.base_name == 'unknown'
        assert handler.config is None
        assert not handler.is_supported()

    def test_single_output_indicator_compute(self, sample_row):
        """
        Test compute with single output indicator (SMA).

        Expected Behavior:
        - Calls indicator.update() with close price only
        - Receives single numeric value from indicator
        - Adds one new column to the row with indicator name
        - Preserves all original row data
        - Returns modified copy of input row
        - Column name matches indicator name exactly
        """
        mock_indicator = Mock()
        mock_indicator.update.return_value = 15.7

        handler = IndicatorHandler('sma_1h', mock_indicator)
        result = handler.compute(sample_row)

        # Verify indicator was called correctly
        mock_indicator.update.assert_called_once_with(102.0)

        # Verify output column was added
        assert 'sma_1h' in result
        assert result['sma_1h'] == 15.7

    def test_multiple_output_indicator_compute(self, sample_row):
        """
        Test compute with multiple output indicator (MACD).

        Expected Behavior:
        - Calls indicator.update() with close price
        - Receives tuple of multiple values from indicator
        - Adds multiple columns with appropriate suffixes
        - MACD produces: main line, signal line, histogram
        - Column names: 'macd_1h', 'macd_1h_signal', 'macd_1h_hist'
        - All original row data preserved
        """
        mock_indicator = Mock()
        mock_indicator.update.return_value = (12.5, 11.2, 1.3)

        handler = IndicatorHandler('macd_1h', mock_indicator)
        result = handler.compute(sample_row)

        # Verify indicator was called correctly
        mock_indicator.update.assert_called_once_with(102.0)

        # Verify all output columns were added
        assert 'macd_1h' in result
        assert 'macd_1h_signal' in result
        assert 'macd_1h_hist' in result
        assert result['macd_1h'] == 12.5
        assert result['macd_1h_signal'] == 11.2
        assert result['macd_1h_hist'] == 1.3

    def test_ursi_indicator_compute(self, sample_row):
        """
        Test compute with URSI indicator (passes entire row).

        Expected Behavior:
        - URSI is a special indicator that needs the entire market data row
        - Calls indicator.update() with complete pd.Series (not just close)
        - Receives tuple with URSI value and signal
        - Adds two columns: 'ursi_1h' and 'signal_ursi_1h'
        - Demonstrates full-row input pattern for complex indicators
        """
        mock_indicator = Mock()
        mock_indicator.update.return_value = (50.5, 45.2)

        handler = IndicatorHandler('ursi_1h', mock_indicator)
        result = handler.compute(sample_row)

        # Verify indicator was called with entire row
        mock_indicator.update.assert_called_once()
        call_args = mock_indicator.update.call_args[0]
        assert isinstance(call_args[0], pd.Series)

        # Verify output columns
        assert 'ursi_1h' in result
        assert 'signal_ursi_1h' in result
        assert result['ursi_1h'] == 50.5
        assert result['signal_ursi_1h'] == 45.2

    def test_multi_input_indicator_compute(self, sample_row):
        """
        Test compute with multi-input indicator (ATR).

        Expected Behavior:
        - ATR requires high, low, and close prices
        - Calls indicator.update() with three separate arguments
        - Input order: high, low, close (as defined in configuration)
        - Receives single ATR value
        - Adds one column: 'atr_1h'
        - Demonstrates multi-field input extraction pattern
        """
        mock_indicator = Mock()
        mock_indicator.update.return_value = 8.5

        handler = IndicatorHandler('atr_1h', mock_indicator)
        result = handler.compute(sample_row)

        # Verify indicator was called with correct inputs
        mock_indicator.update.assert_called_once_with(105.0, 95.0, 102.0)

        # Verify output
        assert 'atr_1h' in result
        assert result['atr_1h'] == 8.5

    def test_compute_with_fewer_outputs_than_expected(self, sample_row):
        """
        Test compute when indicator returns fewer outputs than configured.

        Expected Behavior:
        - MACD is configured for 3 outputs but indicator returns only 2
        - Missing outputs are padded with NaN values
        - All configured columns are still created
        - Prevents crashes when indicators return partial results
        - Maintains consistent column structure across all rows
        """
        mock_indicator = Mock()
        mock_indicator.update.return_value = (12.5, 11.2)  # Only 2 outputs instead of 3

        handler = IndicatorHandler('macd_1h', mock_indicator)
        result = handler.compute(sample_row)

        # Should pad with None
        assert 'macd_1h' in result
        assert 'macd_1h_signal' in result
        assert 'macd_1h_hist' in result
        assert result['macd_1h'] == 12.5
        assert result['macd_1h_signal'] == 11.2
        assert pd.isna(result['macd_1h_hist'])


    def test_compute_raises_on_indicator_error(self, sample_row):
        """
        Test that compute raises if indicator.update fails.

        Expected Behavior:
        - Follows crash-hard philosophy for error handling
        - If underlying indicator raises exception, it propagates immediately
        - No graceful fallback or error recovery
        - Ensures data quality by preventing partial/incorrect results
        - Application terminates with clear error from indicator
        """
        mock_indicator = Mock()
        mock_indicator.update.side_effect = Exception("Indicator failed")

        handler = IndicatorHandler('macd_1h', mock_indicator)

        with pytest.raises(Exception, match="Indicator failed"):
            handler.compute(sample_row)

    def test_bulk_compute_single_output(self, sample_df):
        """
        Test bulk compute with single output indicator.

        Expected Behavior:
        - Calls indicator.batch_update() with close price Series
        - Receives pd.Series with values for all rows
        - Adds single column to DataFrame with indicator name
        - Vectorized processing for better performance
        - All original DataFrame columns preserved
        - Output Series length matches input DataFrame length
        """
        mock_indicator = Mock()
        mock_series = pd.Series([15.1, 15.2, 15.3, 15.4])
        mock_indicator.batch_update.return_value = mock_series

        handler = IndicatorHandler('sma_1h', mock_indicator)
        result = handler.bulk_compute(sample_df)

        # Verify indicator was called correctly
        mock_indicator.batch_update.assert_called_once()
        call_args = mock_indicator.batch_update.call_args[0]
        pd.testing.assert_series_equal(call_args[0], sample_df['close'], check_names=False)

        # Verify output column
        assert 'sma_1h' in result.columns
        pd.testing.assert_series_equal(result['sma_1h'], mock_series, check_names=False)

    def test_bulk_compute_multiple_outputs(self, sample_df):
        """
        Test bulk compute with multiple output indicator.

        Expected Behavior:
        - Calls indicator.batch_update() with close price Series
        - Receives tuple of pd.Series for each output
        - Adds multiple columns with appropriate suffixes
        - All Series have same length as input DataFrame
        - MACD produces: main, signal, histogram Series
        - Column names follow naming convention
        """
        mock_indicator = Mock()
        macd_series = pd.Series([12.1, 12.2, 12.3, 12.4])
        signal_series = pd.Series([11.1, 11.2, 11.3, 11.4])
        hist_series = pd.Series([1.0, 1.0, 1.0, 1.0])
        mock_indicator.batch_update.return_value = (macd_series, signal_series, hist_series)

        handler = IndicatorHandler('macd_1h', mock_indicator)
        result = handler.bulk_compute(sample_df)

        # Verify all output columns
        assert 'macd_1h' in result.columns
        assert 'macd_1h_signal' in result.columns
        assert 'macd_1h_hist' in result.columns
        pd.testing.assert_series_equal(result['macd_1h'], macd_series, check_names=False)
        pd.testing.assert_series_equal(result['macd_1h_signal'], signal_series, check_names=False)
        pd.testing.assert_series_equal(result['macd_1h_hist'], hist_series, check_names=False)

    def test_bulk_compute_ursi(self, sample_df):
        """
        Test bulk compute with URSI indicator.

        Expected Behavior:
        - URSI requires entire DataFrame for bulk processing
        - Calls indicator.batch_update() with complete DataFrame
        - Receives tuple of Series for URSI and signal values
        - Adds two columns: 'ursi_1h' and 'signal_ursi_1h'
        - Demonstrates full-DataFrame input pattern for complex indicators
        """
        mock_indicator = Mock()
        ursi_series = pd.Series([50.1, 50.2, 50.3, 50.4])
        signal_series = pd.Series([45.1, 45.2, 45.3, 45.4])
        mock_indicator.batch_update.return_value = (ursi_series, signal_series)

        handler = IndicatorHandler('ursi_1h', mock_indicator)
        result = handler.bulk_compute(sample_df)

        # Verify indicator was called with entire DataFrame
        mock_indicator.batch_update.assert_called_once()
        call_args = mock_indicator.batch_update.call_args[0]
        assert isinstance(call_args[0], pd.DataFrame)

        # Verify outputs
        assert 'ursi_1h' in result.columns
        assert 'signal_ursi_1h' in result.columns

    def test_bulk_compute_error_handling(self, sample_df):
        """
        Test graceful error handling during bulk compute.

        Expected Behavior:
        - Follows crash-hard philosophy for bulk processing errors
        - If indicator.batch_update() fails, exception propagates
        - No partial results or graceful degradation
        - Ensures data integrity by preventing incomplete processing
        - Application terminates with clear error from indicator
        """
        mock_indicator = Mock()
        mock_indicator.batch_update.side_effect = Exception("Batch failed")

        handler = IndicatorHandler('macd_1h', mock_indicator)

        with pytest.raises(Exception, match="Batch failed"):
            handler.bulk_compute(sample_df)


    def test_unsupported_indicator_compute(self, sample_row):
        """
        Test compute with unsupported indicator.

        Expected Behavior:
        - Unsupported indicators are handled gracefully
        - No processing is attempted on the data
        - Original row is returned completely unchanged
        - Underlying indicator is never called
        - Allows system to continue with supported indicators
        - No columns are added to the row
        """
        mock_indicator = Mock()
        handler = IndicatorHandler('unknown_1h', mock_indicator)

        result = handler.compute(sample_row)

        # Should return original row unchanged
        pd.testing.assert_series_equal(result, sample_row)
        mock_indicator.update.assert_not_called()

    def test_unsupported_indicator_bulk_compute(self, sample_df):
        """
        Test bulk compute with unsupported indicator.

        Expected Behavior:
        - Unsupported indicators are handled gracefully in bulk mode
        - No processing is attempted on the DataFrame
        - Original DataFrame is returned completely unchanged
        - Underlying indicator is never called
        - Allows system to continue with supported indicators
        - No columns are added to the DataFrame
        """
        mock_indicator = Mock()
        handler = IndicatorHandler('unknown_1h', mock_indicator)

        result = handler.bulk_compute(sample_df)

        # Should return original DataFrame unchanged
        pd.testing.assert_frame_equal(result, sample_df)
        mock_indicator.batch_update.assert_not_called()

    def test_get_output_columns(self):
        """
        Test getting output column names.

        Expected Behavior:
        - Returns list of column names that will be added by indicator
        - MACD returns 3 columns with appropriate suffixes
        - SMA returns 1 column with indicator name
        - Unsupported indicators return empty list
        - Column names follow consistent naming convention
        - Used for pre-allocation and validation
        """
        mock_indicator = Mock()

        # Test MACD (3 outputs)
        handler = IndicatorHandler('macd_1h', mock_indicator)
        outputs = handler.get_output_columns()
        expected = ['macd_1h', 'macd_1h_signal', 'macd_1h_hist']
        assert outputs == expected

        # Test SMA (1 output)
        handler = IndicatorHandler('sma_1h', mock_indicator)
        outputs = handler.get_output_columns()
        expected = ['sma_1h']
        assert outputs == expected

        # Test unsupported indicator
        handler = IndicatorHandler('unknown_1h', mock_indicator)
        outputs = handler.get_output_columns()
        assert outputs == []

    def test_add_indicator_config(self):
        """
        Test adding new indicator configuration.

        Expected Behavior:
        - New indicator types can be added dynamically at runtime
        - Configuration includes input extraction functions
        - Configuration includes output column naming functions
        - Added indicators become immediately available
        - System is extensible without code changes
        - Custom indicators follow same patterns as built-in ones
        """
        # Add a custom indicator
        custom_config = {
            'inputs': lambda row: (row['close'], row['volume']),
            'bulk_inputs': lambda df: (df['close'], df['volume']),
            'outputs': lambda name: [f'{name}_value', f'{name}_signal']
        }

        IndicatorHandler.add_indicator_config('custom', custom_config)

        # Test that it's now supported
        mock_indicator = Mock()
        handler = IndicatorHandler('custom_1h', mock_indicator)
        assert handler.is_supported()
        assert handler.get_output_columns() == ['custom_1h_value', 'custom_1h_signal']

    def test_get_supported_indicators(self):
        """
        Test getting list of supported indicators.

        Expected Behavior:
        - Returns complete list of all configured indicator types
        - Includes all built-in indicators
        - Includes any dynamically added indicators
        - Used for validation and system introspection
        - List contains base names (without timeframe suffixes)
        """
        supported = IndicatorHandler.get_supported_indicators()

        # Should include all configured indicators
        expected_indicators = [
            'ursi', 'bb', 'atr', 'rsi', 'sar', 'stochrsi', 'supertrend',
            'macd', 'ichimoku', 'adx', 'obv', 'aroon', 'keltner', 'ema', 'sma'
        ]

        for indicator in expected_indicators:
            assert indicator in supported

    def test_complex_indicator_bollinger_bands(self, sample_row):
        """
        Test complex indicator with 4 outputs (Bollinger Bands).

        Expected Behavior:
        - Bollinger Bands produces 4 distinct outputs
        - Upper band, middle band (SMA), lower band, %B indicator
        - Column names: 'bb_1h_upper', 'bb_1h_middle', 'bb_1h_lower', 'bb_1h_percent_b'
        - All values are numeric and represent band levels
        - Demonstrates handling of indicators with many outputs
        """
        mock_indicator = Mock()
        mock_indicator.update.return_value = (110.0, 102.0, 94.0, 0.8)

        handler = IndicatorHandler('bb_1h', mock_indicator)
        result = handler.compute(sample_row)

        # Verify all BB outputs
        assert 'bb_1h_upper' in result
        assert 'bb_1h_middle' in result
        assert 'bb_1h_lower' in result
        assert 'bb_1h_percent_b' in result
        assert result['bb_1h_upper'] == 110.0
        assert result['bb_1h_middle'] == 102.0
        assert result['bb_1h_lower'] == 94.0
        assert result['bb_1h_percent_b'] == 0.8

    def test_ichimoku_indicator_six_outputs(self, sample_row):
        """
        Test Ichimoku indicator with 6 outputs.

        Expected Behavior:
        - Ichimoku is the most complex indicator with 6 outputs
        - Tenkan-sen, Kijun-sen, Senkou Span A, Senkou Span B, Chikou Span, Cloud signal
        - Column names follow pattern: 'ichimoku_1h_tenkan', 'ichimoku_1h_kijun', etc.
        - Demonstrates maximum complexity handling
        - All outputs are properly mapped to columns
        """
        mock_indicator = Mock()
        mock_indicator.update.return_value = (103.5, 102.0, 101.5, 100.5, 102.5, 1)

        handler = IndicatorHandler('ichimoku_1h', mock_indicator)
        result = handler.compute(sample_row)

        # Verify all Ichimoku outputs
        expected_cols = [
            'ichimoku_1h_tenkan', 'ichimoku_1h_kijun', 'ichimoku_1h_senkou_a',
            'ichimoku_1h_senkou_b', 'ichimoku_1h_chikou', 'ichimoku_1h_cloud'
        ]

        for col in expected_cols:
            assert col in result

    def test_missing_fields_crashes_app(self):
        """
        Test that missing fields crash the app with KeyError.

        Expected Behavior:
        - Follows crash-hard philosophy for data quality
        - Missing required fields cause immediate KeyError
        - ATR requires 'high' and 'low' fields that are missing
        - No graceful fallback or NaN substitution
        - Application terminates rather than producing incorrect results
        - Ensures data integrity by preventing partial processing
        """
        incomplete_row = pd.Series({'close': 100.0})  # Missing high, low for ATR

        mock_indicator = Mock()
        handler = IndicatorHandler('atr_1h', mock_indicator)

        # Should crash with KeyError
        with pytest.raises(KeyError, match="'high'"):
            handler.compute(incomplete_row)


    def test_data_integrity_original_unchanged(self, sample_row, sample_df):
        """
        Test that original data is not modified.

        Expected Behavior:
        - Input row and DataFrame are never modified during processing
        - All operations work on copies of the input data
        - Original data remains exactly as provided
        - Immutability principle is strictly enforced
        - Safe for use in streaming applications where data is reused
        - Prevents side effects and data corruption
        """
        mock_indicator = Mock()
        mock_indicator.update.return_value = 15.7
        mock_indicator.batch_update.return_value = pd.Series([15.1, 15.2, 15.3, 15.4])

        handler = IndicatorHandler('sma_1h', mock_indicator)

        # Store original data
        original_row = sample_row.copy()
        original_df = sample_df.copy()

        # Compute indicators
        handler.compute(sample_row)
        handler.bulk_compute(sample_df)

        # Verify originals are unchanged
        pd.testing.assert_series_equal(sample_row, original_row, check_names=False)
        pd.testing.assert_frame_equal(sample_df, original_df, check_names=False)


