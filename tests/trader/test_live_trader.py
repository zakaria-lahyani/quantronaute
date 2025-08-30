"""Unit tests for LiveTrader class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.trader.live_trader import LiveTrader
from app.clients.mt5.models.order import PendingOrder
from app.clients.mt5.models.response import Position, Order, ClosedPosition
from .fixtures import *


class TestLiveTrader:
    """Test cases for LiveTrader class."""

    def test_init(self, mock_mt5_client, mock_logger):
        """Test LiveTrader initialization."""
        trader = LiveTrader(mock_mt5_client, logger=mock_logger)
        
        assert trader.client == mock_mt5_client
        assert trader.logger == mock_logger

    def test_init_without_logger(self, mock_mt5_client):
        """Test LiveTrader initialization without logger."""
        trader = LiveTrader(mock_mt5_client)
        
        assert trader.client == mock_mt5_client
        assert trader.logger is not None

    def test_execute_orders_success(self, mock_mt5_client, sample_entry_decisions):
        """Test successful order execution."""
        mock_mt5_client.orders.create_buy_limit_order.return_value = {"order_id": 123}
        
        trader = LiveTrader(mock_mt5_client)
        results = trader.execute_orders(sample_entry_decisions)
        
        assert len(results) == len(sample_entry_decisions)
        mock_mt5_client.orders.create_buy_limit_order.assert_called()

    def test_execute_orders_exception(self, mock_mt5_client, sample_entry_decisions):
        """Test order execution with exception."""
        mock_mt5_client.orders.create_buy_limit_order.side_effect = Exception("API Error")
        
        trader = LiveTrader(mock_mt5_client)
        results = trader.execute_orders(sample_entry_decisions)
        
        assert len(results) == len(sample_entry_decisions)
        for result in results:
            assert "error" in result

    def test_get_open_positions_success(self, mock_mt5_client, sample_positions):
        """Test getting open positions successfully."""
        mock_mt5_client.positions.get_open_positions.return_value = sample_positions
        
        trader = LiveTrader(mock_mt5_client)
        positions = trader.get_open_positions("XAUUSD")
        
        assert len(positions) == len(sample_positions)
        mock_mt5_client.positions.get_open_positions.assert_called_with("XAUUSD")

    def test_get_open_positions_exception(self, mock_mt5_client):
        """Test getting open positions with exception."""
        mock_mt5_client.positions.get_open_positions.side_effect = Exception("API Error")
        
        trader = LiveTrader(mock_mt5_client)
        positions = trader.get_open_positions("XAUUSD")
        
        assert positions == []

    def test_get_pending_orders_success(self, mock_mt5_client, sample_order):
        """Test getting pending orders successfully."""
        # Mock the Order objects returned by API
        mock_orders = [sample_order]
        mock_mt5_client.orders.get_pending_orders.return_value = mock_orders
        
        trader = LiveTrader(mock_mt5_client)
        orders = trader.get_pending_orders("XAUUSD")
        
        assert len(orders) == 1
        assert isinstance(orders[0], PendingOrder)
        assert orders[0].ticket == sample_order.ticket
        mock_mt5_client.orders.get_pending_orders.assert_called_with("XAUUSD")

    def test_get_pending_orders_volume_conversion(self, mock_mt5_client):
        """Test volume conversion in get_pending_orders."""
        # Create order with volume_current
        order_with_volume_current = Order(
            ticket=123,
            symbol="XAUUSD",
            volume=None,
            volume_current=0.5,
            volume_initial=0.3,
            type=2,
            price_open=2500.0,
            magic=12345
        )
        
        mock_mt5_client.orders.get_pending_orders.return_value = [order_with_volume_current]
        
        trader = LiveTrader(mock_mt5_client)
        orders = trader.get_pending_orders("XAUUSD")
        
        assert orders[0].volume_current == 0.5
        assert orders[0].volume_initial == 0.3

    def test_get_pending_orders_volume_fallback(self, mock_mt5_client):
        """Test volume fallback in get_pending_orders."""
        # Create order without volume_current
        order_without_volume = Order(
            ticket=123,
            symbol="XAUUSD",
            volume=0.2,
            type=2,
            price_open=2500.0,
            magic=12345
        )
        
        mock_mt5_client.orders.get_pending_orders.return_value = [order_without_volume]
        
        trader = LiveTrader(mock_mt5_client)
        orders = trader.get_pending_orders("XAUUSD")
        
        assert orders[0].volume_current == 0.2
        assert orders[0].volume_initial == 0.2

    def test_get_pending_orders_volume_minimum(self, mock_mt5_client):
        """Test minimum volume in get_pending_orders."""
        # Create order with no volume data
        order_no_volume = Order(
            ticket=123,
            symbol="XAUUSD",
            volume=None,
            type=2,
            price_open=2500.0,
            magic=12345
        )
        
        mock_mt5_client.orders.get_pending_orders.return_value = [order_no_volume]
        
        trader = LiveTrader(mock_mt5_client)
        orders = trader.get_pending_orders("XAUUSD")
        
        assert orders[0].volume_current == 0.01  # Minimum volume
        assert orders[0].volume_initial == 0.01

    def test_get_order_type_int(self, mock_mt5_client):
        """Test order type string to int conversion."""
        trader = LiveTrader(mock_mt5_client)
        
        assert trader._get_order_type_int("BUY") == 0
        assert trader._get_order_type_int("SELL") == 1
        assert trader._get_order_type_int("BUY_LIMIT") == 2
        assert trader._get_order_type_int("SELL_LIMIT") == 3
        assert trader._get_order_type_int("BUY_STOP") == 4
        assert trader._get_order_type_int("SELL_STOP") == 5
        assert trader._get_order_type_int("INVALID") == -1

    def test_get_closed_positions_success(self, mock_mt5_client, sample_closed_positions):
        """Test getting closed positions successfully."""
        mock_mt5_client.history.get_closed_positions.return_value = sample_closed_positions
        
        trader = LiveTrader(mock_mt5_client)
        positions = trader.get_closed_positions("2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z")
        
        assert len(positions) == len(sample_closed_positions)
        mock_mt5_client.history.get_closed_positions.assert_called()

    def test_get_closed_positions_exception(self, mock_mt5_client):
        """Test getting closed positions with exception."""
        mock_mt5_client.history.get_closed_positions.side_effect = Exception("API Error")
        
        trader = LiveTrader(mock_mt5_client)
        positions = trader.get_closed_positions("2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z")
        
        assert positions == []

    def test_update_open_position_success(self, mock_mt5_client):
        """Test updating open position successfully."""
        mock_mt5_client.positions.modify_position.return_value = True
        
        trader = LiveTrader(mock_mt5_client)
        result = trader.update_open_position("XAUUSD", 12345, 2490.0, 2520.0)
        
        assert result == {"success": True}
        mock_mt5_client.positions.modify_position.assert_called_with(
            symbol="XAUUSD",
            ticket=12345,
            stop_loss=2490.0,
            take_profit=2520.0
        )

    def test_update_open_position_boolean_false(self, mock_mt5_client):
        """Test updating open position returning False."""
        mock_mt5_client.positions.modify_position.return_value = False
        
        trader = LiveTrader(mock_mt5_client)
        result = trader.update_open_position("XAUUSD", 12345, 2490.0, 2520.0)
        
        assert result == {"error": "Failed to update position"}

    def test_update_open_position_exception(self, mock_mt5_client):
        """Test updating open position with exception."""
        mock_mt5_client.positions.modify_position.side_effect = Exception("API Error")
        
        trader = LiveTrader(mock_mt5_client)
        result = trader.update_open_position("XAUUSD", 12345, 2490.0, 2520.0)
        
        assert "error" in result

    def test_close_open_position_success(self, mock_mt5_client, sample_position):
        """Test closing open position successfully."""
        mock_mt5_client.positions.get_position_by_ticket.return_value = sample_position
        mock_mt5_client.positions.close_position.return_value = True
        
        trader = LiveTrader(mock_mt5_client)
        result = trader.close_open_position("XAUUSD", 12345)
        
        assert result == {"success": True}
        mock_mt5_client.positions.close_position.assert_called_with(
            symbol="XAUUSD",
            ticket=12345,
            volume=sample_position.volume
        )

    def test_close_open_position_not_found(self, mock_mt5_client):
        """Test closing open position that doesn't exist."""
        mock_mt5_client.positions.get_position_by_ticket.return_value = None
        
        trader = LiveTrader(mock_mt5_client)
        result = trader.close_open_position("XAUUSD", 12345)
        
        assert result == {"error": "Position 12345 not found"}

    def test_close_open_position_with_volume(self, mock_mt5_client):
        """Test closing open position with specified volume."""
        mock_mt5_client.positions.close_position.return_value = True
        
        trader = LiveTrader(mock_mt5_client)
        result = trader.close_open_position("XAUUSD", 12345, volume=0.5)
        
        assert result == {"success": True}
        mock_mt5_client.positions.close_position.assert_called_with(
            symbol="XAUUSD",
            ticket=12345,
            volume=0.5
        )

    def test_close_open_position_boolean_false(self, mock_mt5_client, sample_position):
        """Test closing position returning False."""
        mock_mt5_client.positions.get_position_by_ticket.return_value = sample_position
        mock_mt5_client.positions.close_position.return_value = False
        
        trader = LiveTrader(mock_mt5_client)
        result = trader.close_open_position("XAUUSD", 12345)
        
        assert result == {"error": "Failed to close position"}

    def test_close_all_open_position_success(self, mock_mt5_client):
        """Test closing all open positions successfully."""
        mock_mt5_client.positions.close_all_positions.return_value = True
        
        trader = LiveTrader(mock_mt5_client)
        result = trader.close_all_open_position()
        
        assert result == {"success": True}
        mock_mt5_client.positions.close_all_positions.assert_called()

    def test_close_all_open_position_boolean_false(self, mock_mt5_client):
        """Test closing all positions returning False."""
        mock_mt5_client.positions.close_all_positions.return_value = False
        
        trader = LiveTrader(mock_mt5_client)
        result = trader.close_all_open_position()
        
        assert result == {"error": "Failed to close all positions"}

    def test_cancel_pending_orders_success(self, mock_mt5_client):
        """Test canceling pending order successfully."""
        mock_mt5_client.orders.delete_pending_order.return_value = True
        
        trader = LiveTrader(mock_mt5_client)
        result = trader.cancel_pending_orders(54321)
        
        assert result == {"success": True}
        mock_mt5_client.orders.delete_pending_order.assert_called_with(54321)

    def test_cancel_pending_orders_boolean_false(self, mock_mt5_client):
        """Test canceling pending order returning False."""
        mock_mt5_client.orders.delete_pending_order.return_value = False
        
        trader = LiveTrader(mock_mt5_client)
        result = trader.cancel_pending_orders(54321)
        
        assert result == {"error": "Failed to cancel order"}

    def test_cancel_pending_orders_exception(self, mock_mt5_client):
        """Test canceling pending order with exception."""
        mock_mt5_client.orders.delete_pending_order.side_effect = Exception("API Error")
        
        trader = LiveTrader(mock_mt5_client)
        result = trader.cancel_pending_orders(54321)
        
        assert "error" in result

    def test_cancel_all_pending_orders_success(self, mock_mt5_client, sample_pending_orders):
        """Test canceling all pending orders successfully."""
        # Mock getting orders and then canceling them
        trader = LiveTrader(mock_mt5_client)
        trader.get_pending_orders = Mock(return_value=sample_pending_orders)
        trader.cancel_pending_orders = Mock(return_value={"success": True})
        
        results = trader.cancel_all_pending_orders("XAUUSD")
        
        assert len(results) == len(sample_pending_orders)
        trader.get_pending_orders.assert_called_with("XAUUSD")

    def test_cancel_all_pending_orders_no_orders(self, mock_mt5_client):
        """Test canceling all pending orders with no orders."""
        trader = LiveTrader(mock_mt5_client)
        trader.get_pending_orders = Mock(return_value=[])
        
        results = trader.cancel_all_pending_orders("XAUUSD")
        
        assert results == []

    def test_order_creation_buy_limit(self, mock_mt5_client, sample_entry_decision):
        """Test BUY_LIMIT order creation."""
        sample_entry_decision.entry_signals = "BUY_LIMIT"
        mock_mt5_client.orders.create_buy_limit_order.return_value = {"order_id": 123}
        
        trader = LiveTrader(mock_mt5_client)
        results = trader.execute_orders([sample_entry_decision])
        
        mock_mt5_client.orders.create_buy_limit_order.assert_called_once()
        assert len(results) == 1

    def test_order_creation_sell_limit(self, mock_mt5_client, sample_entry_decision):
        """Test SELL_LIMIT order creation."""
        sample_entry_decision.entry_signals = "SELL_LIMIT"
        sample_entry_decision.direction = "short"
        mock_mt5_client.orders.create_sell_limit_order.return_value = {"order_id": 123}
        
        trader = LiveTrader(mock_mt5_client)
        results = trader.execute_orders([sample_entry_decision])
        
        mock_mt5_client.orders.create_sell_limit_order.assert_called_once()
        assert len(results) == 1

    def test_order_creation_buy_stop(self, mock_mt5_client, sample_entry_decision):
        """Test BUY_STOP order creation."""
        sample_entry_decision.entry_signals = "BUY_STOP"
        mock_mt5_client.orders.create_buy_stop_order.return_value = {"order_id": 123}
        
        trader = LiveTrader(mock_mt5_client)
        results = trader.execute_orders([sample_entry_decision])
        
        mock_mt5_client.orders.create_buy_stop_order.assert_called_once()
        assert len(results) == 1

    def test_order_creation_sell_stop(self, mock_mt5_client, sample_entry_decision):
        """Test SELL_STOP order creation."""
        sample_entry_decision.entry_signals = "SELL_STOP"
        sample_entry_decision.direction = "short"
        mock_mt5_client.orders.create_sell_stop_order.return_value = {"order_id": 123}
        
        trader = LiveTrader(mock_mt5_client)
        results = trader.execute_orders([sample_entry_decision])
        
        mock_mt5_client.orders.create_sell_stop_order.assert_called_once()
        assert len(results) == 1

    def test_order_creation_unknown_type(self, mock_mt5_client, sample_entry_decision):
        """Test unknown order type handling."""
        sample_entry_decision.entry_signals = "UNKNOWN_TYPE"
        
        trader = LiveTrader(mock_mt5_client)
        results = trader.execute_orders([sample_entry_decision])
        
        assert len(results) == 1
        assert "error" in results[0]
        assert "Unsupported order type" in results[0]["error"]