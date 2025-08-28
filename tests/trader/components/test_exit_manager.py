"""
Unit tests for ExitManager.
"""

import pytest
from unittest.mock import Mock

from app.trader.components.exit_manager import ExitManager
from .fixtures import (
    mock_trader, mock_logger, sample_positions, sample_exit_decisions
)


class TestExitManager:
    """Test cases for ExitManager component."""
    
    def test_init(self, mock_trader, mock_logger):
        """Test ExitManager initialization."""
        exit_manager = ExitManager(mock_trader, mock_logger)
        
        assert exit_manager.trader == mock_trader
        assert exit_manager.logger == mock_logger
    
    def test_process_exits_empty_list(self, mock_trader, mock_logger, sample_positions):
        """Test processing empty exit list."""
        exit_manager = ExitManager(mock_trader, mock_logger)
        
        exit_manager.process_exits([], sample_positions)
        
        # Should not call any trader methods
        mock_trader.close_open_position.assert_not_called()
        mock_logger.debug.assert_called_once_with("No exit signals to process")
    
    def test_process_exits_successful_long_exit(self, mock_trader, mock_logger, sample_positions, sample_exit_decisions):
        """Test successful long position exit."""
        exit_manager = ExitManager(mock_trader, mock_logger)
        
        # Get the long exit decision (first one)
        long_exit = sample_exit_decisions[0]  # magic=988128682, direction="long"
        
        exit_manager.process_exits([long_exit], sample_positions)
        
        # Should close the matching long position (ticket=12345, magic=988128682, type=0)
        mock_trader.close_open_position.assert_called_once_with("XAUUSD", 12345)
        
        # Should log the closure
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args[0][0]
        assert "Closed position: ticket=12345" in log_call
        assert "magic=988128682" in log_call
    
    def test_process_exits_successful_short_exit(self, mock_trader, mock_logger, sample_positions, sample_exit_decisions):
        """Test successful short position exit."""
        exit_manager = ExitManager(mock_trader, mock_logger)
        
        # Get the short exit decision (second one)
        short_exit = sample_exit_decisions[1]  # magic=988128683, direction="short"
        
        exit_manager.process_exits([short_exit], sample_positions)
        
        # Should close the matching short position (ticket=12346, magic=988128683, type=1)
        mock_trader.close_open_position.assert_called_once_with("XAUUSD", 12346)
        
        # Should log the closure
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args[0][0]
        assert "Closed position: ticket=12346" in log_call
        assert "magic=988128683" in log_call
    
    def test_process_exits_no_matching_position(self, mock_trader, mock_logger, sample_positions):
        """Test exit with no matching position."""
        exit_manager = ExitManager(mock_trader, mock_logger)
        
        # Create exit decision that doesn't match any position
        from app.strategy_builder.data.dtos import ExitDecision
        from datetime import datetime
        
        non_matching_exit = ExitDecision(
            symbol="XAUUSD",
            strategy_name="non-existing",
            magic=999999999,  # Different magic
            direction="long",
            decision_time=datetime.now()
        )
        
        exit_manager.process_exits([non_matching_exit], sample_positions)
        
        # Should not call close_open_position
        mock_trader.close_open_position.assert_not_called()
        
        # Should log warning
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "No matching positions found" in warning_call
        assert "magic=999999999" in warning_call
    
    def test_process_exits_trader_exception(self, mock_trader, mock_logger, sample_positions, sample_exit_decisions):
        """Test handling trader exceptions during exit."""
        exit_manager = ExitManager(mock_trader, mock_logger)
        
        # Make trader.close_open_position raise an exception
        mock_trader.close_open_position.side_effect = Exception("Trading error")
        
        long_exit = sample_exit_decisions[0]
        exit_manager.process_exits([long_exit], sample_positions)
        
        # Should attempt to close position
        mock_trader.close_open_position.assert_called_once_with("XAUUSD", 12345)
        
        # Should log error
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to close position 12345" in error_call
        assert "Trading error" in error_call
    
    def test_process_exits_multiple_matching_positions(self, mock_trader, mock_logger):
        """Test exit with multiple matching positions (same magic/type)."""
        exit_manager = ExitManager(mock_trader, mock_logger)
        
        # Create multiple positions with same magic and type
        from app.clients.mt5.models.response import Position
        from app.strategy_builder.data.dtos import ExitDecision
        from datetime import datetime
        
        positions = [
            Position(
                ticket=11111, symbol="XAUUSD", type=0, magic=123456789,
                profit=50.0, swap=-1.0, volume=0.1, price_open=3400.0,
                price_current=3410.0, sl=3390.0, tp=3420.0, time=123456, comment=""
            ),
            Position(
                ticket=22222, symbol="XAUUSD", type=0, magic=123456789,
                profit=75.0, swap=-2.0, volume=0.1, price_open=3405.0,
                price_current=3410.0, sl=3395.0, tp=3425.0, time=123457, comment=""
            )
        ]
        
        exit_decision = ExitDecision(
            symbol="XAUUSD",
            strategy_name="test",
            magic=123456789,
            direction="long",
            decision_time=datetime.now()
        )
        
        exit_manager.process_exits([exit_decision], positions)
        
        # Should close both positions
        assert mock_trader.close_open_position.call_count == 2
        mock_trader.close_open_position.assert_any_call("XAUUSD", 11111)
        mock_trader.close_open_position.assert_any_call("XAUUSD", 22222)
        
        # Should log both closures
        assert mock_logger.info.call_count == 2
    
    def test_process_exits_mixed_symbols(self, mock_trader, mock_logger):
        """Test exit with different symbols."""
        exit_manager = ExitManager(mock_trader, mock_logger)
        
        # Create positions with different symbols
        from app.clients.mt5.models.response import Position
        from app.strategy_builder.data.dtos import ExitDecision
        from datetime import datetime
        
        positions = [
            Position(
                ticket=11111, symbol="XAUUSD", type=0, magic=123456789,
                profit=50.0, swap=-1.0, volume=0.1, price_open=3400.0,
                price_current=3410.0, sl=3390.0, tp=3420.0, time=123456, comment=""
            ),
            Position(
                ticket=22222, symbol="EURUSD", type=0, magic=123456789,  # Different symbol
                profit=75.0, swap=-2.0, volume=0.1, price_open=1.0500,
                price_current=1.0510, sl=1.0490, tp=1.0520, time=123457, comment=""
            )
        ]
        
        # Exit decision for XAUUSD only
        exit_decision = ExitDecision(
            symbol="XAUUSD",
            strategy_name="test",
            magic=123456789,
            direction="long",
            decision_time=datetime.now()
        )
        
        exit_manager.process_exits([exit_decision], positions)
        
        # Should only close XAUUSD position
        mock_trader.close_open_position.assert_called_once_with("XAUUSD", 11111)
        
        # Should log one closure
        mock_logger.info.assert_called_once()