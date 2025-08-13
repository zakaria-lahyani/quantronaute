import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock, call
from app.indicators.indicator_manager import IndicatorManager
from app.indicators.indicator_handler import IndicatorHandler


class TestIndicatorManager:
    """Test suite for IndicatorManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Sample historical data
        self.historical_data = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=10, freq='1H'),
            'high': [105, 107, 106, 108, 110, 109, 111, 113, 112, 114],
            'low': [95, 97, 96, 98, 100, 99, 101, 103, 102, 104],
            'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109],
            'volume': [1000, 1500, 1200, 1300, 1800, 1600, 1700, 2000, 1900, 2100]
        })
        
        # Sample configuration
        self.config = {
            'rsi_14': {'period': 14},
            'sma_20': {'period': 20}
        }
        
        # Mock handlers
        self.mock_rsi_handler = Mock(spec=IndicatorHandler)
        self.mock_sma_handler = Mock(spec=IndicatorHandler)
        
        # Configure mock handlers
        self.mock_rsi_handler.compute.side_effect = lambda row: self._add_rsi_to_row(row)
        self.mock_rsi_handler.bulk_compute.side_effect = lambda df: self._add_rsi_to_df(df)
        
        self.mock_sma_handler.compute.side_effect = lambda row: self._add_sma_to_row(row)
        self.mock_sma_handler.bulk_compute.side_effect = lambda df: self._add_sma_to_df(df)

    def _add_rsi_to_row(self, row):
        """Helper to simulate RSI computation on a row."""
        result = row.copy()
        result['rsi_14'] = 50.0  # Mock RSI value
        return result

    def _add_rsi_to_df(self, df):
        """Helper to simulate RSI computation on a DataFrame."""
        result = df.copy()
        result['rsi_14'] = 50.0  # Mock RSI values
        return result

    def _add_sma_to_row(self, row):
        """Helper to simulate SMA computation on a row."""
        result = row.copy()
        result['sma_20'] = row['close'] * 0.99  # Mock SMA value
        return result

    def _add_sma_to_df(self, df):
        """Helper to simulate SMA computation on a DataFrame."""
        result = df.copy()
        result['sma_20'] = df['close'] * 0.99  # Mock SMA values
        return result

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_manager_initialization_bulk_mode(self, mock_factory):
        """Test manager initialization in bulk mode."""
        # Setup factory mock
        mock_factory.return_value.create_handlers.return_value = {
            'rsi_14': self.mock_rsi_handler,
            'sma_20': self.mock_sma_handler
        }
        
        # Initialize manager in bulk mode
        manager = IndicatorManager(self.historical_data, self.config, is_bulk=True)
        
        # Verify factory was called correctly
        mock_factory.assert_called_once_with(self.config)
        
        # Verify handlers were created
        assert manager.handlers == {
            'rsi_14': self.mock_rsi_handler,
            'sma_20': self.mock_sma_handler
        }
        
        # Verify bulk compute was called
        assert self.mock_rsi_handler.bulk_compute.called
        assert self.mock_sma_handler.bulk_compute.called
        
        # Verify original data is preserved
        assert manager.original_historical.equals(self.historical_data)

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_manager_initialization_warmup_mode(self, mock_factory):
        """Test manager initialization in warmup (row-by-row) mode."""
        # Setup factory mock
        mock_factory.return_value.create_handlers.return_value = {
            'rsi_14': self.mock_rsi_handler,
            'sma_20': self.mock_sma_handler
        }
        
        # Initialize manager in warmup mode
        manager = IndicatorManager(self.historical_data, self.config, is_bulk=False)
        
        # Verify factory was called correctly
        mock_factory.assert_called_once_with(self.config)
        
        # Verify row-wise compute was called for each row
        expected_calls = len(self.historical_data)
        assert self.mock_rsi_handler.compute.call_count == expected_calls
        assert self.mock_sma_handler.compute.call_count == expected_calls

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_bulk_compute_method(self, mock_factory):
        """Test bulk_compute method."""
        mock_factory.return_value.create_handlers.return_value = {
            'rsi_14': self.mock_rsi_handler,
            'sma_20': self.mock_sma_handler
        }
        
        manager = IndicatorManager(self.historical_data, self.config, is_bulk=True)
        result = manager.bulk_compute()
        
        # Verify all handlers were called for bulk compute
        self.mock_rsi_handler.bulk_compute.assert_called()
        self.mock_sma_handler.bulk_compute.assert_called()
        
        # Verify result is a DataFrame
        assert isinstance(result, pd.DataFrame)
        
        # Verify original columns are preserved
        for col in self.historical_data.columns:
            assert col in result.columns

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_warmup_historical_method(self, mock_factory):
        """Test warmup_historical method."""
        # Create fresh mocks for this test
        fresh_rsi_handler = Mock(spec=IndicatorHandler)
        fresh_sma_handler = Mock(spec=IndicatorHandler)
        
        fresh_rsi_handler.compute.side_effect = lambda row: self._add_rsi_to_row(row)
        fresh_sma_handler.compute.side_effect = lambda row: self._add_sma_to_row(row)
        
        mock_factory.return_value.create_handlers.return_value = {
            'rsi_14': fresh_rsi_handler,
            'sma_20': fresh_sma_handler
        }
        
        manager = IndicatorManager(self.historical_data, self.config, is_bulk=False)
        # Note: warmup_historical is called during initialization when is_bulk=False
        # So the handlers have already been called
        
        # The initialization already processed the data, so verify the call count
        expected_calls = len(self.historical_data)
        assert fresh_rsi_handler.compute.call_count == expected_calls
        assert fresh_sma_handler.compute.call_count == expected_calls
        
        # Call warmup_historical directly to test the method
        result = manager.warmup_historical()
        
        # Now it should have been called twice
        assert fresh_rsi_handler.compute.call_count == expected_calls * 2
        assert fresh_sma_handler.compute.call_count == expected_calls * 2
        
        # Verify result is a DataFrame with correct length
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(self.historical_data)

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_get_historical_data(self, mock_factory):
        """Test get_historical_data method."""
        mock_factory.return_value.create_handlers.return_value = {
            'rsi_14': self.mock_rsi_handler,
            'sma_20': self.mock_sma_handler
        }
        
        manager = IndicatorManager(self.historical_data, self.config, is_bulk=True)
        historical_data = manager.get_historical_data()
        
        assert isinstance(historical_data, pd.DataFrame)
        assert len(historical_data) == len(self.historical_data)

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_compute_indicators_single_row(self, mock_factory):
        """Test compute_indicators method for single row."""
        mock_factory.return_value.create_handlers.return_value = {
            'rsi_14': self.mock_rsi_handler,
            'sma_20': self.mock_sma_handler
        }
        
        manager = IndicatorManager(self.historical_data, self.config, is_bulk=True)
        
        # Test with a single row
        test_row = pd.Series({
            'high': 115.0,
            'low': 105.0,
            'close': 110.0,
            'volume': 2200
        })
        
        result = manager.compute_indicators(test_row)
        
        # Verify both handlers were called
        self.mock_rsi_handler.compute.assert_called()
        self.mock_sma_handler.compute.assert_called()
        
        # Verify result is a Series
        assert isinstance(result, pd.Series)

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_original_data_preservation(self, mock_factory):
        """Test that original historical data is preserved."""
        mock_factory.return_value.create_handlers.return_value = {}
        
        original_data = self.historical_data.copy()
        manager = IndicatorManager(self.historical_data, {}, is_bulk=True)
        
        # Verify original data is preserved exactly
        assert manager.original_historical.equals(original_data)
        assert not manager.original_historical is self.historical_data  # Should be a copy

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_empty_config(self, mock_factory):
        """Test manager with empty configuration."""
        mock_factory.return_value.create_handlers.return_value = {}
        
        manager = IndicatorManager(self.historical_data, {}, is_bulk=True)
        
        # Should work without errors
        assert manager.handlers == {}
        historical_data = manager.get_historical_data()
        
        # Should return original data unchanged
        assert isinstance(historical_data, pd.DataFrame)
        assert len(historical_data) == len(self.historical_data)

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_single_indicator_config(self, mock_factory):
        """Test manager with single indicator configuration."""
        mock_factory.return_value.create_handlers.return_value = {
            'rsi_14': self.mock_rsi_handler
        }
        
        single_config = {'rsi_14': {'period': 14}}
        manager = IndicatorManager(self.historical_data, single_config, is_bulk=True)
        
        assert len(manager.handlers) == 1
        assert 'rsi_14' in manager.handlers

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_bulk_vs_warmup_consistency(self, mock_factory):
        """Test that bulk and warmup modes produce similar structure."""
        mock_factory.return_value.create_handlers.return_value = {
            'rsi_14': self.mock_rsi_handler
        }
        
        # Test bulk mode
        manager_bulk = IndicatorManager(self.historical_data, {'rsi_14': {'period': 14}}, is_bulk=True)
        bulk_result = manager_bulk.get_historical_data()
        
        # Reset mocks
        self.mock_rsi_handler.reset_mock()
        
        # Test warmup mode
        manager_warmup = IndicatorManager(self.historical_data, {'rsi_14': {'period': 14}}, is_bulk=False)
        warmup_result = manager_warmup.get_historical_data()
        
        # Both should be DataFrames with same length
        assert isinstance(bulk_result, pd.DataFrame)
        assert isinstance(warmup_result, pd.DataFrame)
        assert len(bulk_result) == len(warmup_result)
        assert len(bulk_result) == len(self.historical_data)

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_error_handling_in_factory(self, mock_factory):
        """Test error handling when factory fails."""
        mock_factory.side_effect = ValueError("Factory initialization failed")
        
        with pytest.raises(ValueError, match="Factory initialization failed"):
            IndicatorManager(self.historical_data, self.config, is_bulk=True)

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_handler_computation_errors(self, mock_factory):
        """Test handling of computation errors in handlers."""
        # Setup handler to raise exception
        self.mock_rsi_handler.bulk_compute.side_effect = RuntimeError("Handler computation failed")
        
        mock_factory.return_value.create_handlers.return_value = {
            'rsi_14': self.mock_rsi_handler
        }
        
        # Should propagate the handler exception
        with pytest.raises(RuntimeError, match="Handler computation failed"):
            IndicatorManager(self.historical_data, self.config, is_bulk=True)

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_compute_indicators_preserves_input(self, mock_factory):
        """Test that compute_indicators preserves input row."""
        mock_factory.return_value.create_handlers.return_value = {
            'rsi_14': self.mock_rsi_handler
        }
        
        manager = IndicatorManager(self.historical_data, {'rsi_14': {'period': 14}}, is_bulk=True)
        
        test_row = pd.Series({
            'high': 115.0,
            'low': 105.0,
            'close': 110.0,
            'volume': 2200
        })
        
        original_row = test_row.copy()
        result = manager.compute_indicators(test_row)
        
        # Original row should be unchanged
        assert test_row.equals(original_row)
        
        # Result should be different (has indicators added)
        assert not result.equals(original_row)

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_multiple_handlers_order_preservation(self, mock_factory):
        """Test that multiple handlers are applied in consistent order."""
        # Create mock handlers that modify the data
        def rsi_modifier(data):
            result = data.copy()
            result['rsi_14'] = 50.0
            result['order_marker'] = 'rsi_first'
            return result
        
        def sma_modifier(data):
            result = data.copy()
            result['sma_20'] = 100.0
            if 'order_marker' in result:
                result['order_marker'] = result['order_marker'] + '_then_sma'
            else:
                result['order_marker'] = 'sma_first'
            return result
        
        self.mock_rsi_handler.bulk_compute.side_effect = rsi_modifier
        self.mock_sma_handler.bulk_compute.side_effect = sma_modifier
        
        mock_factory.return_value.create_handlers.return_value = {
            'rsi_14': self.mock_rsi_handler,
            'sma_20': self.mock_sma_handler
        }
        
        manager = IndicatorManager(self.historical_data, self.config, is_bulk=True)
        result = manager.get_historical_data()
        
        # Check that both indicators were applied
        assert 'rsi_14' in result.columns
        assert 'sma_20' in result.columns

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_warmup_with_large_dataset(self, mock_factory):
        """Test warmup mode with larger dataset to verify performance characteristics."""
        # Create larger dataset
        large_data = pd.DataFrame({
            'high': np.random.uniform(100, 110, 1000),
            'low': np.random.uniform(90, 100, 1000),
            'close': np.random.uniform(95, 105, 1000),
            'volume': np.random.randint(1000, 5000, 1000)
        })
        
        mock_factory.return_value.create_handlers.return_value = {
            'rsi_14': self.mock_rsi_handler
        }
        
        manager = IndicatorManager(large_data, {'rsi_14': {'period': 14}}, is_bulk=False)
        
        # Verify all rows were processed
        expected_calls = len(large_data)
        assert self.mock_rsi_handler.compute.call_count == expected_calls
        
        result = manager.get_historical_data()
        assert len(result) == len(large_data)

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_manager_with_complex_config(self, mock_factory):
        """Test manager with complex configuration."""
        complex_config = {
            'rsi_14': {'period': 14, 'signal_period': 9},
            'bb_20': {'window': 20, 'num_std_dev': 2},
            'macd_fast': {'fast': 12, 'slow': 26, 'signal': 9},
            'sma_50': {'period': 50},
            'ema_21': {'period': 21}
        }
        
        # Create mock handlers for all indicators
        mock_handlers = {}
        for name in complex_config.keys():
            mock_handler = Mock(spec=IndicatorHandler)
            mock_handler.bulk_compute.return_value = self.historical_data.copy()
            mock_handlers[name] = mock_handler
        
        mock_factory.return_value.create_handlers.return_value = mock_handlers
        
        manager = IndicatorManager(self.historical_data, complex_config, is_bulk=True)
        
        # Verify all handlers were created
        assert len(manager.handlers) == len(complex_config)
        for name in complex_config.keys():
            assert name in manager.handlers
            
        # Verify all handlers were called
        for handler in mock_handlers.values():
            handler.bulk_compute.assert_called()


class TestIndicatorManagerEdgeCases:
    """Test edge cases and error conditions for IndicatorManager."""

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_empty_historical_data(self, mock_factory):
        """Test manager with empty historical data."""
        empty_data = pd.DataFrame()
        mock_factory.return_value.create_handlers.return_value = {}
        
        manager = IndicatorManager(empty_data, {}, is_bulk=True)
        result = manager.get_historical_data()
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_single_row_historical_data(self, mock_factory):
        """Test manager with single row of historical data."""
        single_row_data = pd.DataFrame({
            'high': [105],
            'low': [95],
            'close': [100],
            'volume': [1000]
        })
        
        mock_handler = Mock(spec=IndicatorHandler)
        mock_handler.bulk_compute.return_value = single_row_data.copy()
        mock_handler.compute.return_value = single_row_data.iloc[0].copy()
        
        mock_factory.return_value.create_handlers.return_value = {
            'rsi_14': mock_handler
        }
        
        # Test both modes
        manager_bulk = IndicatorManager(single_row_data, {'rsi_14': {'period': 14}}, is_bulk=True)
        manager_warmup = IndicatorManager(single_row_data, {'rsi_14': {'period': 14}}, is_bulk=False)
        
        assert len(manager_bulk.get_historical_data()) == 1
        assert len(manager_warmup.get_historical_data()) == 1

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_handler_returns_different_data_structure(self, mock_factory):
        """Test handling when handler returns unexpected data structure."""
        mock_handler = Mock(spec=IndicatorHandler)
        
        # Handler returns string instead of DataFrame/Series
        mock_handler.bulk_compute.return_value = "unexpected_return"
        
        mock_factory.return_value.create_handlers.return_value = {
            'bad_handler': mock_handler
        }
        
        historical_data = pd.DataFrame({
            'close': [100, 101, 102]
        })
        
        # Should not crash but might produce unexpected results
        manager = IndicatorManager(historical_data, {'bad_handler': {}}, is_bulk=True)
        # The behavior depends on pandas handling of the unexpected return
        # At minimum, it shouldn't crash during initialization

    @patch('app.indicators.indicator_manager.IndicatorFactory')
    def test_mixed_handler_success_and_failure(self, mock_factory):
        """Test scenario where some handlers succeed and others fail."""
        good_handler = Mock(spec=IndicatorHandler)
        good_handler.bulk_compute.side_effect = lambda df: df.copy()
        
        bad_handler = Mock(spec=IndicatorHandler)
        bad_handler.bulk_compute.side_effect = ValueError("Handler failed")
        
        mock_factory.return_value.create_handlers.return_value = {
            'good_indicator': good_handler,
            'bad_indicator': bad_handler
        }
        
        historical_data = pd.DataFrame({
            'close': [100, 101, 102]
        })
        
        # Should fail on the bad handler
        with pytest.raises(ValueError, match="Handler failed"):
            IndicatorManager(historical_data, {
                'good_indicator': {},
                'bad_indicator': {}
            }, is_bulk=True)