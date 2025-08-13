"""
Unit tests for MT5 models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.clients.mt5.models import (
    OrderType, Timeframe, APIResponse, Position, Order, Symbol, TickInfo,
    Account, HistoricalBar, HistoricalData, CreateOrderRequest,
    PositionUpdateRequest, PositionCloseRequest, UpdatePendingOrderRequest,
    DeletePendingOrderRequest, SymbolSelectRequest, SymbolSelectResponse,
    SymbolTradableResponse, HTTPValidationError
)


class TestEnums:
    """Test enum classes."""

    def test_order_type_enum(self):
        """Test OrderType enum values."""
        assert OrderType.BUY == "BUY"
        assert OrderType.SELL == "SELL"
        assert OrderType.BUY_LIMIT == "BUY_LIMIT"
        assert OrderType.SELL_LIMIT == "SELL_LIMIT"
        assert OrderType.BUY_STOP == "BUY_STOP"
        assert OrderType.SELL_STOP == "SELL_STOP"
        assert OrderType.BUY_STOP_LIMIT == "BUY_STOP_LIMIT"
        assert OrderType.SELL_STOP_LIMIT == "SELL_STOP_LIMIT"

    def test_timeframe_enum(self):
        """Test Timeframe enum values."""
        assert Timeframe.M1 == "M1"
        assert Timeframe.M5 == "M5"
        assert Timeframe.M15 == "M15"
        assert Timeframe.M30 == "M30"
        assert Timeframe.H1 == "H1"
        assert Timeframe.H4 == "H4"
        assert Timeframe.D1 == "D1"
        assert Timeframe.W1 == "W1"
        assert Timeframe.MN1 == "MN1"


class TestAPIResponse:
    """Test APIResponse model."""

    def test_successful_response(self):
        """Test successful API response."""
        response = APIResponse(
            success=True,
            data={"key": "value"},
            message="Operation successful"
        )
        
        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.message == "Operation successful"
        assert response.error_code is None

    def test_error_response(self):
        """Test error API response."""
        response = APIResponse(
            success=False,
            message="Operation failed",
            error_code="INVALID_PARAM"
        )
        
        assert response.success is False
        assert response.data is None
        assert response.message == "Operation failed"
        assert response.error_code == "INVALID_PARAM"

    def test_minimal_response(self):
        """Test minimal API response."""
        response = APIResponse(success=True)
        
        assert response.success is True
        assert response.data is None
        assert response.message is None
        assert response.error_code is None


class TestPosition:
    """Test Position model."""

    def test_valid_position(self):
        """Test creating valid position."""
        position = Position(
            ticket=123456789,
            symbol="EURUSD",
            volume=0.1,
            type=0,
            price_open=1.1000,
            price_current=1.1015,
            profit=15.0,
            swap=0.0,
            commission=-0.70,
            comment="Test position",
            magic=12345,
            time=datetime(2023, 1, 1, 12, 0, 0),
            sl=1.0950,
            tp=1.1100
        )
        
        assert position.ticket == 123456789
        assert position.symbol == "EURUSD"
        assert position.volume == 0.1
        assert position.type == 0
        assert position.price_open == 1.1000
        assert position.price_current == 1.1015
        assert position.profit == 15.0
        assert position.swap == 0.0
        assert position.commission == -0.70
        assert position.comment == "Test position"
        assert position.magic == 12345
        assert position.sl == 1.0950
        assert position.tp == 1.1100

    def test_position_minimal_fields(self):
        """Test position with minimal required fields."""
        position = Position(
            ticket=123456789,
            symbol="EURUSD",
            volume=0.1,
            type=0,
            price_open=1.1000,
            price_current=1.1015,
            profit=15.0,
            swap=0.0
        )
        
        assert position.ticket == 123456789
        assert position.symbol == "EURUSD"
        assert position.commission == 0.0  # default
        assert position.comment == ""  # default
        assert position.magic == 0  # default


class TestOrder:
    """Test Order model."""

    def test_valid_order(self):
        """Test creating valid order."""
        order = Order(
            ticket=111222333,
            symbol="EURUSD",
            volume=0.1,
            type="BUY_LIMIT",
            price_open=1.0950,
            price_current=1.1000,
            sl=1.0900,
            tp=1.1050,
            comment="Buy limit order",
            magic=98765,
            time_setup=datetime(2023, 1, 1, 10, 0, 0)
        )
        
        assert order.ticket == 111222333
        assert order.symbol == "EURUSD"
        assert order.volume == 0.1
        assert order.type == "BUY_LIMIT"
        assert order.price_open == 1.0950
        assert order.sl == 1.0900
        assert order.tp == 1.1050

    def test_order_type_conversion(self):
        """Test order type conversion from int to string."""
        order = Order(
            ticket=111222333,
            symbol="EURUSD",
            type=0  # Should convert to "BUY"
        )
        
        assert order.type == "BUY"

    def test_order_type_conversion_mapping(self):
        """Test all order type conversions."""
        type_mappings = {
            0: "BUY",
            1: "SELL", 
            2: "BUY_LIMIT",
            3: "SELL_LIMIT",
            4: "BUY_STOP",
            5: "SELL_STOP",
            6: "BUY_STOP_LIMIT",
            7: "SELL_STOP_LIMIT"
        }
        
        for int_type, str_type in type_mappings.items():
            order = Order(ticket=123, symbol="EURUSD", type=int_type)
            assert order.type == str_type

    def test_order_unknown_type(self):
        """Test order with unknown type."""
        order = Order(ticket=123, symbol="EURUSD", type=99)
        assert order.type == "UNKNOWN_TYPE_99"

    def test_order_volume_handling(self):
        """Test order volume handling."""
        # Test with explicit volume
        order = Order(ticket=123, symbol="EURUSD", type=0, volume=0.5)
        assert order.volume == 0.5
        
        # Test with None volume (should get default)
        order = Order(ticket=123, symbol="EURUSD", type=0, volume=None)
        assert order.volume == 0.01  # default

    def test_order_price_open_handling(self):
        """Test order price_open handling."""
        # Test with explicit price
        order = Order(ticket=123, symbol="EURUSD", type=0, price_open=1.1000)
        assert order.price_open == 1.1000
        
        # Test with None price_open
        order = Order(ticket=123, symbol="EURUSD", type=0, price_open=None)
        assert order.price_open == 0.0  # default


class TestSymbol:
    """Test Symbol model."""

    def test_valid_symbol(self):
        """Test creating valid symbol."""
        symbol = Symbol(
            name="EURUSD",
            description="Euro vs US Dollar",
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
            digits=5,
            point=0.00001,
            spread=2,
            trade_mode="FULL",
            volume_min=0.01,
            volume_max=1000.0,
            volume_step=0.01
        )
        
        assert symbol.name == "EURUSD"
        assert symbol.description == "Euro vs US Dollar"
        assert symbol.currency_base == "EUR"
        assert symbol.digits == 5
        assert symbol.point == 0.00001

    def test_symbol_minimal(self):
        """Test symbol with minimal required fields."""
        symbol = Symbol(name="EURUSD")
        
        assert symbol.name == "EURUSD"
        assert symbol.description is None
        assert symbol.digits is None


class TestTickInfo:
    """Test TickInfo model."""

    def test_valid_tick(self):
        """Test creating valid tick info."""
        tick = TickInfo(
            symbol="EURUSD",
            time=datetime(2023, 1, 1, 12, 0, 0),
            bid=1.1000,
            ask=1.1002,
            last=1.1001,
            volume=1000,
            flags=6
        )
        
        assert tick.symbol == "EURUSD"
        assert tick.bid == 1.1000
        assert tick.ask == 1.1002
        assert tick.last == 1.1001
        assert tick.volume == 1000

    def test_tick_minimal(self):
        """Test tick with minimal required fields."""
        tick = TickInfo(
            symbol="EURUSD",
            time=datetime(2023, 1, 1, 12, 0, 0),
            bid=1.1000,
            ask=1.1002
        )
        
        assert tick.symbol == "EURUSD"
        assert tick.bid == 1.1000
        assert tick.ask == 1.1002
        assert tick.last is None
        assert tick.volume is None


class TestAccount:
    """Test Account model."""

    def test_valid_account(self):
        """Test creating valid account."""
        account = Account(
            login=12345678,
            trade_mode="DEMO",
            name="Test Account",
            server="MetaQuotes-Demo",
            currency="USD",
            leverage=500,
            balance=10000.0,
            equity=10150.0,
            margin=250.0,
            margin_free=9900.0,
            profit=150.0
        )
        
        assert account.login == 12345678
        assert account.trade_mode == "DEMO"
        assert account.name == "Test Account"
        assert account.currency == "USD"
        assert account.leverage == 500
        assert account.balance == 10000.0
        assert account.equity == 10150.0

    def test_account_optional_fields(self):
        """Test account with optional fields."""
        account = Account(
            login=12345678,
            trade_mode="DEMO",
            name="Test Account",
            server="MetaQuotes-Demo",
            currency="USD",
            leverage=500,
            balance=10000.0,
            equity=10150.0,
            margin=250.0,
            margin_free=9900.0,
            profit=150.0
        )
        
        assert account.margin_level is None  # optional field
        assert account.company is None  # optional field


class TestHistoricalBar:
    """Test HistoricalBar model."""

    def test_valid_bar(self):
        """Test creating valid historical bar."""
        bar = HistoricalBar(
            time=datetime(2023, 1, 1, 0, 0, 0),
            open=1.1000,
            high=1.1020,
            low=1.0980,
            close=1.1015,
            tick_volume=1500,
            spread=2,
            real_volume=0
        )
        
        assert bar.time == datetime(2023, 1, 1, 0, 0, 0)
        assert bar.open == 1.1000
        assert bar.high == 1.1020
        assert bar.low == 1.0980
        assert bar.close == 1.1015
        assert bar.tick_volume == 1500

    def test_bar_minimal(self):
        """Test bar with minimal required fields."""
        bar = HistoricalBar(
            time=datetime(2023, 1, 1, 0, 0, 0),
            open=1.1000,
            high=1.1020,
            low=1.0980,
            close=1.1015,
            tick_volume=1500
        )
        
        assert bar.spread is None
        assert bar.real_volume is None


class TestHistoricalData:
    """Test HistoricalData model."""

    def test_valid_historical_data(self):
        """Test creating valid historical data."""
        bars = [
            HistoricalBar(
                time=datetime(2023, 1, 1, 0, 0, 0),
                open=1.1000,
                high=1.1020,
                low=1.0980,
                close=1.1015,
                tick_volume=1500
            )
        ]
        
        data = HistoricalData(
            symbol="EURUSD",
            timeframe="H1",
            bars=bars,
            count=1
        )
        
        assert data.symbol == "EURUSD"
        assert data.timeframe == "H1"
        assert len(data.bars) == 1
        assert data.count == 1


class TestRequestModels:
    """Test request models."""

    def test_create_order_request(self):
        """Test CreateOrderRequest model."""
        request = CreateOrderRequest(
            symbol="EURUSD",
            volume=0.1,
            order_type=OrderType.BUY,
            price=1.1000,
            sl=1.0950,
            tp=1.1100,
            comment="Test order",
            magic=12345
        )
        
        assert request.symbol == "EURUSD"
        assert request.volume == 0.1
        assert request.order_type == OrderType.BUY
        assert request.price == 1.1000
        assert request.sl == 1.0950
        assert request.tp == 1.1100

    def test_create_order_request_validation(self):
        """Test CreateOrderRequest validation."""
        # Volume must be positive
        with pytest.raises(ValidationError):
            CreateOrderRequest(
                symbol="EURUSD",
                volume=-0.1,
                order_type=OrderType.BUY
            )
        
        # Volume must be positive (zero not allowed)
        with pytest.raises(ValidationError):
            CreateOrderRequest(
                symbol="EURUSD",
                volume=0.0,
                order_type=OrderType.BUY
            )

    def test_create_order_request_price_validation(self):
        """Test price validation for pending orders."""
        # Price required for limit orders
        with pytest.raises(ValidationError):
            CreateOrderRequest(
                symbol="EURUSD",
                volume=0.1,
                order_type=OrderType.BUY_LIMIT,
                price=None
            )
        
        # Price not required for market orders
        request = CreateOrderRequest(
            symbol="EURUSD", 
            volume=0.1,
            order_type=OrderType.BUY,
            price=None
        )
        assert request.price is None

    def test_position_update_request(self):
        """Test PositionUpdateRequest model."""
        request = PositionUpdateRequest(
            stop_loss=1.0950,
            take_profit=1.1100
        )
        
        assert request.stop_loss == 1.0950
        assert request.take_profit == 1.1100

    def test_position_update_request_optional(self):
        """Test PositionUpdateRequest with optional fields."""
        request = PositionUpdateRequest()
        
        assert request.stop_loss is None
        assert request.take_profit is None

    def test_position_close_request(self):
        """Test PositionCloseRequest model."""
        request = PositionCloseRequest(volume=0.1)
        
        assert request.volume == 0.1
        
        # Volume must be positive
        with pytest.raises(ValidationError):
            PositionCloseRequest(volume=-0.1)

    def test_symbol_select_request(self):
        """Test SymbolSelectRequest model."""
        request = SymbolSelectRequest(symbol="EURUSD", enable=True)
        
        assert request.symbol == "EURUSD"
        assert request.enable is True
        
        # Test default enable value
        request = SymbolSelectRequest(symbol="EURUSD")
        assert request.enable is True

    def test_update_pending_order_request(self):
        """Test UpdatePendingOrderRequest model."""
        request = UpdatePendingOrderRequest(
            ticket=123456,
            price=1.1000,
            sl=1.0950,
            tp=1.1100,
            comment="Updated order"
        )
        
        assert request.ticket == 123456
        assert request.price == 1.1000
        assert request.sl == 1.0950
        assert request.tp == 1.1100
        assert request.comment == "Updated order"

    def test_delete_pending_order_request(self):
        """Test DeletePendingOrderRequest model."""
        request = DeletePendingOrderRequest(ticket=123456)
        
        assert request.ticket == 123456


class TestResponseModels:
    """Test response models."""

    def test_symbol_select_response(self):
        """Test SymbolSelectResponse model."""
        response = SymbolSelectResponse(
            symbol="EURUSD",
            success=True,
            action="added"
        )
        
        assert response.symbol == "EURUSD"
        assert response.success is True
        assert response.action == "added"

    def test_symbol_tradable_response(self):
        """Test SymbolTradableResponse model."""
        response = SymbolTradableResponse(
            symbol="EURUSD",
            is_tradable=True
        )
        
        assert response.symbol == "EURUSD"
        assert response.is_tradable is True


class TestModelValidation:
    """Test model validation edge cases."""

    def test_empty_symbol(self):
        """Test validation with empty symbol."""
        # Most models should accept any string for symbol
        position = Position(
            ticket=123,
            symbol="",  # Empty symbol should be allowed
            volume=0.1,
            type=0,
            price_open=1.1000,
            price_current=1.1000,
            profit=0.0,
            swap=0.0
        )
        assert position.symbol == ""

    def test_large_numbers(self):
        """Test validation with large numbers."""
        position = Position(
            ticket=999999999999,  # Large ticket
            symbol="EURUSD",
            volume=1000.0,  # Large volume
            type=0,
            price_open=999.9999,  # Large price
            price_current=999.9999,
            profit=99999.99,  # Large profit
            swap=0.0
        )
        
        assert position.ticket == 999999999999
        assert position.volume == 1000.0
        assert position.profit == 99999.99

    def test_negative_values_where_allowed(self):
        """Test negative values where they should be allowed."""
        position = Position(
            ticket=123,
            symbol="EURUSD",
            volume=0.1,
            type=0,
            price_open=1.1000,
            price_current=1.0950,
            profit=-50.0,  # Negative profit (loss)
            swap=-2.5,  # Negative swap
            commission=-0.70  # Negative commission
        )
        
        assert position.profit == -50.0
        assert position.swap == -2.5
        assert position.commission == -0.70

    def test_model_dump_method(self):
        """Test model_dump method works correctly."""
        position = Position(
            ticket=123,
            symbol="EURUSD",
            volume=0.1,
            type=0,
            price_open=1.1000,
            price_current=1.1000,
            profit=0.0,
            swap=0.0
        )
        
        data = position.model_dump()
        assert isinstance(data, dict)
        assert data["ticket"] == 123
        assert data["symbol"] == "EURUSD"
        assert data["volume"] == 0.1