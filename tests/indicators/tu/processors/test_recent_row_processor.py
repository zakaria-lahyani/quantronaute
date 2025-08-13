"""
RecentRowsProcessor Test Suite
=============================

Comprehensive test suite for the RecentRowsProcessor class, validating all functionality
including initialization, row management, backtesting support, and error handling.

Expected Behavior Overview:
--------------------------

1. INITIALIZATION:
   - Creates storage for specified timeframes with configurable row limits
   - Validates input parameters and raises appropriate errors
   - Sets up logging and internal state correctly

2. ROW MANAGEMENT:
   - add_or_update_row(): Adds new rows or updates existing ones based on timestamp
   - get_latest_row(): Retrieves most recent row for a timeframe
   - get_all_rows(): Returns all rows as DataFrame with time indexing
   - Maintains circular buffer behavior with max_rows limit

3. BACKTESTING SUPPORT:
   - process_backtest_row(): Combines current row with previous row data
   - Prefixes previous row columns with 'previous_' to avoid conflicts
   - Essential for indicators that need previous values

4. DATA INTEGRITY:
   - Defensive copying prevents external modifications
   - Input validation ensures data quality
   - Immutable operations preserve original data

5. UTILITY METHODS:
   - get_row_count(): Returns number of stored rows
   - clear_timeframe()/clear_all(): Cleanup operations
   - has_sufficient_data(): Validates minimum data requirements
   - get_timeframes(): Returns supported timeframes

6. ERROR HANDLING:
   - Comprehensive validation of all inputs
   - Clear error messages for debugging
   - Crash-hard philosophy for data quality

7. PERFORMANCE:
   - O(1) append/pop operations using deque
   - Lazy DataFrame conversion
   - Memory-efficient circular buffer storage
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
import logging

from app.indicators.processors.recent_row_processor import RecentRowsProcessor


class TestRecentRowsProcessor:
    """
    Comprehensive test suite for RecentRowsProcessor.

    Tests cover all aspects of the processor including initialization,
    row management, backtesting, error handling, and edge cases.
    """

    @pytest.fixture
    def sample_timeframes(self):
        """
        Sample timeframes for testing.

        Expected Behavior:
        - Provides realistic timeframe identifiers
        - Used across multiple test scenarios
        - Represents common trading timeframes

        Returns:
            List[str]: List of timeframe identifiers
        """
        return ['1m', '5m', '15m', '1h']

    @pytest.fixture
    def sample_row(self):
        """
        Sample market data row for testing.

        Expected Behavior:
        - Contains all standard OHLCV fields
        - Includes timestamp for duplicate detection
        - Represents realistic market data structure

        Returns:
            pd.Series: Single row of market data
        """
        return pd.Series({
            'time': '2023-01-01 10:00:00',
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 102.0,
            'volume': 1000.0
        })

    @pytest.fixture
    def sample_rows_sequence(self):
        """
        Sequence of market data rows for testing.

        Expected Behavior:
        - Multiple rows with sequential timestamps
        - Used for testing bulk operations and time-based logic
        - Realistic progression of market data

        Returns:
            List[pd.Series]: Sequence of market data rows
        """
        base_time = datetime(2023, 1, 1, 10, 0, 0)
        rows = []

        for i in range(5):
            row = pd.Series({
                'time': base_time + timedelta(minutes=i),
                'open': 100.0 + i,
                'high': 105.0 + i,
                'low': 95.0 + i,
                'close': 102.0 + i,
                'volume': 1000.0 + i * 100
            })
            rows.append(row)

        return rows

    @pytest.fixture
    def processor(self, sample_timeframes):
        """
        Standard processor instance for testing.

        Expected Behavior:
        - Initialized with sample timeframes
        - Uses default max_rows setting
        - Ready for testing operations

        Returns:
            RecentRowsProcessor: Configured processor instance
        """
        return RecentRowsProcessor(sample_timeframes)

    def test_initialization_valid_params(self, sample_timeframes):
        """
        Test successful initialization with valid parameters.

        Expected Behavior:
        - Creates processor with specified timeframes
        - Sets max_rows correctly
        - Initializes empty storage for each timeframe
        - Sets up internal state properly
        - Logging is configured
        """
        max_rows = 10
        processor = RecentRowsProcessor(sample_timeframes, max_rows)

        # Verify basic attributes
        assert processor.get_timeframes() == sample_timeframes
        assert processor._max_rows == max_rows

        # Verify storage initialization
        for tf in sample_timeframes:
            assert processor.get_row_count(tf) == 0
            assert processor.get_latest_row(tf) is None
            assert len(processor.get_all_rows(tf)) == 0

    def test_initialization_default_max_rows(self, sample_timeframes):
        """
        Test initialization with default max_rows.

        Expected Behavior:
        - Uses DEFAULT_MAX_ROWS constant when not specified
        - All other initialization behavior remains the same
        - Demonstrates default parameter handling
        """
        processor = RecentRowsProcessor(sample_timeframes)
        assert processor._max_rows == RecentRowsProcessor.DEFAULT_MAX_ROWS

    def test_initialization_invalid_timeframes(self):
        """
        Test initialization with invalid timeframes.

        Expected Behavior:
        - Empty timeframes list raises ValueError
        - Non-string timeframes raise TypeError
        - Clear error messages for debugging
        - Follows crash-hard philosophy
        """
        # Empty timeframes
        with pytest.raises(ValueError, match="timeframes cannot be empty"):
            RecentRowsProcessor([])

        # Non-string timeframes
        with pytest.raises(TypeError, match="All timeframes must be strings"):
            RecentRowsProcessor(['1m', 5, '1h'])

    def test_initialization_invalid_max_rows(self, sample_timeframes):
        """
        Test initialization with invalid max_rows.

        Expected Behavior:
        - max_rows less than 1 raises ValueError
        - Zero and negative values are rejected
        - Clear error message for debugging
        """
        with pytest.raises(ValueError, match="max_rows must be at least 1"):
            RecentRowsProcessor(sample_timeframes, max_rows=0)

        with pytest.raises(ValueError, match="max_rows must be at least 1"):
            RecentRowsProcessor(sample_timeframes, max_rows=-1)

    def test_add_or_update_row_new_row(self, processor, sample_row):
        """
        Test adding a new row to empty storage.

        Expected Behavior:
        - Returns False indicating new row was added
        - Row is stored in the specified timeframe
        - Row count increases to 1
        - Latest row includes original + previous_* columns with NaN
        - Original row is not modified (defensive copying)
        """
        original_row = sample_row.copy()
        result = processor.add_or_update_row('1m', sample_row)

        # Verify return value indicates new row
        assert result is False

        # Verify row count and presence
        assert processor.get_row_count('1m') == 1
        latest = processor.get_latest_row('1m')
        assert latest is not None

        # Verify all original columns are present
        for col in original_row.index:
            assert col in latest.index
            assert latest[col] == original_row[col]

        # Verify all previous_* columns are present and NaN
        for col in original_row.index:
            prev_col = f'previous_{col}'
            assert prev_col in latest.index
            assert pd.isna(latest[prev_col])

        # Verify original row unchanged
        pd.testing.assert_series_equal(sample_row, original_row, check_names=False)

    def test_add_or_update_row_update_existing(self, processor, sample_row):
        """
        Test updating an existing row with same timestamp.

        Expected Behavior:
        - First addition returns False (new row)
        - Second addition with same timestamp returns True (update)
        - Row count remains 1 after update
        - Latest row contains updated data
        - Timestamp-based duplicate detection works correctly
        """
        # Add initial row
        result1 = processor.add_or_update_row('1m', sample_row)
        assert result1 is False
        assert processor.get_row_count('1m') == 1

        # Update with same timestamp
        updated_row = sample_row.copy()
        updated_row['close'] = 999.0  # Change a value

        result2 = processor.add_or_update_row('1m', updated_row)
        assert result2 is True
        assert processor.get_row_count('1m') == 1  # Count unchanged

        # Verify updated data
        latest = processor.get_latest_row('1m')
        assert latest['close'] == 999.0

    def test_add_or_update_row_invalid_timeframe(self, processor, sample_row):
        """
        Test adding row with unsupported timeframe.

        Expected Behavior:
        - Raises ValueError for unsupported timeframe
        - Error message includes supported timeframes
        - No data is modified
        - Follows crash-hard philosophy
        """
        with pytest.raises(ValueError, match="Unsupported timeframe: 30m"):
            processor.add_or_update_row('30m', sample_row)

    def test_add_or_update_row_invalid_row_type(self, processor):
        """
        Test adding invalid row type.

        Expected Behavior:
        - Raises TypeError for non-Series input
        - Clear error message for debugging
        - No data is modified
        """
        with pytest.raises(TypeError, match="row must be a pandas Series"):
            processor.add_or_update_row('1m', {'close': 100.0})

    def test_circular_buffer_behavior(self, sample_timeframes):
        """
        Test circular buffer behavior with max_rows limit.

        Expected Behavior:
        - Accepts rows up to max_rows limit
        - Oldest rows are automatically removed when limit exceeded
        - Row count never exceeds max_rows
        - Most recent rows are always preserved
        - Demonstrates deque maxlen behavior
        """
        max_rows = 3
        processor = RecentRowsProcessor(sample_timeframes, max_rows)

        # Add more rows than max_rows
        base_time = datetime(2023, 1, 1, 10, 0, 0)
        for i in range(5):  # Add 5 rows, max is 3
            row = pd.Series({
                'time': base_time + timedelta(minutes=i),
                'close': 100.0 + i
            })
            processor.add_or_update_row('1m', row)

        # Verify only max_rows are kept
        assert processor.get_row_count('1m') == max_rows

        # Verify most recent rows are preserved
        all_rows = processor.get_all_rows('1m')
        expected_closes = [102.0, 103.0, 104.0]  # Last 3 rows
        actual_closes = all_rows['close'].tolist()
        assert actual_closes == expected_closes

    def test_get_latest_row_empty_storage(self, processor):
        """
        Test getting latest row from empty storage.

        Expected Behavior:
        - Returns None when no rows exist
        - No exceptions are raised
        - Graceful handling of empty state
        """
        result = processor.get_latest_row('1m')
        assert result is None

    def test_get_latest_row_with_data(self, processor, sample_rows_sequence):
        """
        Test getting latest row with data present.

        Expected Behavior:
        - Returns most recently added row
        - Returned row is a copy (defensive copying)
        - Modifying returned row doesn't affect storage
        """
        # Add multiple rows
        for row in sample_rows_sequence:
            processor.add_or_update_row('1m', row)

        latest = processor.get_latest_row('1m')
        expected_latest = sample_rows_sequence[-1]

        # Verify correct row returned (processor adds previous_* columns)
        # Check that original columns match
        for col in expected_latest.index:
            assert latest[col] == expected_latest[col], f"Mismatch in column {col}"
        
        # Verify processor added previous_* columns
        expected_previous_cols = [f'previous_{col}' for col in expected_latest.index]
        for prev_col in expected_previous_cols:
            assert prev_col in latest.index, f"Expected previous column {prev_col} not found"

        # Verify defensive copying
        latest['close'] = 999.0
        actual_latest = processor.get_latest_row('1m')
        assert actual_latest['close'] != 999.0

    def test_get_all_rows_empty_storage(self, processor):
        """
        Test getting all rows from empty storage.

        Expected Behavior:
        - Returns empty DataFrame
        - DataFrame has no rows or columns
        - No exceptions are raised
        """
        result = processor.get_all_rows('1m')
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        assert len(result.columns) == 0

    def test_get_all_rows_with_data(self, processor, sample_rows_sequence):
        """
        Test getting all rows with data present.

        Expected Behavior:
        - Returns DataFrame with all stored rows
        - Time column is converted to datetime and set as index
        - All original columns are preserved
        - Rows are in chronological order
        """
        # Add multiple rows
        for row in sample_rows_sequence:
            processor.add_or_update_row('1m', row)

        df = processor.get_all_rows('1m')

        # Verify structure
        assert len(df) == len(sample_rows_sequence)
        assert df.index.name == 'time'
        assert isinstance(df.index, pd.DatetimeIndex)

        # Verify data integrity
        expected_closes = [row['close'] for row in sample_rows_sequence]
        actual_closes = df['close'].tolist()
        assert actual_closes == expected_closes

    def test_get_all_rows_no_time_column(self, processor):
        """
        Test getting all rows when time column is missing.

        Expected Behavior:
        - Returns DataFrame without time index processing
        - No errors are raised
        - Data is preserved as-is
        - Handles edge case gracefully
        """
        row_without_time = pd.Series({
            'open': 100.0,
            'close': 102.0,
            'volume': 1000.0
        })

        processor.add_or_update_row('1m', row_without_time)
        df = processor.get_all_rows('1m')

        # Verify no time index processing
        assert df.index.name != 'time'
        assert len(df) == 1
        assert 'close' in df.columns

    def test_process_backtest_row_no_previous(self, processor, sample_row):
        """
        Test backtesting row processing with no previous row.

        Expected Behavior:
        - process_backtest_row returns the current row (not enriched with previous_* fields)
        - The stored row includes previous_* columns with NaN values
        - Original input row remains unmodified
        - Sets up state for subsequent rows
        """
        original_row = sample_row.copy()
        result = processor.process_backtest_with_indicators_row('1m', sample_row)

        # Verify internal storage has the row
        assert processor.get_row_count('1m') == 1
        stored = processor.get_latest_row('1m')

        # Ensure the original input is unchanged
        pd.testing.assert_series_equal(sample_row, original_row, check_names=False)

        # Ensure returned result is just the input (no previous_* columns expected)
        for col in original_row.index:
            assert col in result.index
            assert result[col] == original_row[col]
            assert f'previous_{col}' not in result.index

        # Ensure stored version has previous_* columns set to NaN
        for col in original_row.index:
            assert col in stored.index
            assert stored[col] == original_row[col]

            prev_col = f'previous_{col}'
            assert prev_col in stored.index
            assert pd.isna(stored[prev_col])


    def test_process_backtest_row_with_previous(self, processor, sample_rows_sequence):
        """
        Test backtesting row processing with previous row data.

        Expected Behavior:
        - Previous row data is added with 'previous_' prefix
        - Current row data is preserved
        - Combined row is stored and returned
        - Previous columns don't include existing 'previous_' columns
        - Essential for indicators needing previous values
        """
        # Add first row
        first_row = sample_rows_sequence[0]
        processor.process_backtest_with_indicators_row('1m', first_row)

        # Process second row (should include previous data)
        second_row = sample_rows_sequence[1]
        result = processor.process_backtest_with_indicators_row('1m', second_row)

        # Verify current row data preserved
        for col in second_row.index:
            assert result[col] == second_row[col]

        # Verify previous row data added
        for col in first_row.index:
            if not col.startswith('previous_'):
                prev_col = f'previous_{col}'
                assert prev_col in result.index
                assert result[prev_col] == first_row[col]

    def test_process_backtest_row_excludes_previous_columns(self, processor):
        """
        Test that previous columns are not re-prefixed in backtesting.

        Expected Behavior:
        - Existing 'previous_' columns are not included in new previous data
        - Prevents recursive prefixing (previous_previous_...)
        - Only original columns are prefixed
        - Maintains clean column structure
        """
        # Create row with existing previous columns
        row_with_previous = pd.Series({
            'time': '2023-01-01 10:00:00',
            'close': 100.0,
            'previous_close': 99.0,  # Existing previous column
            'previous_volume': 900.0
        })

        processor.process_backtest_with_indicators_row('1m', row_with_previous)

        # Add second row
        second_row = pd.Series({
            'time': '2023-01-01 10:01:00',
            'close': 101.0
        })

        result = processor.process_backtest_with_indicators_row('1m', second_row)

        # Verify no double-prefixing
        double_prefixed_cols = [col for col in result.index
                               if col.startswith('previous_previous_')]
        assert len(double_prefixed_cols) == 0

        # Verify only original columns were prefixed
        assert 'previous_close' in result.index
        assert result['previous_close'] == 100.0  # From first row's close

    def test_get_row_count(self, processor, sample_rows_sequence):
        """
        Test row count functionality.

        Expected Behavior:
        - Returns 0 for empty storage
        - Returns correct count as rows are added
        - Count reflects circular buffer behavior
        - Accurate for all timeframes
        """
        # Test empty count
        assert processor.get_row_count('1m') == 0

        # Test count as rows are added
        for i, row in enumerate(sample_rows_sequence):
            processor.add_or_update_row('1m', row)
            assert processor.get_row_count('1m') == i + 1

    def test_clear_timeframe(self, processor, sample_rows_sequence):
        """
        Test clearing specific timeframe.

        Expected Behavior:
        - Removes all rows for specified timeframe
        - Other timeframes remain unaffected
        - Row count becomes 0 for cleared timeframe
        - get_latest_row returns None after clearing
        """
        # Add data to multiple timeframes
        for row in sample_rows_sequence:
            processor.add_or_update_row('1m', row)
            processor.add_or_update_row('5m', row)

        # Clear one timeframe
        processor.clear_timeframe('1m')

        # Verify clearing
        assert processor.get_row_count('1m') == 0
        assert processor.get_latest_row('1m') is None

        # Verify other timeframes unaffected
        assert processor.get_row_count('5m') == len(sample_rows_sequence)

    def test_clear_all(self, processor, sample_rows_sequence):
        """
        Test clearing all timeframes.

        Expected Behavior:
        - Removes all rows from all timeframes
        - All row counts become 0
        - All get_latest_row calls return None
        - Complete reset of processor state
        """
        # Add data to all timeframes
        for tf in processor.get_timeframes():
            for row in sample_rows_sequence:
                processor.add_or_update_row(tf, row)

        # Clear all
        processor.clear_all()

        # Verify all timeframes cleared
        for tf in processor.get_timeframes():
            assert processor.get_row_count(tf) == 0
            assert processor.get_latest_row(tf) is None

    def test_has_sufficient_data(self, processor, sample_rows_sequence):
        """
        Test sufficient data checking.

        Expected Behavior:
        - Returns False when insufficient data
        - Returns True when sufficient data available
        - Handles edge cases (0 rows required, exact match)
        - Validates min_rows parameter
        """
        # Test with no data
        assert not processor.has_sufficient_data('1m', 1)
        assert processor.has_sufficient_data('1m', 0)  # 0 rows required

        # Add some data
        for i, row in enumerate(sample_rows_sequence[:3]):
            processor.add_or_update_row('1m', row)

            # Test various thresholds
            assert processor.has_sufficient_data('1m', i + 1)  # Exact match
            assert processor.has_sufficient_data('1m', i)      # Less than available
            assert not processor.has_sufficient_data('1m', i + 2)  # More than available

    def test_has_sufficient_data_invalid_params(self, processor):
        """
        Test sufficient data checking with invalid parameters.

        Expected Behavior:
        - Raises ValueError for negative min_rows
        - Raises ValueError for unsupported timeframe
        - Clear error messages for debugging
        """
        with pytest.raises(ValueError, match="min_rows must be non-negative"):
            processor.has_sufficient_data('1m', -1)

        with pytest.raises(ValueError, match="Unsupported timeframe"):
            processor.has_sufficient_data('30m', 1)

    def test_get_timeframes_immutability(self, processor):
        """
        Test that get_timeframes returns immutable copy.

        Expected Behavior:
        - Returns copy of timeframes list
        - Modifying returned list doesn't affect processor
        - Defensive programming prevents external modifications
        """
        timeframes = processor.get_timeframes()
        original_timeframes = processor.get_timeframes()

        # Modify returned list
        timeframes.append('30m')

        # Verify processor unaffected
        current_timeframes = processor.get_timeframes()
        assert current_timeframes == original_timeframes
        assert '30m' not in current_timeframes

    def test_repr_string_representation(self, processor):
        """
        Test string representation of processor.

        Expected Behavior:
        - Returns informative string representation
        - Includes key configuration parameters
        - Useful for debugging and logging
        """
        repr_str = repr(processor)
        assert 'RecentRowsProcessor' in repr_str
        assert 'timeframes=' in repr_str
        assert 'max_rows=' in repr_str

    def test_len_total_rows(self, processor, sample_rows_sequence):
        """
        Test total row count across all timeframes.

        Expected Behavior:
        - Returns sum of rows across all timeframes
        - Updates as rows are added to different timeframes
        - Useful for memory usage monitoring
        """
        # Test empty processor
        assert len(processor) == 0

        # Add rows to different timeframes
        processor.add_or_update_row('1m', sample_rows_sequence[0])
        assert len(processor) == 1

        processor.add_or_update_row('5m', sample_rows_sequence[1])
        assert len(processor) == 2

        processor.add_or_update_row('1m', sample_rows_sequence[2])
        assert len(processor) == 3

    def test_timestamp_normalization(self, processor):
        """
        Test timestamp normalization for duplicate detection.

        Expected Behavior:
        - Different timestamp formats are normalized correctly
        - String, datetime, and Timestamp objects work
        - Duplicate detection works across formats
        - Consistent behavior regardless of input format
        """
        # Test different timestamp formats
        formats = [
            '2023-01-01 10:00:00',
            pd.Timestamp('2023-01-01 10:00:00'),
            datetime(2023, 1, 1, 10, 0, 0)
        ]

        for i, time_format in enumerate(formats):
            row = pd.Series({
                'time': time_format,
                'close': 100.0 + i
            })

            # Should update same row due to timestamp normalization
            result = processor.add_or_update_row('1m', row)
            if i == 0:
                assert result is False  # First addition
            else:
                assert result is True   # Updates due to same timestamp

        # Verify only one row exists
        assert processor.get_row_count('1m') == 1

    def test_concurrent_timeframe_independence(self, processor, sample_rows_sequence):
        """
        Test that timeframes operate independently.

        Expected Behavior:
        - Operations on one timeframe don't affect others
        - Each timeframe maintains its own storage
        - Circular buffer limits apply per timeframe
        - Complete isolation between timeframes
        """
        # Add different amounts of data to different timeframes
        for i, row in enumerate(sample_rows_sequence):
            if i < 2:
                processor.add_or_update_row('1m', row)
            if i < 4:
                processor.add_or_update_row('5m', row)
            processor.add_or_update_row('15m', row)

        # Verify independent counts
        assert processor.get_row_count('1m') == 2
        assert processor.get_row_count('5m') == 4
        assert processor.get_row_count('15m') == 5
        assert processor.get_row_count('1h') == 0

    @patch('logging.getLogger')
    def test_logging_integration(self, mock_get_logger, sample_timeframes):
        """
        Test logging integration.

        Expected Behavior:
        - Logger is configured during initialization
        - Debug messages are logged for key operations
        - Logger name matches class name
        - Logging doesn't interfere with functionality
        """
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        processor = RecentRowsProcessor(sample_timeframes)

        # Verify logger setup
        mock_get_logger.assert_called_with('RecentRowsProcessor')
        mock_logger.debug.assert_called()

    def test_edge_case_empty_row(self, processor):
        """
        Test handling of empty row.

        Expected Behavior:
        - Empty Series is handled gracefully
        - No timestamp means no duplicate detection
        - Row is stored as-is
        - No errors are raised
        """
        empty_row = pd.Series(dtype=object)

        result = processor.add_or_update_row('1m', empty_row)
        assert result is False  # New row (no timestamp to match)
        assert processor.get_row_count('1m') == 1

    def test_edge_case_duplicate_timestamps_different_data(self, processor):
        """
        Test duplicate timestamps with different data.

        Expected Behavior:
        - Second row with same timestamp updates the first
        - Latest data overwrites previous data
        - Row count remains 1
        - Demonstrates update behavior
        """
        base_row = pd.Series({
            'time': '2023-01-01 10:00:00',
            'close': 100.0,
            'volume': 1000.0
        })

        updated_row = pd.Series({
            'time': '2023-01-01 10:00:00',
            'close': 200.0,  # Different close
            'volume': 2000.0  # Different volume
        })

        # Add first row
        result1 = processor.add_or_update_row('1m', base_row)
        assert result1 is False

        # Update with same timestamp
        result2 = processor.add_or_update_row('1m', updated_row)
        assert result2 is True

        # Verify update
        assert processor.get_row_count('1m') == 1
        latest = processor.get_latest_row('1m')
        assert latest['close'] == 200.0
        assert latest['volume'] == 2000.0


if __name__ == "__main__":
    # Run the tests
    print("🧪 Running RecentRowsProcessor Tests...")
    print("=" * 50)

    # Create test instance
    test_instance = TestRecentRowsProcessor()

    # Sample data
    sample_timeframes = ['1m', '5m', '15m', '1h']
    sample_row = pd.Series({
        'time': '2023-01-01 10:00:00',
        'open': 100.0,
        'high': 105.0,
        'low': 95.0,
        'close': 102.0,
        'volume': 1000.0
    })

    tests_passed = 0
    tests_failed = 0

    # Test methods to run (simplified for demo)
    test_methods = [
        ('Initialization Valid', lambda: test_instance.test_initialization_valid_params(sample_timeframes)),
        ('Add New Row', lambda: test_instance.test_add_or_update_row_new_row(
            RecentRowsProcessor(sample_timeframes), sample_row)),
        ('Get Latest Row Empty', lambda: test_instance.test_get_latest_row_empty_storage(
            RecentRowsProcessor(sample_timeframes))),
        ('Get All Rows Empty', lambda: test_instance.test_get_all_rows_empty_storage(
            RecentRowsProcessor(sample_timeframes))),
        ('Row Count', lambda: test_instance.test_get_row_count(
            RecentRowsProcessor(sample_timeframes), [sample_row])),
        ('Clear Timeframe', lambda: test_instance.test_clear_timeframe(
            RecentRowsProcessor(sample_timeframes), [sample_row])),
        ('Has Sufficient Data', lambda: test_instance.test_has_sufficient_data(
            RecentRowsProcessor(sample_timeframes), [sample_row])),
        ('String Representation', lambda: test_instance.test_repr_string_representation(
            RecentRowsProcessor(sample_timeframes))),
    ]

    for test_name, test_func in test_methods:
        try:
            test_func()
            print(f"✅ {test_name}")
            tests_passed += 1
        except Exception as e:
            print(f"❌ {test_name}: {str(e)}")
            tests_failed += 1

    print("=" * 50)
    print(f"📊 Test Results: {tests_passed} passed, {tests_failed} failed")
    print("🎯 Full test suite requires pytest with proper imports")

    if tests_failed == 0:
        print("🎉 All basic tests passed! The RecentRowsProcessor is well-tested!")
    else:
        print("⚠️  Some tests failed. Check the implementation.")
