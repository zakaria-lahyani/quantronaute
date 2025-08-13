"""
Unit tests for PositionsClient class.
"""

import pytest
from unittest.mock import Mock, patch

from app.clients.mt5.api.positions import PositionsClient
from app.clients.mt5.models import Position, PositionUpdateRequest, PositionCloseRequest, CloseAllPositionsRequest
from app.clients.mt5.exceptions import MT5APIError, MT5ValidationError
from app.clients.mt5.utils import validate_symbol, validate_ticket


class TestPositionsClient:
    """Test PositionsClient class."""

    def test_initialization(self):
        """Test PositionsClient initialization."""
        client = PositionsClient("http://localhost:8000")
        
        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 30.0

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_get_open_positions(self, mock_get):
        """Test get_open_positions method."""
        mock_positions_data = [
            {
                "ticket": 123456789,
                "symbol": "EURUSD",
                "volume": 0.1,
                "type": 0,
                "price_open": 1.1000,
                "price_current": 1.1015,
                "profit": 15.0,
                "swap": 0.0,
                "commission": -0.70
            },
            {
                "ticket": 987654321,
                "symbol": "GBPUSD",
                "volume": 0.05,
                "type": 1,
                "price_open": 1.2500,
                "price_current": 1.2485,
                "profit": 7.5,
                "swap": 0.0,
                "commission": -0.35
            }
        ]
        mock_get.return_value = mock_positions_data
        
        client = PositionsClient("http://localhost:8000")
        result = client.get_open_positions()
        
        mock_get.assert_called_once_with("positions")
        assert len(result) == 2
        assert all(isinstance(pos, Position) for pos in result)
        assert result[0].ticket == 123456789
        assert result[0].symbol == "EURUSD"
        assert result[1].ticket == 987654321
        assert result[1].symbol == "GBPUSD"

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_get_open_positions_empty(self, mock_get):
        """Test get_open_positions with no positions."""
        mock_get.return_value = []
        
        client = PositionsClient("http://localhost:8000")
        result = client.get_open_positions()
        
        mock_get.assert_called_once_with("positions")
        assert result == []

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_get_open_positions_none_response(self, mock_get):
        """Test get_open_positions with None response."""
        mock_get.return_value = None
        
        client = PositionsClient("http://localhost:8000")
        result = client.get_open_positions()
        
        mock_get.assert_called_once_with("positions")
        assert result == []

    @patch('app.clients.mt5.api.positions.validate_symbol')
    @patch('app.clients.mt5.base.BaseClient.get')
    def test_get_positions_by_symbol(self, mock_get, mock_validate):
        """Test get_positions_by_symbol method."""
        mock_validate.return_value = "EURUSD"
        mock_positions_data = [
            {
                "ticket": 123456789,
                "symbol": "EURUSD",
                "volume": 0.1,
                "type": 0,
                "price_open": 1.1000,
                "price_current": 1.1015,
                "profit": 15.0,
                "swap": 0.0,
                "commission": -0.70
            }
        ]
        mock_get.return_value = mock_positions_data
        
        client = PositionsClient("http://localhost:8000")
        result = client.get_positions_by_symbol("eurusd")
        
        mock_validate.assert_called_once_with("eurusd")
        mock_get.assert_called_once_with("positions/EURUSD")
        assert len(result) == 1
        assert isinstance(result[0], Position)
        assert result[0].symbol == "EURUSD"

    @patch('app.clients.mt5.api.positions.validate_ticket')
    @patch('app.clients.mt5.base.BaseClient.get')
    def test_get_position_by_ticket(self, mock_get, mock_validate):
        """Test get_position_by_ticket method."""
        mock_validate.return_value = 123456789
        mock_position_data = {
            "ticket": 123456789,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": 0,
            "price_open": 1.1000,
            "price_current": 1.1015,
            "profit": 15.0,
            "swap": 0.0,
            "commission": -0.70
        }
        mock_get.return_value = mock_position_data
        
        client = PositionsClient("http://localhost:8000")
        result = client.get_position_by_ticket(123456789)
        
        mock_validate.assert_called_once_with(123456789)
        mock_get.assert_called_once_with("position/123456789")
        assert isinstance(result, Position)
        assert result.ticket == 123456789
        assert result.symbol == "EURUSD"

    @patch('app.clients.mt5.api.positions.validate_ticket')
    @patch('app.clients.mt5.base.BaseClient.get')
    def test_get_position_by_ticket_list_response(self, mock_get, mock_validate):
        """Test get_position_by_ticket with list response."""
        mock_validate.return_value = 123456789
        mock_position_data = [{
            "ticket": 123456789,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": 0,
            "price_open": 1.1000,
            "price_current": 1.1015,
            "profit": 15.0,
            "swap": 0.0,
            "commission": -0.70
        }]
        mock_get.return_value = mock_position_data
        
        client = PositionsClient("http://localhost:8000")
        result = client.get_position_by_ticket(123456789)
        
        assert isinstance(result, Position)
        assert result.ticket == 123456789

    @patch('app.clients.mt5.api.positions.validate_ticket')
    @patch('app.clients.mt5.base.BaseClient.get')
    def test_get_position_by_ticket_not_found(self, mock_get, mock_validate):
        """Test get_position_by_ticket when position not found."""
        mock_validate.return_value = 123456789
        mock_get.return_value = []
        
        client = PositionsClient("http://localhost:8000")
        result = client.get_position_by_ticket(123456789)
        
        assert result is None

    @patch('app.clients.mt5.api.positions.validate_symbol')
    @patch('app.clients.mt5.api.positions.validate_ticket')
    @patch('app.clients.mt5.base.BaseClient.post')
    def test_modify_position(self, mock_post, mock_validate_ticket, mock_validate_symbol):
        """Test modify_position method."""
        mock_validate_symbol.return_value = "EURUSD"
        mock_validate_ticket.return_value = 123456789
        mock_post.return_value = {"success": True, "message": "Position modified"}
        
        client = PositionsClient("http://localhost:8000")
        result = client.modify_position(
            symbol="eurusd",
            ticket=123456789,
            stop_loss=1.0950,
            take_profit=1.1100
        )
        
        mock_validate_symbol.assert_called_once_with("eurusd")
        mock_validate_ticket.assert_called_once_with(123456789)
        mock_post.assert_called_once_with(
            "positions/EURUSD/update/123456789",
            json_data={"stop_loss": 1.0950, "take_profit": 1.1100}
        )
        assert result == {"success": True, "message": "Position modified"}

    @patch('app.clients.mt5.api.positions.validate_symbol')
    @patch('app.clients.mt5.api.positions.validate_ticket')
    @patch('app.clients.mt5.base.BaseClient.post')
    def test_modify_position_stop_loss_only(self, mock_post, mock_validate_ticket, mock_validate_symbol):
        """Test modify_position with only stop loss."""
        mock_validate_symbol.return_value = "EURUSD"
        mock_validate_ticket.return_value = 123456789
        mock_post.return_value = {"success": True}
        
        client = PositionsClient("http://localhost:8000")
        result = client.modify_position(
            symbol="EURUSD",
            ticket=123456789,
            stop_loss=1.0950
        )
        
        mock_post.assert_called_once_with(
            "positions/EURUSD/update/123456789",
            json_data={"stop_loss": 1.0950, "take_profit": None}
        )
        assert result["success"] is True

    @patch('app.clients.mt5.api.positions.validate_symbol')
    @patch('app.clients.mt5.api.positions.validate_ticket')
    @patch('app.clients.mt5.base.BaseClient.post')
    def test_modify_position_take_profit_only(self, mock_post, mock_validate_ticket, mock_validate_symbol):
        """Test modify_position with only take profit."""
        mock_validate_symbol.return_value = "EURUSD"
        mock_validate_ticket.return_value = 123456789
        mock_post.return_value = {"success": True}
        
        client = PositionsClient("http://localhost:8000")
        result = client.modify_position(
            symbol="EURUSD",
            ticket=123456789,
            take_profit=1.1100
        )
        
        mock_post.assert_called_once_with(
            "positions/EURUSD/update/123456789",
            json_data={"stop_loss": None, "take_profit": 1.1100}
        )
        assert result["success"] is True

    @patch('app.clients.mt5.api.positions.validate_symbol')
    @patch('app.clients.mt5.api.positions.validate_ticket')
    @patch('app.clients.mt5.base.BaseClient.post')
    def test_close_position(self, mock_post, mock_validate_ticket, mock_validate_symbol):
        """Test close_position method."""
        mock_validate_symbol.return_value = "EURUSD"
        mock_validate_ticket.return_value = 123456789
        mock_post.return_value = {"success": True, "message": "Position closed"}
        
        client = PositionsClient("http://localhost:8000")
        result = client.close_position(
            symbol="eurusd",
            ticket=123456789,
            volume=0.1
        )
        
        mock_validate_symbol.assert_called_once_with("eurusd")
        mock_validate_ticket.assert_called_once_with(123456789)
        mock_post.assert_called_once_with(
            "positions/EURUSD/close/123456789",
            json_data={"volume": 0.1}
        )
        assert result == {"success": True, "message": "Position closed"}

    @patch('app.clients.mt5.base.BaseClient.post')
    def test_close_all_positions(self, mock_post):
        """Test close_all_positions method."""
        mock_post.return_value = {"success": True, "message": "All positions closed"}
        
        client = PositionsClient("http://localhost:8000")
        result = client.close_all_positions()
        
        mock_post.assert_called_once_with(
            "positions/close_all",
            json_data={"symbol": None}
        )
        assert result == {"success": True, "message": "All positions closed"}

    @patch('app.clients.mt5.base.BaseClient.post')
    def test_close_all_positions_by_symbol(self, mock_post):
        """Test close_all_positions with specific symbol."""
        mock_post.return_value = {"success": True, "message": "EURUSD positions closed"}
        
        client = PositionsClient("http://localhost:8000")
        result = client.close_all_positions(symbol="EURUSD")
        
        mock_post.assert_called_once_with(
            "positions/close_all",
            json_data={"symbol": "EURUSD"}
        )
        assert result == {"success": True, "message": "EURUSD positions closed"}

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_api_error_handling(self, mock_get):
        """Test API error handling."""
        mock_get.side_effect = MT5APIError(
            message="Position not found",
            status_code=404,
            error_code="POSITION_NOT_FOUND"
        )
        
        client = PositionsClient("http://localhost:8000")
        
        with pytest.raises(MT5APIError) as exc_info:
            client.get_open_positions()
        
        assert exc_info.value.message == "Position not found"
        assert exc_info.value.status_code == 404
        assert exc_info.value.error_code == "POSITION_NOT_FOUND"

    @patch('app.clients.mt5.api.positions.validate_symbol')
    def test_validation_error_handling(self, mock_validate):
        """Test validation error handling."""
        mock_validate.side_effect = ValueError("Invalid symbol format")
        
        client = PositionsClient("http://localhost:8000")
        
        with pytest.raises(ValueError, match="Invalid symbol format"):
            client.get_positions_by_symbol("invalid_symbol")

    def test_inheritance(self):
        """Test that PositionsClient properly inherits from BaseClient."""
        client = PositionsClient("http://localhost:8000")
        
        # Should have BaseClient attributes
        assert hasattr(client, 'base_url')
        assert hasattr(client, 'timeout')
        assert hasattr(client, 'retry_config')
        assert hasattr(client, 'headers')
        
        # Should have BaseClient methods
        assert hasattr(client, 'get')
        assert hasattr(client, 'post')
        assert hasattr(client, 'put')
        assert hasattr(client, 'delete')
        assert hasattr(client, 'close')

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_position_model_creation(self, mock_get):
        """Test that Position models are created correctly from API data."""
        mock_position_data = {
            "ticket": 123456789,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": 0,  # This should be converted by the model
            "price_open": 1.1000,
            "price_current": 1.1015,
            "profit": 15.0,
            "swap": 0.0,
            "commission": -0.70,
            "comment": "Test position",
            "magic": 12345,
            "sl": 1.0950,
            "tp": 1.1100
        }
        mock_get.return_value = [mock_position_data]
        
        client = PositionsClient("http://localhost:8000")
        result = client.get_open_positions()
        
        assert len(result) == 1
        position = result[0]
        assert isinstance(position, Position)
        
        # Verify all fields are properly set
        assert position.ticket == 123456789
        assert position.symbol == "EURUSD"
        assert position.volume == 0.1
        assert position.type == 0  # Position keeps int type
        assert position.price_open == 1.1000
        assert position.price_current == 1.1015
        assert position.profit == 15.0
        assert position.swap == 0.0
        assert position.commission == -0.70
        assert position.comment == "Test position"
        assert position.magic == 12345
        assert position.sl == 1.0950
        assert position.tp == 1.1100

    @patch('app.clients.mt5.base.BaseClient.post')
    def test_request_models_usage(self, mock_post):
        """Test that request models are properly used and serialized."""
        mock_post.return_value = {"success": True}
        
        client = PositionsClient("http://localhost:8000")
        
        # Test modify_position uses PositionUpdateRequest
        with patch('app.clients.mt5.utils.validate_symbol', return_value="EURUSD"), \
             patch('app.clients.mt5.utils.validate_ticket', return_value=123):
            
            client.modify_position("EURUSD", 123, stop_loss=1.0950, take_profit=1.1100)
            
            # Verify the request was made with model_dump() output
            mock_post.assert_called_with(
                "positions/EURUSD/update/123",
                json_data={"stop_loss": 1.0950, "take_profit": 1.1100}
            )

        # Test close_position uses PositionCloseRequest
        with patch('app.clients.mt5.utils.validate_symbol', return_value="EURUSD"), \
             patch('app.clients.mt5.utils.validate_ticket', return_value=123):
            
            client.close_position("EURUSD", 123, 0.1)
            
            # Verify the request was made with model_dump() output
            mock_post.assert_called_with(
                "positions/EURUSD/close/123",
                json_data={"volume": 0.1}
            )

        # Test close_all_positions uses CloseAllPositionsRequest
        client.close_all_positions("EURUSD")
        
        mock_post.assert_called_with(
            "positions/close_all",
            json_data={"symbol": "EURUSD"}
        )

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_edge_cases(self, mock_get):
        """Test edge cases and boundary conditions."""
        # Test with empty list response
        mock_get.return_value = []
        client = PositionsClient("http://localhost:8000")
        result = client.get_open_positions()
        assert result == []
        
        # Test with None response
        mock_get.return_value = None
        result = client.get_open_positions()
        assert result == []
        
        # Test with positions having minimal data
        minimal_position = {
            "ticket": 123,
            "symbol": "EURUSD",
            "volume": 0.01,
            "type": 0,
            "price_open": 1.0,
            "price_current": 1.0,
            "profit": 0.0,
            "swap": 0.0
        }
        mock_get.return_value = [minimal_position]
        result = client.get_open_positions()
        
        assert len(result) == 1
        assert isinstance(result[0], Position)
        assert result[0].ticket == 123
        assert result[0].commission == 0.0  # default value