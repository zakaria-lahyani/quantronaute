"""
Unit tests for PnLCalculator.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from app.trader.components.pnl_calculator import PnLCalculator
from .fixtures import (
    mock_logger, sample_positions, sample_closed_positions
)


class TestPnLCalculator:
    """Test cases for PnLCalculator component."""
    
    def test_init(self, mock_logger):
        """Test PnLCalculator initialization."""
        pnl_calculator = PnLCalculator(mock_logger)
        
        assert pnl_calculator.logger == mock_logger
    
    def test_calculate_closed_pnl_empty_list(self, mock_logger):
        """Test calculating PnL with empty closed positions list."""
        pnl_calculator = PnLCalculator(mock_logger)
        
        result = pnl_calculator.calculate_closed_pnl([])
        
        assert result == 0.0
    
    def test_calculate_closed_pnl_with_positions(self, mock_logger, sample_closed_positions):
        """Test calculating PnL with closed positions."""
        pnl_calculator = PnLCalculator(mock_logger)
        
        result = pnl_calculator.calculate_closed_pnl(sample_closed_positions)
        
        # Calculate expected PnL
        # Position 1: profit=150.0, commission=-3.0, swap=-1.0 = 146.0
        # Position 2: profit=-75.0, commission=-3.0, swap=-2.0 = -80.0
        # Total: 146.0 + (-80.0) = 66.0
        expected_pnl = 66.0
        
        assert result == expected_pnl
        
        # Should log debug information
        mock_logger.debug.assert_called_once()
        debug_call = mock_logger.debug.call_args[0][0]
        assert "Closed PnL" in debug_call
        assert "total=66.00" in debug_call
    
    def test_calculate_floating_pnl_empty_list(self, mock_logger):
        """Test calculating floating PnL with empty positions list."""
        pnl_calculator = PnLCalculator(mock_logger)
        
        result = pnl_calculator.calculate_floating_pnl([])
        
        assert result == 0.0
    
    def test_calculate_floating_pnl_with_positions(self, mock_logger, sample_positions):
        """Test calculating floating PnL with open positions."""
        pnl_calculator = PnLCalculator(mock_logger)
        
        result = pnl_calculator.calculate_floating_pnl(sample_positions)
        
        # Calculate expected floating PnL
        # Position 1: profit=100.0, swap=-5.0 = 95.0
        # Position 2: profit=-50.0, swap=-2.0 = -52.0
        # Total: 95.0 + (-52.0) = 43.0
        expected_pnl = 43.0
        
        assert result == expected_pnl
        
        # Should log debug information
        mock_logger.debug.assert_called_once()
        debug_call = mock_logger.debug.call_args[0][0]
        assert "Floating PnL" in debug_call
        assert "total=43.00" in debug_call
    
    def test_calculate_total_daily_pnl(self, mock_logger, sample_positions, sample_closed_positions):
        """Test calculating total daily PnL."""
        pnl_calculator = PnLCalculator(mock_logger)
        
        result = pnl_calculator.calculate_total_daily_pnl(sample_closed_positions, sample_positions)
        
        # Expected: closed_pnl (66.0) + floating_pnl (43.0) = 109.0
        expected_total = 109.0
        
        assert result == expected_total
        
        # Should log info with summary
        mock_logger.info.assert_called_once()
        info_call = mock_logger.info.call_args[0][0]
        assert "Daily PnL Summary" in info_call
        assert "closed=66.00" in info_call
        assert "floating=43.00" in info_call
        assert "total=109.00" in info_call
    
    def test_calculate_closed_pnl_negative_values(self, mock_logger):
        """Test calculating closed PnL with negative values."""
        pnl_calculator = PnLCalculator(mock_logger)
        
        from app.clients.mt5.models.history import ClosedPosition
        
        negative_positions = [
            ClosedPosition(
                ticket=99999,
                symbol="XAUUSD",
                type=0,
                magic=123456,
                profit=-200.0,  # Large loss
                commission=-5.0,
                swap=-3.0,
                volume=0.5,
                price=3360.0,  # Close price
                time=datetime(2025, 1, 15, 10, 0, 0),
                order=99999,
                position_id=99999,
                external_id="",
                comment="",
                fee=0.0,
                reason=0,
                entry=0,
                time_msc=1234567900000
            )
        ]
        
        result = pnl_calculator.calculate_closed_pnl(negative_positions)
        
        # Expected: -200.0 + (-5.0) + (-3.0) = -208.0
        expected_pnl = -208.0
        
        assert result == expected_pnl
    
    def test_calculate_floating_pnl_negative_values(self, mock_logger):
        """Test calculating floating PnL with negative values."""
        pnl_calculator = PnLCalculator(mock_logger)
        
        from app.clients.mt5.models.response import Position
        
        negative_positions = [
            Position(
                ticket=88888,
                symbol="XAUUSD",
                type=1,  # SELL
                magic=123456,
                profit=-150.0,  # Loss
                swap=-10.0,     # Negative swap
                volume=0.3,
                price_open=3380.0,
                price_current=3395.0,
                sl=3400.0,
                tp=3360.0,
                time=1234567890,
                comment=""
            )
        ]
        
        result = pnl_calculator.calculate_floating_pnl(negative_positions)
        
        # Expected: -150.0 + (-10.0) = -160.0
        expected_pnl = -160.0
        
        assert result == expected_pnl
    
    def test_calculate_pnl_zero_values(self, mock_logger):
        """Test calculating PnL with zero values."""
        pnl_calculator = PnLCalculator(mock_logger)
        
        from app.clients.mt5.models.history import ClosedPosition
        
        zero_positions = [
            ClosedPosition(
                ticket=77777,
                symbol="XAUUSD",
                type=0,
                magic=123456,
                profit=0.0,
                commission=0.0,
                swap=0.0,
                volume=0.1,
                price=3400.0,  # Close price (no price change)
                time=datetime(2025, 1, 15, 10, 0, 0),
                order=77777,
                position_id=77777,
                external_id="",
                comment="",
                fee=0.0,
                reason=0,
                entry=0,
                time_msc=1234567891000
            )
        ]
        
        result = pnl_calculator.calculate_closed_pnl(zero_positions)
        
        assert result == 0.0
    
    def test_calculate_pnl_precision(self, mock_logger):
        """Test PnL calculation precision with fractional values."""
        pnl_calculator = PnLCalculator(mock_logger)
        
        from app.clients.mt5.models.history import ClosedPosition
        
        precise_positions = [
            ClosedPosition(
                ticket=66666,
                symbol="XAUUSD",
                type=0,
                magic=123456,
                profit=123.456789,
                commission=-2.123456,
                swap=-0.987654,
                volume=0.1,
                price=3412.345,  # Close price
                time=datetime(2025, 1, 15, 10, 0, 0),
                order=66666,
                position_id=66666,
                external_id="",
                comment="",
                fee=0.0,
                reason=0,
                entry=0,
                time_msc=1234567895000
            )
        ]
        
        result = pnl_calculator.calculate_closed_pnl(precise_positions)
        
        # Expected: 123.456789 + (-2.123456) + (-0.987654) = 120.345679
        expected_pnl = 120.345679
        
        assert abs(result - expected_pnl) < 1e-6  # Allow small floating point differences
    
    def test_mixed_profit_loss_scenarios(self, mock_logger):
        """Test mixed profit and loss scenarios."""
        pnl_calculator = PnLCalculator(mock_logger)
        
        from app.clients.mt5.models.history import ClosedPosition
        from app.clients.mt5.models.response import Position
        
        # Mix of profitable and losing closed positions
        mixed_closed = [
            ClosedPosition(
                ticket=11111, symbol="XAUUSD", type=0, magic=111,
                profit=500.0, commission=-5.0, swap=-2.0,
                volume=0.5, price=3350.0,  # Close price
                time=datetime(2025, 1, 15, 10, 0, 0),
                order=11111, position_id=11111, external_id="", comment="",
                fee=0.0, reason=0, entry=0, time_msc=1234567895000
            ),
            ClosedPosition(
                ticket=22222, symbol="XAUUSD", type=1, magic=222,
                profit=-300.0, commission=-3.0, swap=-1.0,
                volume=0.3, price=3430.0,  # Close price
                time=datetime(2025, 1, 15, 10, 5, 0),
                order=22222, position_id=22222, external_id="", comment="",
                fee=0.0, reason=0, entry=0, time_msc=1234567905000
            )
        ]
        
        # Mix of profitable and losing open positions
        mixed_open = [
            Position(
                ticket=33333, symbol="XAUUSD", type=0, magic=333,
                profit=200.0, swap=-3.0, volume=0.2,
                price_open=3350.0, price_current=3400.0,
                sl=3330.0, tp=3420.0, time=1234567910, comment=""
            ),
            Position(
                ticket=44444, symbol="XAUUSD", type=1, magic=444,
                profit=-100.0, swap=-2.0, volume=0.1,
                price_open=3380.0, price_current=3390.0,
                sl=3400.0, tp=3360.0, time=1234567915, comment=""
            )
        ]
        
        closed_pnl = pnl_calculator.calculate_closed_pnl(mixed_closed)
        floating_pnl = pnl_calculator.calculate_floating_pnl(mixed_open)
        total_pnl = pnl_calculator.calculate_total_daily_pnl(mixed_closed, mixed_open)
        
        # Closed: (500-5-2) + (-300-3-1) = 493 + (-304) = 189
        assert closed_pnl == 189.0
        
        # Floating: (200-3) + (-100-2) = 197 + (-102) = 95
        assert floating_pnl == 95.0
        
        # Total: 189 + 95 = 284
        assert total_pnl == 284.0