"""
Unit tests for OrderExecutor.
"""

import pytest
from unittest.mock import Mock

from app.trader.components.order_executor import OrderExecutor
from .fixtures import (
    mock_trader, mock_logger, sample_entry_decisions, sample_risk_entry
)


class TestOrderExecutor:
    """Test cases for OrderExecutor component."""
    
    def test_init(self, mock_trader, mock_logger):
        """Test OrderExecutor initialization."""
        risk_calculator = Mock()
        symbol = "XAUUSD"
        
        order_executor = OrderExecutor(mock_trader, risk_calculator, symbol, mock_logger)
        
        assert order_executor.trader == mock_trader
        assert order_executor.risk_calculator == risk_calculator
        assert order_executor.symbol == symbol
        assert order_executor.logger == mock_logger
    
    def test_execute_entries_empty_list(self, mock_trader, mock_logger):
        """Test executing empty entry list."""
        risk_calculator = Mock()
        order_executor = OrderExecutor(mock_trader, risk_calculator, "XAUUSD", mock_logger)
        
        order_executor.execute_entries([])
        
        # Should not call any methods
        mock_trader.get_current_price.assert_not_called()
        risk_calculator.process_entries.assert_not_called()
        mock_logger.debug.assert_called_once_with("No entry signals to process")
    
    def test_execute_entries_successful(self, mock_trader, mock_logger, sample_entry_decisions, sample_risk_entry):
        """Test successful entry execution."""
        risk_calculator = Mock()
        risk_calculator.process_entries.return_value = [sample_risk_entry]
        
        order_executor = OrderExecutor(mock_trader, risk_calculator, "XAUUSD", mock_logger)
        
        order_executor.execute_entries(sample_entry_decisions)
        
        # Should get current price
        mock_trader.get_current_price.assert_called_once_with("XAUUSD")
        
        # Should process entries with risk calculator
        risk_calculator.process_entries.assert_called_once_with(
            sample_entry_decisions, 3400.0  # mock_trader returns 3400.0
        )
        
        # Should execute the risk entry
        mock_trader.open_pending_order.assert_called_once_with(trade=sample_risk_entry)
        
        # Should log execution info
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Processing risk entry for group test-gro" in call for call in info_calls)
        assert any("Creating 2 orders" in call for call in info_calls)
    
    def test_execute_entries_multiple_risk_entries(self, mock_trader, mock_logger, sample_entry_decisions):
        """Test executing multiple risk entries."""
        risk_calculator = Mock()
        
        # Create multiple risk entries
        risk_entry_1 = Mock()
        risk_entry_1.group_id = "group-1-12345678"
        risk_entry_1.limit_orders = [{'order': 1}, {'order': 2}]
        
        risk_entry_2 = Mock()
        risk_entry_2.group_id = "group-2-87654321" 
        risk_entry_2.limit_orders = [{'order': 3}]
        
        risk_calculator.process_entries.return_value = [risk_entry_1, risk_entry_2]
        
        # Set up trader responses
        mock_trader.open_pending_order.side_effect = [
            [{'status': 'success', 'ticket': 111}, {'status': 'success', 'ticket': 222}],
            [{'status': 'success', 'ticket': 333}]
        ]
        
        order_executor = OrderExecutor(mock_trader, risk_calculator, "XAUUSD", mock_logger)
        
        order_executor.execute_entries(sample_entry_decisions)
        
        # Should execute both risk entries
        assert mock_trader.open_pending_order.call_count == 2
        mock_trader.open_pending_order.assert_any_call(trade=risk_entry_1)
        mock_trader.open_pending_order.assert_any_call(trade=risk_entry_2)
        
        # Should log both executions
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        # group_id[:8] for "group-1-12345678" = "group-1-"
        # group_id[:8] for "group-2-87654321" = "group-2-"
        group_1_logs = [call for call in info_calls if "group-1-" in call]
        group_2_logs = [call for call in info_calls if "group-2-" in call]
        
        assert len(group_1_logs) >= 1, f"Expected group-1- logs, got: {info_calls}"
        assert len(group_2_logs) >= 1, f"Expected group-2- logs, got: {info_calls}"
    
    def test_execute_risk_entry_trader_exception(self, mock_trader, mock_logger, sample_risk_entry):
        """Test handling trader exceptions during execution."""
        risk_calculator = Mock()
        risk_calculator.process_entries.return_value = [sample_risk_entry]
        
        # Make trader raise exception
        mock_trader.open_pending_order.side_effect = Exception("Trading system error")
        
        order_executor = OrderExecutor(mock_trader, risk_calculator, "XAUUSD", mock_logger)
        
        # Should not raise exception
        order_executor.execute_entries([Mock()])
        
        # Should log error
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to execute risk entry test-gro" in error_call
        assert "Trading system error" in error_call
    
    def test_process_execution_results_all_successful(self, mock_trader, mock_logger, sample_risk_entry):
        """Test processing all successful execution results."""
        risk_calculator = Mock()
        order_executor = OrderExecutor(mock_trader, risk_calculator, "XAUUSD", mock_logger)
        
        # Mock successful results
        results = [
            {'status': 'success', 'ticket': 12345},
            {'status': 'success', 'ticket': 12346}
        ]
        
        order_executor._process_execution_results(results, sample_risk_entry)
        
        # Should log success for all orders
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        success_logs = [call for call in info_calls if "Execution summary: 2/2 orders successful" in call]
        assert len(success_logs) == 1
    
    def test_process_execution_results_mixed_results(self, mock_trader, mock_logger):
        """Test processing mixed execution results (some success, some failure)."""
        risk_calculator = Mock()
        order_executor = OrderExecutor(mock_trader, risk_calculator, "XAUUSD", mock_logger)
        
        # Create risk entry with 3 orders to match 3 results
        from app.trader.risk_manager.models import RiskEntryResult
        
        risk_entry_3_orders = RiskEntryResult(
            group_id="mixed-test-123",
            limit_orders=[
                {'symbol': 'XAUUSD', 'order_type': 'BUY_LIMIT', 'volume': 0.03, 'price': 3380.0},
                {'symbol': 'XAUUSD', 'order_type': 'BUY_LIMIT', 'volume': 0.03, 'price': 3375.0},
                {'symbol': 'XAUUSD', 'order_type': 'BUY_LIMIT', 'volume': 0.04, 'price': 3370.0}
            ],
            total_orders=3,
            total_size=0.1,
            scaled_sizes=[0.03, 0.03, 0.04],
            entry_prices=[3380.0, 3375.0, 3370.0],
            stop_losses=[3370.0, 3365.0, 3360.0],
            group_stop_loss=3360.0,
            stop_loss_mode="group",
            original_risk=150.0,
            take_profit=Mock(),
            calculated_risk=145.0,
            weighted_avg_entry=3375.0,
            stop_calculation_method="price_level",
            strategy_name="mixed-test",
            magic=123456789
        )
        
        results = [
            {'status': 'success', 'ticket': 12345},
            {'error': 'Insufficient margin'},
            {'result': True}  # Alternative success format
        ]
        
        order_executor._process_execution_results(results, risk_entry_3_orders)
        
        # Should log individual results
        error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        
        # Should have error log for failed order
        assert any("Order 2 failed: Insufficient margin" in call for call in error_calls)
        
        # Should have success summary (2 out of 3 successful)
        assert any("Execution summary: 2/3 orders successful" in call for call in info_calls)
    
    def test_process_execution_results_all_failed(self, mock_trader, mock_logger, sample_risk_entry):
        """Test processing all failed execution results."""
        risk_calculator = Mock()
        order_executor = OrderExecutor(mock_trader, risk_calculator, "XAUUSD", mock_logger)
        
        results = [
            {'error': 'Invalid price'},
            {'error': 'Market closed'}
        ]
        
        order_executor._process_execution_results(results, sample_risk_entry)
        
        # Should log all failures
        error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
        assert len(error_calls) == 2
        assert any("Order 1 failed: Invalid price" in call for call in error_calls)
        assert any("Order 2 failed: Market closed" in call for call in error_calls)
        
        # Should show 0 successful
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Execution summary: 0/2 orders successful" in call for call in info_calls)
    
    def test_process_execution_results_non_dict_responses(self, mock_trader, mock_logger, sample_risk_entry):
        """Test processing non-dictionary execution results."""
        risk_calculator = Mock()
        order_executor = OrderExecutor(mock_trader, risk_calculator, "XAUUSD", mock_logger)
        
        results = [
            "Order placed successfully",  # String response
            12345,                        # Numeric response (ticket ID)
            None,                         # None response (failure)
            True                          # Boolean response (success)
        ]
        
        order_executor._process_execution_results(results, sample_risk_entry)
        
        # Should log non-dict responses
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        
        response_logs = [call for call in info_calls if "response:" in call]
        assert len(response_logs) == 4
        
        # Should count non-None/non-empty as successful (3 out of 2 - limited by risk_entry.limit_orders)
        # Note: sample_risk_entry has 2 limit_orders, so denominator is 2, not 4
        summary_logs = [call for call in info_calls if "Execution summary: 3/2" in call]
        assert len(summary_logs) == 1
    
    def test_execute_entries_integration(self, mock_trader, mock_logger):
        """Test full integration of entry execution process."""
        # Set up risk calculator mock
        risk_calculator = Mock()
        
        # Create a realistic risk entry
        from app.trader.risk_manager.models import RiskEntryResult
        
        risk_entry = RiskEntryResult(
            group_id="integration-test-12345678",
            limit_orders=[
                {
                    'symbol': 'XAUUSD',
                    'order_type': 'BUY_LIMIT',
                    'volume': 0.05,
                    'price': 3380.0,
                    'magic': 123456789
                },
                {
                    'symbol': 'XAUUSD', 
                    'order_type': 'BUY_LIMIT',
                    'volume': 0.05,
                    'price': 3375.0,
                    'magic': 123456789
                }
            ],
            total_orders=2,
            total_size=0.1,
            scaled_sizes=[0.05, 0.05],
            entry_prices=[3380.0, 3375.0],
            stop_losses=[3370.0, 3365.0],
            group_stop_loss=3365.0,
            stop_loss_mode="group",
            original_risk=100.0,
            take_profit=Mock(),
            calculated_risk=95.0,
            weighted_avg_entry=3377.5,
            stop_calculation_method="price_level",
            strategy_name="integration-test",
            magic=123456789
        )
        
        risk_calculator.process_entries.return_value = [risk_entry]
        
        # Set up trader mock responses
        mock_trader.get_current_price.return_value = 3400.0
        mock_trader.open_pending_order.return_value = [
            {'status': 'success', 'ticket': 111111},
            {'status': 'success', 'ticket': 222222}
        ]
        
        # Create order executor and sample entry
        order_executor = OrderExecutor(mock_trader, risk_calculator, "XAUUSD", mock_logger)
        
        from app.strategy_builder.data.dtos import EntryDecision
        from datetime import datetime
        
        entry = EntryDecision(
            symbol="XAUUSD",
            strategy_name="integration-test",
            magic=123456789,
            direction="long",
            entry_signals="BUY_LIMIT",
            entry_price=3380.0,
            position_size=0.1,
            stop_loss=Mock(),
            take_profit=Mock(),
            decision_time=datetime.now()
        )
        
        # Execute the entry
        order_executor.execute_entries([entry])
        
        # Verify complete execution flow
        mock_trader.get_current_price.assert_called_once_with("XAUUSD")
        risk_calculator.process_entries.assert_called_once_with([entry], 3400.0)
        mock_trader.open_pending_order.assert_called_once_with(trade=risk_entry)
        
        # Verify logging
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        
        # Should log processing info (group_id[:8] = "integrat")
        assert any("Processing risk entry for group integrat" in call for call in info_calls)
        assert any("Creating 2 orders" in call for call in info_calls)
        
        # Should log execution summary
        assert any("Execution summary: 2/2 orders successful" in call for call in info_calls)
    
    def test_execute_entries_with_different_symbols(self, mock_trader, mock_logger):
        """Test that executor only gets price for its configured symbol."""
        risk_calculator = Mock() 
        risk_calculator.process_entries.return_value = []
        
        # Create executor for EURUSD
        order_executor = OrderExecutor(mock_trader, risk_calculator, "EURUSD", mock_logger)
        
        # Execute with any entry (symbol doesn't matter for price fetching)
        order_executor.execute_entries([Mock()])
        
        # Should get price for configured symbol, not entry symbol
        mock_trader.get_current_price.assert_called_once_with("EURUSD")
    
    def test_execute_risk_entry_logging_precision(self, mock_trader, mock_logger):
        """Test precise logging of risk entry details."""
        risk_calculator = Mock()
        order_executor = OrderExecutor(mock_trader, risk_calculator, "XAUUSD", mock_logger)
        
        # Create risk entry with specific group ID
        from app.trader.risk_manager.models import RiskEntryResult
        
        risk_entry = RiskEntryResult(
            group_id="very-long-group-id-1234567890abcdef",
            limit_orders=[{'order': 1}],  # Single order
            total_orders=1,
            total_size=0.1,
            scaled_sizes=[0.1],
            entry_prices=[3400.0],
            stop_losses=[3390.0],
            group_stop_loss=3390.0,
            stop_loss_mode="group",
            original_risk=100.0,
            take_profit=Mock(),
            calculated_risk=95.0,
            weighted_avg_entry=3400.0,
            stop_calculation_method="price_level",
            strategy_name="precision-test",
            magic=123456789
        )
        
        mock_trader.open_pending_order.return_value = [{'status': 'success'}]
        
        order_executor._execute_risk_entry(risk_entry)
        
        # Should log truncated group ID (first 8 characters)
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        
        group_logs = [call for call in info_calls if "very-lon" in call]  # First 8 chars
        assert len(group_logs) >= 1
        
        order_count_logs = [call for call in info_calls if "Creating 1 orders" in call]
        assert len(order_count_logs) == 1