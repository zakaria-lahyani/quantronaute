import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from app.indicators.indicator_handler import IndicatorHandler


class TestIndicatorHandler:
    """Test suite for IndicatorHandler class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock indicator instance
        self.mock_indicator = Mock()
        self.mock_indicator.update.return_value = 0.5
        self.mock_indicator.batch_update.return_value = [0.1, 0.2, 0.3]
        
        # Sample data
        self.sample_row = pd.Series({
            'high': 105.0,
            'low': 95.0,
            'close': 100.0,
            'volume': 1000
        })
        
        self.sample_df = pd.DataFrame({
            'high': [105.0, 107.0, 103.0],
            'low': [95.0, 97.0, 93.0],
            'close': [100.0, 102.0, 98.0],
            'volume': [1000, 1500, 1200]
        })

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_handler_initialization(self, mock_config):
        """Test handler initializes correctly."""
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name]
        }
        
        handler = IndicatorHandler('rsi_14', self.mock_indicator)
        
        assert handler.name == 'rsi_14'
        assert handler.base_name == 'rsi'
        assert handler.indicator == self.mock_indicator
        assert handler.config is not None

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_handler_initialization_complex_name(self, mock_config):
        """Test handler handles complex names correctly."""
        mock_config.get.return_value = {}
        
        handler = IndicatorHandler('macd_1h_custom', self.mock_indicator)
        
        assert handler.name == 'macd_1h_custom'
        assert handler.base_name == 'macd'

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_handler_initialization_no_config(self, mock_config):
        """Test handler handles missing configuration."""
        mock_config.get.return_value = None
        
        handler = IndicatorHandler('unknown_indicator', self.mock_indicator)
        
        assert handler.name == 'unknown_indicator'
        assert handler.base_name == 'unknown'
        assert handler.config is None

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_compute_single_row_success(self, mock_config):
        """Test successful single row computation."""
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name]
        }
        
        handler = IndicatorHandler('rsi_14', self.mock_indicator)
        result = handler.compute(self.sample_row)
        
        # Verify indicator was called correctly
        self.mock_indicator.update.assert_called_once_with(100.0)
        
        # Verify result
        assert isinstance(result, pd.Series)
        assert result['close'] == 100.0  # Original data preserved
        assert result['rsi_14'] == 0.5    # Indicator result added

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_compute_single_row_multiple_outputs(self, mock_config):
        """Test single row computation with multiple outputs."""
        self.mock_indicator.update.return_value = (0.5, 0.3)
        
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name, f'{name}_signal']
        }
        
        handler = IndicatorHandler('rsi_14', self.mock_indicator)
        result = handler.compute(self.sample_row)
        
        assert result['rsi_14'] == 0.5
        assert result['rsi_14_signal'] == 0.3

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_compute_single_row_no_config(self, mock_config):
        """Test single row computation with no configuration."""
        mock_config.get.return_value = None
        
        handler = IndicatorHandler('unknown', self.mock_indicator)
        result = handler.compute(self.sample_row)
        
        # Should return original row unchanged
        assert result.equals(self.sample_row)
        self.mock_indicator.update.assert_not_called()

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_bulk_compute_success(self, mock_config):
        """Test successful bulk computation."""
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name]
        }
        
        handler = IndicatorHandler('sma_20', self.mock_indicator)
        result = handler.bulk_compute(self.sample_df)
        
        # Verify indicator was called correctly
        expected_close = self.sample_df['close']
        self.mock_indicator.batch_update.assert_called_once()
        call_args = self.mock_indicator.batch_update.call_args[0]
        assert call_args[0].equals(expected_close)
        
        # Verify result
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(self.sample_df)
        assert 'sma_20' in result.columns
        assert result['sma_20'].tolist() == [0.1, 0.2, 0.3]

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_bulk_compute_multiple_inputs(self, mock_config):
        """Test bulk computation with multiple input columns."""
        mock_config.get.return_value = {
            'inputs': lambda row: (row['high'], row['low'], row['close']),
            'bulk_inputs': lambda df: (df['high'], df['low'], df['close']),
            'outputs': lambda name: [name]
        }
        
        handler = IndicatorHandler('atr_14', self.mock_indicator)
        result = handler.bulk_compute(self.sample_df)
        
        # Verify indicator was called with multiple inputs
        call_args = self.mock_indicator.batch_update.call_args[0]
        assert len(call_args) == 3  # high, low, close
        assert call_args[0].equals(self.sample_df['high'])
        assert call_args[1].equals(self.sample_df['low'])
        assert call_args[2].equals(self.sample_df['close'])

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_bulk_compute_no_config(self, mock_config):
        """Test bulk computation with no configuration."""
        mock_config.get.return_value = None
        
        handler = IndicatorHandler('unknown', self.mock_indicator)
        result = handler.bulk_compute(self.sample_df)
        
        # Should return original DataFrame unchanged
        assert result.equals(self.sample_df)
        self.mock_indicator.batch_update.assert_not_called()

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_pad_result_shorter_than_expected(self, mock_config):
        """Test result padding when indicator returns fewer outputs than expected."""
        self.mock_indicator.update.return_value = (0.5,)  # Only one output
        
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name, f'{name}_signal', f'{name}_trend']  # Three outputs expected
        }
        
        handler = IndicatorHandler('test_indicator', self.mock_indicator)
        result = handler.compute(self.sample_row)
        
        assert result['test_indicator'] == 0.5
        assert pd.isna(result['test_indicator_signal'])
        assert pd.isna(result['test_indicator_trend'])

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_single_output_as_non_tuple(self, mock_config):
        """Test handling of single output that's not returned as tuple."""
        self.mock_indicator.update.return_value = 0.75  # Single value, not tuple
        
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name]
        }
        
        handler = IndicatorHandler('test_indicator', self.mock_indicator)
        result = handler.compute(self.sample_row)
        
        assert result['test_indicator'] == 0.75

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_compute_preserves_original_data(self, mock_config):
        """Test that computation preserves original data."""
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name]
        }
        
        handler = IndicatorHandler('test_indicator', self.mock_indicator)
        original_row = self.sample_row.copy()
        result = handler.compute(self.sample_row)
        
        # Original row should be unchanged
        assert self.sample_row.equals(original_row)
        
        # Result should have original data plus indicator
        for key in original_row.index:
            assert result[key] == original_row[key]

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_compute_with_missing_input_columns(self, mock_config):
        """Test computation with missing required input columns."""
        mock_config.get.return_value = {
            'inputs': lambda row: (row['missing_column'],),
            'bulk_inputs': lambda df: (df['missing_column'],),
            'outputs': lambda name: [name]
        }
        
        handler = IndicatorHandler('test_indicator', self.mock_indicator)
        
        # Should raise KeyError for missing column
        with pytest.raises(KeyError):
            handler.compute(self.sample_row)

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_compute_with_indicator_exception(self, mock_config):
        """Test handling of indicator computation exceptions."""
        self.mock_indicator.update.side_effect = ValueError("Invalid input")
        
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name]
        }
        
        handler = IndicatorHandler('test_indicator', self.mock_indicator)
        
        # Should propagate the exception
        with pytest.raises(ValueError, match="Invalid input"):
            handler.compute(self.sample_row)

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_get_output_columns(self, mock_config):
        """Test getting output column names."""
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name, f'{name}_signal', f'{name}_histogram']
        }
        
        handler = IndicatorHandler('macd_12_26', self.mock_indicator)
        columns = handler.get_output_columns()
        
        expected = ['macd_12_26', 'macd_12_26_signal', 'macd_12_26_histogram']
        assert columns == expected

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_get_output_columns_no_config(self, mock_config):
        """Test getting output columns with no configuration."""
        mock_config.get.return_value = None
        
        handler = IndicatorHandler('unknown', self.mock_indicator)
        columns = handler.get_output_columns()
        
        assert columns == []

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_is_supported_true(self, mock_config):
        """Test is_supported returns True when configuration exists."""
        mock_config.get.return_value = {'some': 'config'}
        
        handler = IndicatorHandler('rsi_14', self.mock_indicator)
        
        assert handler.is_supported() is True

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_is_supported_false(self, mock_config):
        """Test is_supported returns False when no configuration."""
        mock_config.get.return_value = None
        
        handler = IndicatorHandler('unknown', self.mock_indicator)
        
        assert handler.is_supported() is False

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_add_indicator_config_class_method(self, mock_config):
        """Test adding new indicator configuration."""
        new_config = {
            'inputs': lambda row: (row['volume'],),
            'bulk_inputs': lambda df: (df['volume'],),
            'outputs': lambda name: [name]
        }
        
        IndicatorHandler.add_indicator_config('custom_indicator', new_config)
        
        # Verify the configuration was added
        mock_config.__setitem__.assert_called_once_with('custom_indicator', new_config)

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_get_supported_indicators_class_method(self, mock_config):
        """Test getting list of supported indicators."""
        mock_config.keys.return_value = ['rsi', 'sma', 'macd', 'bb']
        
        supported = IndicatorHandler.get_supported_indicators()
        
        assert supported == ['rsi', 'sma', 'macd', 'bb']

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_apply_indicator_with_complex_outputs(self, mock_config):
        """Test _apply_indicator with complex output structure."""
        # Mock indicator that returns multiple outputs
        self.mock_indicator.update.return_value = (10.5, 20.3, 30.7, 40.1)
        
        mock_config.get.return_value = {
            'inputs': lambda row: (row['high'], row['low'], row['close']),
            'bulk_inputs': lambda df: (df['high'], df['low'], df['close']),
            'outputs': lambda name: [f'{name}_upper', f'{name}_middle', f'{name}_lower', f'{name}_width']
        }
        
        handler = IndicatorHandler('bb_20', self.mock_indicator)
        result = handler.compute(self.sample_row)
        
        assert result['bb_20_upper'] == 10.5
        assert result['bb_20_middle'] == 20.3
        assert result['bb_20_lower'] == 30.7
        assert result['bb_20_width'] == 40.1

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_bulk_compute_preserves_dataframe_index(self, mock_config):
        """Test that bulk computation preserves DataFrame index."""
        # Create DataFrame with custom index
        df_with_index = self.sample_df.copy()
        df_with_index.index = ['A', 'B', 'C']
        
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name]
        }
        
        handler = IndicatorHandler('test_indicator', self.mock_indicator)
        result = handler.bulk_compute(df_with_index)
        
        # Index should be preserved
        assert result.index.tolist() == ['A', 'B', 'C']

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_handler_with_lambda_configuration(self, mock_config):
        """Test handler works with lambda-based configuration."""
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [f'{name}_value', f'{name}_signal']
        }
        
        self.mock_indicator.update.return_value = (0.65, 0.35)
        
        handler = IndicatorHandler('custom_indicator', self.mock_indicator)
        result = handler.compute(self.sample_row)
        
        assert 'custom_indicator_value' in result
        assert 'custom_indicator_signal' in result
        assert result['custom_indicator_value'] == 0.65
        assert result['custom_indicator_signal'] == 0.35


class TestIndicatorHandlerEdgeCases:
    """Test edge cases and error conditions for IndicatorHandler."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_indicator = Mock()

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_empty_row_input(self, mock_config):
        """Test handling of empty row input."""
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name]
        }
        
        handler = IndicatorHandler('test_indicator', self.mock_indicator)
        empty_row = pd.Series(dtype=float)
        
        # Should raise KeyError for missing column
        with pytest.raises(KeyError):
            handler.compute(empty_row)

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_empty_dataframe_input(self, mock_config):
        """Test handling of empty DataFrame input."""
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name]
        }
        
        handler = IndicatorHandler('test_indicator', self.mock_indicator)
        empty_df = pd.DataFrame()
        
        # Should raise KeyError for missing column
        with pytest.raises(KeyError):
            handler.bulk_compute(empty_df)

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_indicator_returns_none(self, mock_config):
        """Test handling when indicator returns None."""
        self.mock_indicator.update.return_value = None
        
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name]
        }
        
        handler = IndicatorHandler('test_indicator', self.mock_indicator)
        row = pd.Series({'close': 100.0})
        result = handler.compute(row)
        
        assert pd.isna(result['test_indicator'])

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_indicator_returns_empty_tuple(self, mock_config):
        """Test handling when indicator returns empty tuple."""
        self.mock_indicator.update.return_value = ()
        
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name, f'{name}_signal']
        }
        
        handler = IndicatorHandler('test_indicator', self.mock_indicator)
        row = pd.Series({'close': 100.0})
        result = handler.compute(row)
        
        # Should pad with None values
        assert pd.isna(result['test_indicator'])
        assert pd.isna(result['test_indicator_signal'])

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_config_input_function_exception(self, mock_config):
        """Test handling of exception in configuration input function."""
        def bad_input_func(row):
            raise ValueError("Bad input configuration")
        
        mock_config.get.return_value = {
            'inputs': bad_input_func,
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': lambda name: [name]
        }
        
        handler = IndicatorHandler('test_indicator', self.mock_indicator)
        row = pd.Series({'close': 100.0})
        
        # Should propagate the configuration exception
        with pytest.raises(ValueError, match="Bad input configuration"):
            handler.compute(row)

    @patch('app.indicators.indicator_handler.INDICATOR_CONFIG')
    def test_config_output_function_exception(self, mock_config):
        """Test handling of exception in configuration output function."""
        def bad_output_func(name):
            raise ValueError("Bad output configuration")
        
        mock_config.get.return_value = {
            'inputs': lambda row: (row['close'],),
            'bulk_inputs': lambda df: (df['close'],),
            'outputs': bad_output_func
        }
        
        self.mock_indicator.update.return_value = 0.5
        
        handler = IndicatorHandler('test_indicator', self.mock_indicator)
        row = pd.Series({'close': 100.0})
        
        # Should propagate the configuration exception
        with pytest.raises(ValueError, match="Bad output configuration"):
            handler.compute(row)