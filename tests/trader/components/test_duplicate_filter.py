"""
Unit tests for DuplicateFilter.
"""

import pytest
from unittest.mock import Mock

from app.trader.components.duplicate_filter import DuplicateFilter
from .fixtures import (
    mock_logger, sample_positions, sample_pending_orders, sample_entry_decisions
)


class TestDuplicateFilter:
    """Test cases for DuplicateFilter component."""
    
    def test_init(self, mock_logger):
        """Test DuplicateFilter initialization."""
        duplicate_filter = DuplicateFilter(mock_logger)
        
        assert duplicate_filter.logger == mock_logger
    
    def test_filter_entries_empty_list(self, mock_logger):
        """Test filtering empty entry list."""
        duplicate_filter = DuplicateFilter(mock_logger)
        
        result = duplicate_filter.filter_entries([], [], [])
        
        assert result == []
    
    def test_filter_entries_no_existing_trades(self, mock_logger, sample_entry_decisions):
        """Test filtering with no existing trades."""
        duplicate_filter = DuplicateFilter(mock_logger)
        
        result = duplicate_filter.filter_entries(sample_entry_decisions, [], [])
        
        # All entries should pass through
        assert len(result) == 2
        assert result == sample_entry_decisions
        
        # Should log allowed entries
        assert mock_logger.info.call_count >= 2  # Start message + entries
        allowed_logs = [call for call in mock_logger.info.call_args_list 
                       if "Entry ALLOWED" in str(call)]
        assert len(allowed_logs) == 2
    
    def test_filter_entries_duplicate_in_positions(self, mock_logger, sample_entry_decisions, sample_positions):
        """Test filtering entries that duplicate existing positions."""
        duplicate_filter = DuplicateFilter(mock_logger)
        
        # sample_positions has position with magic=988128682, type=0 (BUY)
        # sample_entry_decisions[0] has magic=988128682, entry_signals="BUY_LIMIT" (type=2)
        # These should NOT be considered duplicates as types differ (0 vs 2)
        
        result = duplicate_filter.filter_entries(sample_entry_decisions, sample_positions, [])
        
        # Should allow both entries as they don't exactly match existing types
        assert len(result) == 2
    
    def test_filter_entries_duplicate_in_pending_orders(self, mock_logger, sample_entry_decisions, sample_pending_orders):
        """Test filtering entries that duplicate existing pending orders."""
        duplicate_filter = DuplicateFilter(mock_logger)
        
        # sample_pending_orders has order with magic=988128682, type=2 (BUY_LIMIT)
        # sample_entry_decisions[0] has magic=988128682, entry_signals="BUY_LIMIT" (type=2)
        # These should be considered duplicates
        
        result = duplicate_filter.filter_entries(sample_entry_decisions, [], sample_pending_orders)
        
        # Should filter out the first entry (duplicate) but keep the second
        assert len(result) == 1
        assert result[0].magic == 988128685  # Second entry
        
        # Should log one blocked and one allowed
        blocked_logs = [call for call in mock_logger.warning.call_args_list 
                       if "Entry BLOCKED" in str(call)]
        assert len(blocked_logs) == 1
        
        allowed_logs = [call for call in mock_logger.info.call_args_list 
                       if "Entry ALLOWED" in str(call)]
        assert len(allowed_logs) == 1
    
    def test_filter_entries_mixed_duplicates(self, mock_logger, sample_positions, sample_pending_orders):
        """Test filtering with duplicates in both positions and pending orders."""
        duplicate_filter = DuplicateFilter(mock_logger)
        
        # Create entry decisions that match existing trades
        from app.strategy_builder.data.dtos import EntryDecision
        from datetime import datetime
        
        entries = [
            EntryDecision(
                symbol="XAUUSD",
                strategy_name="test-1",
                magic=988128682,  # Matches pending order
                direction="long",
                entry_signals="BUY_LIMIT",  # type=2, matches pending order type
                entry_price=3380.0,
                position_size=0.1,
                stop_loss=Mock(),
                take_profit=Mock(),
                decision_time=datetime.now()
            ),
            EntryDecision(
                symbol="XAUUSD",
                strategy_name="test-2",
                magic=999999999,  # Doesn't match anything
                direction="short",
                entry_signals="SELL_LIMIT",  # type=3
                entry_price=3420.0,
                position_size=0.2,
                stop_loss=Mock(),
                take_profit=Mock(),
                decision_time=datetime.now()
            )
        ]
        
        result = duplicate_filter.filter_entries(entries, sample_positions, sample_pending_orders)
        
        # Should filter out first entry, keep second
        assert len(result) == 1
        assert result[0].magic == 999999999
    
    def test_get_order_type(self, mock_logger):
        """Test order type conversion."""
        duplicate_filter = DuplicateFilter(mock_logger)
        
        assert duplicate_filter._get_order_type("BUY") == 0
        assert duplicate_filter._get_order_type("SELL") == 1
        assert duplicate_filter._get_order_type("BUY_LIMIT") == 2
        assert duplicate_filter._get_order_type("SELL_LIMIT") == 3
        assert duplicate_filter._get_order_type("INVALID") == -1
    
    def test_filter_entries_invalid_signal_type(self, mock_logger):
        """Test filtering with invalid signal type."""
        duplicate_filter = DuplicateFilter(mock_logger)
        
        from app.strategy_builder.data.dtos import EntryDecision
        from datetime import datetime
        
        entries = [
            EntryDecision(
                symbol="XAUUSD",
                strategy_name="test",
                magic=123456789,
                direction="long",
                entry_signals="INVALID_SIGNAL",  # Invalid signal type
                entry_price=3380.0,
                position_size=0.1,
                stop_loss=Mock(),
                take_profit=Mock(),
                decision_time=datetime.now()
            )
        ]
        
        result = duplicate_filter.filter_entries(entries, [], [])
        
        # Should filter out entry with invalid signal type
        assert len(result) == 0
        
        # Should log error
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Unknown entry signal type: INVALID_SIGNAL" in error_call
    
    def test_filter_entries_comprehensive_logging(self, mock_logger, sample_entry_decisions):
        """Test comprehensive logging during filtering."""
        duplicate_filter = DuplicateFilter(mock_logger)
        
        result = duplicate_filter.filter_entries(sample_entry_decisions, [], [])
        
        # Check logging structure
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        
        # Should have start message
        start_logs = [call for call in info_calls if "DUPLICATE FILTER START" in call]
        assert len(start_logs) == 1
        
        # Should have entry count
        count_logs = [call for call in info_calls if "Checking 2 entries" in call]
        assert len(count_logs) == 1
        
        # Should have result summary
        result_logs = [call for call in info_calls if "FILTER RESULT" in call]
        assert len(result_logs) == 1
        
        # Should have individual entry checks
        check_logs = [call for call in info_calls if "Checking entry:" in call]
        assert len(check_logs) == 2
    
    def test_filter_entries_existing_trades_logging(self, mock_logger, sample_positions, sample_pending_orders, sample_entry_decisions):
        """Test logging of existing trades."""
        duplicate_filter = DuplicateFilter(mock_logger)
        
        result = duplicate_filter.filter_entries(sample_entry_decisions, sample_positions, sample_pending_orders)
        
        # Should log existing positions and pending orders
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        
        existing_pos_logs = [call for call in info_calls if "Existing positions" in call]
        assert len(existing_pos_logs) == 1
        
        existing_pending_logs = [call for call in info_calls if "Existing pending" in call]
        assert len(existing_pending_logs) == 1
    
    def test_get_existing_trades(self, mock_logger, sample_positions, sample_pending_orders):
        """Test getting existing trades set."""
        duplicate_filter = DuplicateFilter(mock_logger)
        
        existing = duplicate_filter._get_existing_trades(sample_positions, sample_pending_orders)
        
        # Should contain tuples from both positions and pending orders
        expected_positions = {(988128682, 0), (988128683, 1)}  # From sample_positions
        expected_pending = {(988128682, 2), (988128684, 3)}    # From sample_pending_orders
        expected_all = expected_positions | expected_pending
        
        assert existing == expected_all
    
    def test_filter_against_existing_edge_cases(self, mock_logger):
        """Test edge cases in filtering against existing trades."""
        duplicate_filter = DuplicateFilter(mock_logger)
        
        from app.strategy_builder.data.dtos import EntryDecision
        from datetime import datetime
        
        # Entry with same magic but different type should be allowed
        entry = EntryDecision(
            symbol="XAUUSD",
            strategy_name="test",
            magic=988128682,
            direction="short",  
            entry_signals="SELL_LIMIT",  # type=3, different from existing BUY_LIMIT type=2
            entry_price=3420.0,
            position_size=0.1,
            stop_loss=Mock(),
            take_profit=Mock(),
            decision_time=datetime.now()
        )
        
        existing_trades = {(988128682, 2)}  # Same magic, different type
        existing_positions = set()
        existing_pending = {(988128682, 2)}
        
        result = duplicate_filter._filter_against_existing(
            [entry], existing_trades, existing_positions, existing_pending
        )
        
        # Should allow the entry as types are different (3 vs 2)
        assert len(result) == 1
        assert result[0] == entry