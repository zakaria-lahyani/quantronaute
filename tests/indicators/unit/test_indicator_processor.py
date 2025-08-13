import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock, call
from app.indicators.indicator_processor import IndicatorProcessor
from app.indicators.indicator_manager import IndicatorManager


class TestIndicatorProcessor:
    """Test suite for IndicatorProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Sample configurations for different timeframes
        self.configs = {
            '1m': {'rsi_14': {'period': 14}, 'sma_20': {'period': 20}},
            '5m': {'macd_12_26': {'fast': 12, 'slow': 26, 'signal': 9}},
            '1h': {'bb_20': {'window': 20, 'num_std_dev': 2}}
        }
        
        # Sample historical data for different timeframes
        self.historicals = {
            '1m': pd.DataFrame({
                'timestamp': pd.date_range('2023-01-01', periods=100, freq='1min'),
                'high': np.random.uniform(100, 110, 100),
                'low': np.random.uniform(90, 100, 100),
                'close': np.random.uniform(95, 105, 100),
                'volume': np.random.randint(1000, 5000, 100)
            }),
            '5m': pd.DataFrame({
                'timestamp': pd.date_range('2023-01-01', periods=50, freq='5min'),
                'high': np.random.uniform(100, 110, 50),
                'low': np.random.uniform(90, 100, 50),
                'close': np.random.uniform(95, 105, 50),
                'volume': np.random.randint(1000, 5000, 50)
            }),
            '1h': pd.DataFrame({
                'timestamp': pd.date_range('2023-01-01', periods=24, freq='1H'),
                'high': np.random.uniform(100, 110, 24),
                'low': np.random.uniform(90, 100, 24),
                'close': np.random.uniform(95, 105, 24),
                'volume': np.random.randint(1000, 5000, 24)
            })
        }
        
        # Sample market data row
        self.sample_row = pd.Series({
            'timestamp': pd.Timestamp('2023-01-01 12:00:00'),
            'high': 105.0,
            'low': 95.0,
            'close': 100.0,
            'volume': 2000
        })

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_processor_initialization_success(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test successful processor initialization."""
        # Setup mocks
        mock_recent_proc = Mock()
        mock_recent_proc_class.return_value = mock_recent_proc
        
        mock_hist_proc = Mock()
        mock_hist_proc_class.return_value = mock_hist_proc
        
        mock_managers = {}
        for tf in self.configs.keys():
            mock_managers[tf] = Mock(spec=IndicatorManager)
        
        mock_manager_class.side_effect = lambda hist_data, config, is_bulk: mock_managers[
            next(tf for tf in self.configs.keys() if self.historicals[tf] is hist_data)
        ]
        
        # Initialize processor
        processor = IndicatorProcessor(
            self.configs,
            self.historicals,
            is_bulk=True,
            recent_rows_limit=5
        )
        
        # Verify initialization
        assert processor._is_bulk == True
        assert processor._recent_rows_limit == 5
        assert processor._timeframes == set(self.configs.keys())
        
        # Verify managers were created
        assert len(processor._managers) == len(self.configs)
        
        # Verify recent rows manager was initialized
        mock_recent_proc_class.assert_called_once_with(
            list(self.configs.keys()),
            max_rows=5
        )
        
        # Verify historical data processor was initialized
        mock_hist_proc_class.assert_called_once_with(mock_recent_proc, max_rows=5)
        
        # Verify historical data was initialized
        mock_hist_proc.initialize_from_historical.assert_called_once()

    def test_processor_initialization_validation_errors(self):
        """Test processor initialization validation errors."""
        # Empty configs
        with pytest.raises(ValueError, match="configs must be a non-empty dictionary"):
            IndicatorProcessor({}, self.historicals, is_bulk=True)
        
        # Empty historicals
        with pytest.raises(ValueError, match="historicals must be a non-empty dictionary"):
            IndicatorProcessor(self.configs, {}, is_bulk=True)
        
        # is_bulk not boolean
        with pytest.raises(TypeError, match="is_bulk must be a boolean"):
            IndicatorProcessor(self.configs, self.historicals, is_bulk="true")
        
        # Invalid recent_rows_limit
        with pytest.raises(ValueError, match="recent_rows_limit must be a positive integer"):
            IndicatorProcessor(self.configs, self.historicals, is_bulk=True, recent_rows_limit=0)
        
        # Mismatched timeframes
        mismatched_historicals = {'1m': self.historicals['1m']}  # Missing timeframes
        with pytest.raises(ValueError, match="Timeframe mismatch"):
            IndicatorProcessor(self.configs, mismatched_historicals, is_bulk=True)
        
        # Non-DataFrame historical data
        invalid_historicals = self.historicals.copy()
        invalid_historicals['1m'] = "not a dataframe"
        with pytest.raises(TypeError, match="Historical data for timeframe 1m must be a DataFrame"):
            IndicatorProcessor(self.configs, invalid_historicals, is_bulk=True)
        
        # Empty DataFrame
        empty_historicals = self.historicals.copy()
        empty_historicals['1m'] = pd.DataFrame()
        with pytest.raises(ValueError, match="Historical data for timeframe 1m cannot be empty"):
            IndicatorProcessor(self.configs, empty_historicals, is_bulk=True)

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_compute_indicators_success(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test successful indicator computation."""
        # Setup mocks
        mock_recent_proc = Mock()
        mock_recent_proc_class.return_value = mock_recent_proc
        
        mock_hist_proc = Mock()
        mock_hist_proc_class.return_value = mock_hist_proc
        
        mock_manager = Mock(spec=IndicatorManager)
        result_row = self.sample_row.copy()
        result_row['rsi_14'] = 50.0
        mock_manager.compute_indicators.return_value = result_row
        
        mock_manager_class.return_value = mock_manager
        
        # Initialize processor with single timeframe for simplicity
        single_config = {'1m': self.configs['1m']}
        single_historical = {'1m': self.historicals['1m']}
        
        processor = IndicatorProcessor(single_config, single_historical, is_bulk=True)
        
        # Test compute_indicators
        result = processor.compute_indicators('1m', self.sample_row)
        
        # Verify manager was called
        mock_manager.compute_indicators.assert_called()
        
        # Verify result
        assert isinstance(result, pd.Series)
        assert result['rsi_14'] == 50.0

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_compute_indicators_invalid_timeframe(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test compute_indicators with invalid timeframe."""
        # Setup basic mocks
        mock_recent_proc_class.return_value = Mock()
        mock_hist_proc_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        
        processor = IndicatorProcessor(self.configs, self.historicals, is_bulk=True)
        
        with pytest.raises(ValueError, match="Unsupported timeframe: invalid_tf"):
            processor.compute_indicators('invalid_tf', self.sample_row)

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_compute_indicators_invalid_row(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test compute_indicators with invalid row input."""
        # Setup basic mocks
        mock_recent_proc_class.return_value = Mock()
        mock_hist_proc_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        
        processor = IndicatorProcessor(self.configs, self.historicals, is_bulk=True)
        
        # Test with non-Series input
        with pytest.raises(TypeError, match="row must be a pandas Series"):
            processor.compute_indicators('1m', "not a series")
        
        # Test with empty Series
        with pytest.raises(ValueError, match="row cannot be empty"):
            processor.compute_indicators('1m', pd.Series(dtype=float))

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_process_new_row_success(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test successful new row processing."""
        # Setup mocks
        mock_recent_proc = Mock()
        mock_recent_proc_class.return_value = mock_recent_proc
        
        mock_hist_proc = Mock()
        mock_hist_proc_class.return_value = mock_hist_proc
        
        mock_manager = Mock(spec=IndicatorManager)
        computed_row = self.sample_row.copy()
        computed_row['rsi_14'] = 50.0
        mock_manager.compute_indicators.return_value = computed_row
        
        stored_row = computed_row.copy()
        stored_row['stored_timestamp'] = pd.Timestamp('2023-01-01 12:00:00')
        mock_recent_proc.get_latest_row.return_value = stored_row
        
        mock_manager_class.return_value = mock_manager
        
        # Initialize processor
        single_config = {'1m': self.configs['1m']}
        single_historical = {'1m': self.historicals['1m']}
        processor = IndicatorProcessor(single_config, single_historical, is_bulk=True)
        
        # Test process_new_row
        result = processor.process_new_row('1m', self.sample_row)
        
        # Verify processing steps
        mock_manager.compute_indicators.assert_called()
        mock_recent_proc.add_or_update_row.assert_called_with('1m', computed_row)
        mock_recent_proc.get_latest_row.assert_called_with('1m')
        
        # Verify result is the stored row
        assert result.equals(stored_row)

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_process_new_row_storage_failure(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test new row processing when storage fails."""
        # Setup mocks
        mock_recent_proc = Mock()
        mock_recent_proc_class.return_value = mock_recent_proc
        
        mock_hist_proc = Mock()
        mock_hist_proc_class.return_value = mock_hist_proc
        
        mock_manager = Mock(spec=IndicatorManager)
        mock_manager.compute_indicators.return_value = self.sample_row
        
        # Simulate storage failure
        mock_recent_proc.get_latest_row.return_value = None
        
        mock_manager_class.return_value = mock_manager
        
        processor = IndicatorProcessor({'1m': {}}, {'1m': self.historicals['1m']}, is_bulk=True)
        
        with pytest.raises(RuntimeError, match="Failed to store row for timeframe 1m"):
            processor.process_new_row('1m', self.sample_row)

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_process_new_row_mtf_success(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test multi-timeframe row processing."""
        # Setup mocks
        mock_recent_proc = Mock()
        mock_recent_proc_class.return_value = mock_recent_proc
        
        mock_hist_proc = Mock()
        mock_hist_proc_class.return_value = mock_hist_proc
        
        # Create managers for each timeframe
        mock_managers = {}
        for tf in self.configs.keys():
            mock_manager = Mock(spec=IndicatorManager)
            computed_row = self.sample_row.copy()
            computed_row[f'indicator_{tf}'] = 50.0
            mock_manager.compute_indicators.return_value = computed_row
            mock_managers[tf] = mock_manager
        
        mock_manager_class.side_effect = lambda hist_data, config, is_bulk: mock_managers[
            next(tf for tf in self.configs.keys() if self.historicals[tf] is hist_data)
        ]
        
        # Mock storage returns
        def get_latest_row(tf):
            result = self.sample_row.copy()
            result[f'stored_{tf}'] = True
            return result
        
        mock_recent_proc.get_latest_row.side_effect = get_latest_row
        
        processor = IndicatorProcessor(self.configs, self.historicals, is_bulk=True)
        
        # Test MTF processing
        new_rows = {
            '1m': self.sample_row,
            '5m': self.sample_row,
            '1h': self.sample_row
        }
        
        results = processor.process_new_row_mtf(new_rows)
        
        # Verify all timeframes were processed
        assert len(results) == len(self.configs)
        for tf in self.configs.keys():
            assert tf in results
            assert f'stored_{tf}' in results[tf]

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_process_new_row_mtf_partial_failure(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test MTF processing with partial failures."""
        # Setup mocks
        mock_recent_proc = Mock()
        mock_recent_proc_class.return_value = mock_recent_proc
        
        mock_hist_proc = Mock()
        mock_hist_proc_class.return_value = mock_hist_proc
        
        # Create managers with one that fails
        mock_managers = {}
        for i, tf in enumerate(self.configs.keys()):
            mock_manager = Mock(spec=IndicatorManager)
            if i == 0:  # First manager fails
                mock_manager.compute_indicators.side_effect = ValueError("Computation failed")
            else:
                mock_manager.compute_indicators.return_value = self.sample_row
            mock_managers[tf] = mock_manager
        
        mock_manager_class.side_effect = lambda hist_data, config, is_bulk: mock_managers[
            next(tf for tf in self.configs.keys() if self.historicals[tf] is hist_data)
        ]
        
        processor = IndicatorProcessor(self.configs, self.historicals, is_bulk=True)
        
        new_rows = {tf: self.sample_row for tf in self.configs.keys()}
        
        with pytest.raises(RuntimeError, match="Processing failed for timeframes"):
            processor.process_new_row_mtf(new_rows)

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_get_recent_rows(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test getting recent rows."""
        # Setup mocks
        mock_recent_proc = Mock()
        recent_df = pd.DataFrame({
            'close': [100, 101, 102],
            'rsi_14': [45, 50, 55]
        })
        mock_recent_proc.get_all_rows.return_value = recent_df
        mock_recent_proc_class.return_value = mock_recent_proc
        
        mock_hist_proc_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        
        processor = IndicatorProcessor(self.configs, self.historicals, is_bulk=True)
        
        # Test get_recent_rows
        result = processor.get_recent_rows('1m')
        
        mock_recent_proc.get_all_rows.assert_called_with('1m')
        assert result.equals(recent_df)

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_get_recent_rows_insufficient_data(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test get_recent_rows with insufficient data."""
        # Setup mocks
        mock_recent_proc = Mock()
        mock_recent_proc.get_all_rows.return_value = pd.DataFrame({'close': [100]})  # Only 1 row
        mock_recent_proc_class.return_value = mock_recent_proc
        
        mock_hist_proc_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        
        processor = IndicatorProcessor(self.configs, self.historicals, is_bulk=True)
        
        with pytest.raises(ValueError, match="Insufficient data for timeframe 1m"):
            processor.get_recent_rows('1m', min_rows=5)

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_get_latest_row(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test getting latest row."""
        # Setup mocks
        mock_recent_proc = Mock()
        latest_row = pd.Series({'close': 100, 'rsi_14': 50})
        mock_recent_proc.get_latest_row.return_value = latest_row
        mock_recent_proc_class.return_value = mock_recent_proc
        
        mock_hist_proc_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        
        processor = IndicatorProcessor(self.configs, self.historicals, is_bulk=True)
        
        result = processor.get_latest_row('1m')
        
        mock_recent_proc.get_latest_row.assert_called_with('1m')
        assert result.equals(latest_row)

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_get_historical_indicator_data(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test getting historical indicator data."""
        # Setup mocks
        mock_recent_proc_class.return_value = Mock()
        mock_hist_proc_class.return_value = Mock()
        
        mock_manager = Mock(spec=IndicatorManager)
        historical_df = pd.DataFrame({
            'close': [100, 101, 102],
            'rsi_14': [45, 50, 55]
        })
        mock_manager.get_historical_data.return_value = historical_df
        
        mock_manager_class.return_value = mock_manager
        
        single_config = {'1m': self.configs['1m']}
        single_historical = {'1m': self.historicals['1m']}
        processor = IndicatorProcessor(single_config, single_historical, is_bulk=True)
        
        result = processor.get_historical_indicator_data('1m')
        
        mock_manager.get_historical_data.assert_called_once()
        assert result.equals(historical_df)

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_get_supported_timeframes(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test getting supported timeframes."""
        # Setup mocks
        mock_recent_proc_class.return_value = Mock()
        mock_hist_proc_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        
        processor = IndicatorProcessor(self.configs, self.historicals, is_bulk=True)
        
        timeframes = processor.get_supported_timeframes()
        
        assert isinstance(timeframes, list)
        assert set(timeframes) == set(self.configs.keys())
        assert timeframes == sorted(timeframes)  # Should be sorted

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_clear_recent_data(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test clearing recent data."""
        # Setup mocks
        mock_recent_proc = Mock()
        mock_recent_proc_class.return_value = mock_recent_proc
        
        mock_hist_proc_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        
        processor = IndicatorProcessor(self.configs, self.historicals, is_bulk=True)
        
        # Test clearing specific timeframe
        processor.clear_recent_data('1m')
        mock_recent_proc.clear_timeframe.assert_called_with('1m')
        
        # Test clearing all timeframes
        processor.clear_recent_data()
        mock_recent_proc.clear_all.assert_called_once()

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_has_sufficient_recent_data(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test checking for sufficient recent data."""
        # Setup mocks
        mock_recent_proc = Mock()
        mock_recent_proc.has_sufficient_data.return_value = True
        mock_recent_proc_class.return_value = mock_recent_proc
        
        mock_hist_proc_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        
        processor = IndicatorProcessor(self.configs, self.historicals, is_bulk=True)
        
        result = processor.has_sufficient_recent_data('1m', 5)
        
        mock_recent_proc.has_sufficient_data.assert_called_with('1m', 5)
        assert result == True

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_processor_str_representation(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test processor string representation."""
        # Setup mocks
        mock_recent_proc_class.return_value = Mock()
        mock_hist_proc_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        
        processor = IndicatorProcessor(self.configs, self.historicals, is_bulk=True, recent_rows_limit=10)
        
        str_repr = str(processor)
        
        assert "IndicatorProcessor" in str_repr
        assert "is_bulk=True" in str_repr
        assert "recent_rows_limit=10" in str_repr
        assert "timeframes=" in str_repr

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_processor_len_method(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test processor len method."""
        # Setup mocks
        mock_recent_proc = MagicMock()
        mock_recent_proc.__len__.return_value = 15
        mock_recent_proc_class.return_value = mock_recent_proc
        
        mock_hist_proc_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        
        processor = IndicatorProcessor(self.configs, self.historicals, is_bulk=True)
        
        assert len(processor) == 15

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_mtf_input_validation(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test multi-timeframe input validation."""
        # Setup basic mocks
        mock_recent_proc_class.return_value = Mock()
        mock_hist_proc_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        
        processor = IndicatorProcessor(self.configs, self.historicals, is_bulk=True)
        
        # Test invalid input types
        with pytest.raises(TypeError, match="new_rows must be a dictionary"):
            processor.process_new_row_mtf("not a dict")
        
        # Test empty input
        with pytest.raises(ValueError, match="new_rows cannot be empty"):
            processor.process_new_row_mtf({})
        
        # Test invalid timeframe in input
        with pytest.raises(ValueError, match="Unsupported timeframe"):
            processor.process_new_row_mtf({'invalid_tf': self.sample_row})
        
        # Test invalid row in input
        with pytest.raises(TypeError, match="row must be a pandas Series"):
            processor.process_new_row_mtf({'1m': "not a series"})


class TestIndicatorProcessorEdgeCases:
    """Test edge cases and error conditions for IndicatorProcessor."""

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_manager_creation_failure(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test handling of manager creation failure."""
        # Setup mocks
        mock_recent_proc_class.return_value = Mock()
        mock_hist_proc_class.return_value = Mock()
        
        # Manager creation fails
        mock_manager_class.side_effect = ValueError("Manager creation failed")
        
        configs = {'1m': {'rsi_14': {'period': 14}}}
        historicals = {'1m': pd.DataFrame({'close': [100, 101, 102]})}
        
        with pytest.raises(ValueError, match="Manager creation failed"):
            IndicatorProcessor(configs, historicals, is_bulk=True)

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_historical_initialization_failure(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test handling of historical data initialization failure."""
        # Setup mocks
        mock_recent_proc_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        
        mock_hist_proc = Mock()
        mock_hist_proc.initialize_from_historical.side_effect = RuntimeError("Initialization failed")
        mock_hist_proc_class.return_value = mock_hist_proc
        
        configs = {'1m': {'rsi_14': {'period': 14}}}
        historicals = {'1m': pd.DataFrame({'close': [100, 101, 102]})}
        
        with pytest.raises(RuntimeError, match="Initialization failed"):
            IndicatorProcessor(configs, historicals, is_bulk=True)

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_indicator_computation_exception_handling(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test handling of indicator computation exceptions."""
        # Setup mocks
        mock_recent_proc_class.return_value = Mock()
        mock_hist_proc_class.return_value = Mock()
        
        mock_manager = Mock(spec=IndicatorManager)
        mock_manager.compute_indicators.side_effect = KeyError("Missing column")
        mock_manager_class.return_value = mock_manager
        
        configs = {'1m': {'rsi_14': {'period': 14}}}
        historicals = {'1m': pd.DataFrame({'close': [100, 101, 102]})}
        
        processor = IndicatorProcessor(configs, historicals, is_bulk=True)
        
        sample_row = pd.Series({'close': 100})
        
        # Should propagate the exception
        with pytest.raises(KeyError, match="Missing column"):
            processor.compute_indicators('1m', sample_row)

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_processor_with_single_timeframe(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test processor with single timeframe configuration."""
        # Setup mocks
        mock_recent_proc_class.return_value = Mock()
        mock_hist_proc_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        
        single_config = {'1m': {'rsi_14': {'period': 14}}}
        single_historical = {'1m': pd.DataFrame({'close': [100, 101, 102]})}
        
        processor = IndicatorProcessor(single_config, single_historical, is_bulk=True)
        
        assert processor.get_supported_timeframes() == ['1m']
        assert len(processor._managers) == 1

    @patch('app.indicators.indicator_processor.IndicatorManager')
    @patch('app.indicators.indicator_processor.RecentRowsProcessor')
    @patch('app.indicators.indicator_processor.HistoricalDataProcessor')
    def test_processor_with_large_number_of_timeframes(self, mock_hist_proc_class, mock_recent_proc_class, mock_manager_class):
        """Test processor with many timeframes."""
        # Setup mocks
        mock_recent_proc_class.return_value = Mock()
        mock_hist_proc_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        
        # Create many timeframes
        many_configs = {}
        many_historicals = {}
        for i in range(10):
            tf = f'{i}m'
            many_configs[tf] = {'rsi_14': {'period': 14}}
            many_historicals[tf] = pd.DataFrame({'close': [100, 101, 102]})
        
        processor = IndicatorProcessor(many_configs, many_historicals, is_bulk=True)
        
        assert len(processor.get_supported_timeframes()) == 10
        assert len(processor._managers) == 10