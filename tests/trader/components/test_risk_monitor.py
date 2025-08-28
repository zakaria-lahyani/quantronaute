"""
Unit tests for RiskMonitor.
"""

import pytest
from unittest.mock import Mock

from app.trader.components.risk_monitor import RiskMonitor
from app.trader.components.pnl_calculator import PnLCalculator
from .fixtures import (
    mock_trader, mock_logger, sample_positions, sample_closed_positions
)


class TestRiskMonitor:
    """Test cases for RiskMonitor component."""
    
    def test_init(self, mock_trader, mock_logger):
        """Test RiskMonitor initialization."""
        daily_loss_limit = -1000.0
        pnl_calculator = Mock()
        
        risk_monitor = RiskMonitor(mock_trader, daily_loss_limit, pnl_calculator, mock_logger)
        
        assert risk_monitor.trader == mock_trader
        assert risk_monitor.daily_loss_limit == daily_loss_limit
        assert risk_monitor.pnl_calculator == pnl_calculator
        assert risk_monitor.logger == mock_logger
    
    def test_init_with_default_pnl_calculator(self, mock_trader):
        """Test RiskMonitor initialization with default PnL calculator."""
        daily_loss_limit = -1000.0
        
        risk_monitor = RiskMonitor(mock_trader, daily_loss_limit)
        
        assert isinstance(risk_monitor.pnl_calculator, PnLCalculator)
    
    def test_check_catastrophic_loss_limit_within_limits(self, mock_trader, mock_logger, sample_positions, sample_closed_positions):
        """Test risk check when PnL is within acceptable limits."""
        daily_loss_limit = -1000.0  # Loss limit of $1000
        pnl_calculator = Mock()
        pnl_calculator.calculate_total_daily_pnl.return_value = -500.0  # Loss of $500, within limit
        
        risk_monitor = RiskMonitor(mock_trader, daily_loss_limit, pnl_calculator, mock_logger)
        
        result = risk_monitor.check_catastrophic_loss_limit(sample_positions, sample_closed_positions)
        
        assert result is False  # No limit breach
        
        # Should call PnL calculator
        pnl_calculator.calculate_total_daily_pnl.assert_called_once_with(sample_closed_positions, sample_positions)
        
        # Should log risk check info
        mock_logger.info.assert_called_once()
        info_call = mock_logger.info.call_args[0][0]
        assert "Risk Check" in info_call
        assert "Daily PnL=-500.00" in info_call
        assert "Ratio=0.500" in info_call
        
        # Should not call emergency shutdown
        mock_trader.close_all_open_position.assert_not_called()
        mock_trader.cancel_all_pending_orders.assert_not_called()
    
    def test_check_catastrophic_loss_limit_breach(self, mock_trader, mock_logger, sample_positions, sample_closed_positions):
        """Test risk check when catastrophic loss limit is breached."""
        daily_loss_limit = -500.0   # Loss limit of $500
        pnl_calculator = Mock()
        pnl_calculator.calculate_total_daily_pnl.return_value = -800.0  # Loss of $800, exceeds limit
        
        risk_monitor = RiskMonitor(mock_trader, daily_loss_limit, pnl_calculator, mock_logger)
        
        result = risk_monitor.check_catastrophic_loss_limit(sample_positions, sample_closed_positions)
        
        assert result is True  # Limit breached
        
        # Should log critical alert
        mock_logger.critical.assert_called()
        critical_calls = [str(call) for call in mock_logger.critical.call_args_list]
        assert any("CATASTROPHIC LOSS LIMIT BREACHED" in call for call in critical_calls)
        
        # Should execute emergency shutdown
        mock_trader.close_all_open_position.assert_called_once()
        mock_trader.cancel_all_pending_orders.assert_called_once()
        
        # Should log shutdown steps
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        assert any("Executing emergency shutdown" in call for call in warning_calls)
        assert any("All open positions closed" in call for call in warning_calls)
        assert any("All pending orders cancelled" in call for call in warning_calls)
    
    def test_check_catastrophic_loss_limit_exact_breach(self, mock_trader, mock_logger):
        """Test risk check when PnL exactly equals the loss limit."""
        daily_loss_limit = -1000.0
        pnl_calculator = Mock()
        pnl_calculator.calculate_total_daily_pnl.return_value = -1000.0  # Exactly at limit
        
        risk_monitor = RiskMonitor(mock_trader, daily_loss_limit, pnl_calculator, mock_logger)
        
        result = risk_monitor.check_catastrophic_loss_limit([], [])
        
        # Ratio = -1000 / -1000 = 1.0, which is NOT < -1.0, so no breach
        assert result is False
        
        # Should not trigger emergency shutdown
        mock_trader.close_all_open_position.assert_not_called()
    
    def test_check_catastrophic_loss_limit_positive_pnl(self, mock_trader, mock_logger):
        """Test risk check with positive PnL (profit)."""
        daily_loss_limit = -1000.0
        pnl_calculator = Mock()
        pnl_calculator.calculate_total_daily_pnl.return_value = 500.0  # Profit
        
        risk_monitor = RiskMonitor(mock_trader, daily_loss_limit, pnl_calculator, mock_logger)
        
        result = risk_monitor.check_catastrophic_loss_limit([], [])
        
        # Ratio = 500 / -1000 = -0.5, which is NOT < -1.0, so no breach
        assert result is False
        
        # Should log positive ratio
        mock_logger.info.assert_called_once()
        info_call = mock_logger.info.call_args[0][0]
        assert "Ratio=-0.500" in info_call
    
    def test_execute_emergency_shutdown_success(self, mock_trader, mock_logger):
        """Test successful emergency shutdown execution."""
        daily_loss_limit = -500.0
        pnl_calculator = Mock()
        pnl_calculator.calculate_total_daily_pnl.return_value = -1000.0
        
        risk_monitor = RiskMonitor(mock_trader, daily_loss_limit, pnl_calculator, mock_logger)
        
        # Trigger emergency shutdown
        risk_monitor.check_catastrophic_loss_limit([], [])
        
        # Verify shutdown sequence
        mock_trader.close_all_open_position.assert_called_once()
        mock_trader.cancel_all_pending_orders.assert_called_once()
        
        # Verify logging sequence
        warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
        critical_calls = [call[0][0] for call in mock_logger.critical.call_args_list]
        
        assert "Executing emergency shutdown..." in warning_calls
        assert "All open positions closed" in warning_calls
        assert "All pending orders cancelled" in warning_calls
        assert "Emergency shutdown completed" in critical_calls
    
    def test_execute_emergency_shutdown_with_exception(self, mock_trader, mock_logger):
        """Test emergency shutdown when trader methods raise exceptions."""
        daily_loss_limit = -500.0
        pnl_calculator = Mock()
        pnl_calculator.calculate_total_daily_pnl.return_value = -1000.0
        
        # Make trader methods raise exceptions
        mock_trader.close_all_open_position.side_effect = Exception("Close positions failed")
        mock_trader.cancel_all_pending_orders.side_effect = Exception("Cancel orders failed")
        
        risk_monitor = RiskMonitor(mock_trader, daily_loss_limit, pnl_calculator, mock_logger)
        
        # Should not raise exception, but log error
        result = risk_monitor.check_catastrophic_loss_limit([], [])
        
        assert result is True  # Still considered a breach
        
        # Should log error
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Error during emergency shutdown" in error_call
    
    def test_get_risk_metrics(self, mock_trader, mock_logger, sample_positions, sample_closed_positions):
        """Test getting comprehensive risk metrics."""
        daily_loss_limit = -1000.0
        pnl_calculator = Mock()
        pnl_calculator.calculate_total_daily_pnl.return_value = -300.0
        pnl_calculator.calculate_floating_pnl.return_value = -150.0
        pnl_calculator.calculate_closed_pnl.return_value = -150.0
        
        risk_monitor = RiskMonitor(mock_trader, daily_loss_limit, pnl_calculator, mock_logger)
        
        metrics = risk_monitor.get_risk_metrics(sample_positions, sample_closed_positions)
        
        expected_metrics = {
            'total_daily_pnl': -300.0,
            'daily_loss_limit': -1000.0,
            'loss_ratio': 0.3,  # -300 / -1000 = 0.3
            'open_positions_count': 2,  # len(sample_positions)
            'floating_pnl': -150.0,
            'closed_pnl': -150.0
        }
        
        assert metrics == expected_metrics
        
        # Should call all PnL calculation methods
        pnl_calculator.calculate_total_daily_pnl.assert_called_once_with(sample_closed_positions, sample_positions)
        pnl_calculator.calculate_floating_pnl.assert_called_once_with(sample_positions)
        pnl_calculator.calculate_closed_pnl.assert_called_once_with(sample_closed_positions)
    
    def test_get_risk_metrics_zero_loss_limit(self, mock_trader, mock_logger):
        """Test risk metrics with zero loss limit (edge case)."""
        daily_loss_limit = 0.0  # Edge case
        pnl_calculator = Mock()
        pnl_calculator.calculate_total_daily_pnl.return_value = -100.0
        pnl_calculator.calculate_floating_pnl.return_value = -50.0
        pnl_calculator.calculate_closed_pnl.return_value = -50.0
        
        risk_monitor = RiskMonitor(mock_trader, daily_loss_limit, pnl_calculator, mock_logger)
        
        metrics = risk_monitor.get_risk_metrics([], [])
        
        # Loss ratio should be 0 when loss limit is 0 (to avoid division by zero)
        assert metrics['loss_ratio'] == 0
        assert metrics['daily_loss_limit'] == 0.0
    
    def test_risk_monitor_integration_with_real_pnl_calculator(self, mock_trader, mock_logger, sample_positions, sample_closed_positions):
        """Test RiskMonitor with real PnLCalculator integration."""
        daily_loss_limit = -100.0  # Set low limit to trigger breach
        
        # Use real PnL calculator (no mock)
        risk_monitor = RiskMonitor(mock_trader, daily_loss_limit, logger=mock_logger)
        
        result = risk_monitor.check_catastrophic_loss_limit(sample_positions, sample_closed_positions)
        
        # With sample data, total PnL should be positive (109.0), so no breach
        assert result is False
        
        # But let's test with modified data that would cause a breach
        from app.clients.mt5.models.response import Position
        
        losing_positions = [
            Position(
                ticket=99999, symbol="XAUUSD", type=0, magic=123,
                profit=-200.0, swap=-10.0, volume=0.1,  # Large loss
                price_open=3400.0, price_current=3350.0,
                sl=3300.0, tp=3450.0, time=123456, comment=""
            )
        ]
        
        result_with_loss = risk_monitor.check_catastrophic_loss_limit(losing_positions, [])
        
        # Should breach limit: (-200 + -10) = -210, which is > -100 limit
        assert result_with_loss is True
        
        # Should trigger shutdown
        mock_trader.close_all_open_position.assert_called()
        mock_trader.cancel_all_pending_orders.assert_called()
    
    def test_risk_thresholds_boundary_conditions(self, mock_trader, mock_logger):
        """Test various boundary conditions for risk thresholds."""
        test_cases = [
            # (loss_limit, actual_pnl, should_breach)
            (-1000.0, -999.0, False),    # Just within limit
            (-1000.0, -1000.0, False),   # Exactly at limit  
            (-1000.0, -1001.0, True),    # Just over limit
            (-100.0, -200.0, True),      # Double the limit
            (-500.0, 100.0, False),      # Profitable
            (-1.0, -1.1, True),          # Small amounts
        ]
        
        for loss_limit, actual_pnl, should_breach in test_cases:
            pnl_calculator = Mock()
            pnl_calculator.calculate_total_daily_pnl.return_value = actual_pnl
            
            risk_monitor = RiskMonitor(mock_trader, loss_limit, pnl_calculator, mock_logger)
            
            result = risk_monitor.check_catastrophic_loss_limit([], [])
            
            assert result == should_breach, f"Failed for limit={loss_limit}, pnl={actual_pnl}"
            
            # Reset mocks for next iteration
            mock_trader.reset_mock()
            mock_logger.reset_mock()