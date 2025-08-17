"""
Unit tests for the RiskManager class.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from app.entry_manager.manager import EntryManager
from app.entry_manager.core.exceptions import ValidationError, CalculationError
from app.strategy_builder.core.domain.enums import TimeFrameEnum
from app.strategy_builder.data.dtos import EntryDecision, ExitDecision, Trades

from ..fixtures.mock_strategies import (
    create_basic_strategy,
    create_percentage_strategy,
    create_volatility_strategy,
    create_trailing_stop_strategy,
    create_multi_target_strategy,
    create_multiple_strategies
)
from ..fixtures.mock_data import (
    create_market_data_simple,
    create_market_data_trending,
    create_market_data_volatile,
    create_market_data_with_indicators,
    create_multi_timeframe_data,
    create_empty_market_data
)


class TestRiskManagerInit:
    """Test RiskManager initialization."""
    
    def test_valid_initialization(self):
        """Test valid RiskManager initialization."""
        strategy = create_basic_strategy()
        strategies = {"test": strategy}
        
        manager = EntryManager(
            strategies=strategies,
            symbol="EURUSD",
            pip_value=10000.0
        )
        
        assert manager.symbol == "EURUSD"
        assert manager.pip_value == 10000.0
        assert "test" in manager.strategies
    
    def test_invalid_pip_value(self):
        """Test initialization with invalid pip value."""
        strategy = create_basic_strategy()
        strategies = {"test": strategy}
        
        with pytest.raises(ValidationError) as exc_info:
            EntryManager(
                strategies=strategies,
                symbol="EURUSD",
                pip_value=0
            )
        assert "pip_value must be positive" in str(exc_info.value)
        
        with pytest.raises(ValidationError):
            EntryManager(
                strategies=strategies,
                symbol="EURUSD",
                pip_value=-10000.0
            )
    
    def test_strategy_without_risk_config(self):
        """Test initialization with strategy missing risk configuration."""
        # Create a mock strategy without risk
        strategy = Mock()
        strategy.risk = None
        strategies = {"test": strategy}
        
        with pytest.raises(ValidationError) as exc_info:
            EntryManager(
                strategies=strategies,
                symbol="EURUSD",
                pip_value=10000.0
            )
        assert "must have risk configuration" in str(exc_info.value)
    
    def test_strategy_without_stop_loss(self):
        """Test initialization with strategy missing stop loss."""
        strategy = Mock()
        strategy.risk = Mock()
        strategy.risk.sl = None
        strategy.risk.tp = Mock()
        strategies = {"test": strategy}
        
        with pytest.raises(ValidationError) as exc_info:
            EntryManager(
                strategies=strategies,
                symbol="EURUSD",
                pip_value=10000.0
            )
        assert "must have stop loss configuration" in str(exc_info.value)
    
    def test_strategy_without_take_profit(self):
        """Test initialization with strategy missing take profit."""
        strategy = Mock()
        strategy.risk = Mock()
        strategy.risk.sl = Mock()
        strategy.risk.tp = None
        strategies = {"test": strategy}
        
        with pytest.raises(ValidationError) as exc_info:
            EntryManager(
                strategies=strategies,
                symbol="EURUSD",
                pip_value=10000.0
            )
        assert "must have take profit configuration" in str(exc_info.value)
    
    def test_custom_logger(self):
        """Test initialization with custom logger."""
        strategy = create_basic_strategy()
        strategies = {"test": strategy}
        custom_logger = Mock()
        
        manager = EntryManager(
            strategies=strategies,
            symbol="EURUSD",
            pip_value=10000.0,
            logger=custom_logger
        )
        
        assert manager.logger == custom_logger


class TestCalculateEntryDecision:
    """Test calculate_entry_decision method."""
    
    @pytest.fixture
    def manager(self):
        """Create a RiskManager for testing."""
        strategies = create_multiple_strategies()
        return EntryManager(
            strategies=strategies,
            symbol="EURUSD",
            pip_value=10000.0
        )
    
    def test_calculate_entry_long(self, manager):
        """Test calculating entry decision for long position."""
        market_data = create_market_data_simple(current_price=1.1000)
        decision_time = datetime.now()
        
        entry = manager.calculate_entry_decision(
            strategy_name="conservative",
            symbol="EURUSD",
            direction="long",
            entry_price=1.1000,
            decision_time=decision_time,
            market_data=market_data,
            account_balance=10000.0
        )
        
        assert isinstance(entry, EntryDecision)
        assert entry.symbol == "EURUSD"
        assert entry.strategy_name == "conservative"
        assert entry.direction == "long"
        assert entry.position_size == 500.0  # Fixed size from conservative strategy
        assert entry.stop_loss is not None
        assert entry.take_profit is not None
    
    def test_calculate_entry_short(self, manager):
        """Test calculating entry decision for short position."""
        market_data = create_market_data_simple(current_price=1.1000)
        decision_time = datetime.now()
        
        entry = manager.calculate_entry_decision(
            strategy_name="aggressive",
            symbol="EURUSD",
            direction="short",
            entry_price=1.1000,
            decision_time=decision_time,
            market_data=market_data
        )
        
        assert isinstance(entry, EntryDecision)
        assert entry.direction == "short"
        assert entry.position_size == 2000.0  # Fixed size from aggressive strategy
    
    def test_calculate_entry_with_limit_order(self):
        """Test entry decision with ATR distance creates limit order."""
        strategy = create_volatility_strategy(atr_distance=0.002)
        strategies = {"volatility": strategy}
        manager = EntryManager(strategies, "EURUSD", 10000.0)
        
        market_data = create_market_data_simple(current_price=1.1000, atr_value=0.001)
        
        entry = manager.calculate_entry_decision(
            strategy_name="volatility",
            symbol="EURUSD",
            direction="long",
            entry_price=1.1000,
            decision_time=datetime.now(),
            market_data=market_data,
            account_balance=10000.0
        )
        
        assert entry.entry_signals == "BUY_LIMIT"
        assert entry.entry_price == 1.098  # 1.1000 - 0.002
    
    def test_calculate_entry_invalid_strategy(self, manager):
        """Test calculating entry with invalid strategy name."""
        with pytest.raises(ValidationError) as exc_info:
            manager.calculate_entry_decision(
                strategy_name="non_existent",
                symbol="EURUSD",
                direction="long",
                entry_price=1.1000,
                decision_time=datetime.now()
            )
        assert "Strategy 'non_existent' not found" in str(exc_info.value)
    
    def test_calculate_entry_error_handling(self, manager):
        """Test error handling in entry calculation."""
        # Mock a calculator to raise an error
        with patch.object(manager, '_calculate_position_size', side_effect=Exception("Test error")):
            with pytest.raises(CalculationError) as exc_info:
                manager.calculate_entry_decision(
                    strategy_name="conservative",
                    symbol="EURUSD",
                    direction="long",
                    entry_price=1.1000,
                    decision_time=datetime.now()
                )
            assert "Failed to calculate entry decision" in str(exc_info.value)


class TestCalculateExitDecision:
    """Test calculate_exit_decision method."""
    
    @pytest.fixture
    def manager(self):
        """Create a RiskManager for testing."""
        strategy = create_basic_strategy()
        strategies = {"test": strategy}
        return EntryManager(strategies, "EURUSD", 10000.0)
    
    def test_calculate_exit_long(self, manager):
        """Test calculating exit decision for long position."""
        decision_time = datetime.now()
        
        exit_decision = manager.calculate_exit_decision(
            strategy_name="test",
            symbol="EURUSD",
            direction="long",
            decision_time=decision_time
        )
        
        assert isinstance(exit_decision, ExitDecision)
        assert exit_decision.symbol == "EURUSD"
        assert exit_decision.strategy_name == "test"
        assert exit_decision.direction == "long"
        assert exit_decision.decision_time == decision_time
    
    def test_calculate_exit_short(self, manager):
        """Test calculating exit decision for short position."""
        exit_decision = manager.calculate_exit_decision(
            strategy_name="test",
            symbol="EURUSD",
            direction="short",
            decision_time=datetime.now()
        )
        
        assert exit_decision.direction == "short"
    
    def test_calculate_exit_invalid_strategy(self, manager):
        """Test calculating exit with invalid strategy name."""
        with pytest.raises(ValidationError) as exc_info:
            manager.calculate_exit_decision(
                strategy_name="non_existent",
                symbol="EURUSD",
                direction="long",
                decision_time=datetime.now()
            )
        assert "Strategy 'non_existent' not found" in str(exc_info.value)


class TestManageTrades:
    """Test manage_trades method."""
    
    @pytest.fixture
    def manager(self):
        """Create a RiskManager for testing."""
        strategies = create_multiple_strategies()
        return EntryManager(strategies, "EURUSD", 10000.0)
    
    def test_manage_trades_with_entries(self, manager):
        """Test managing trades with entry signals."""
        market_data = create_multi_timeframe_data()
        
        # Create mock strategy results with entry signals
        strategy_results = {
            "conservative": Mock(
                entry=Mock(long=True, short=False),
                exit=Mock(long=False, short=False)
            ),
            "aggressive": Mock(
                entry=Mock(long=False, short=True),
                exit=Mock(long=False, short=False)
            )
        }
        
        trades = manager.manage_trades(
            strategy_results=strategy_results,
            market_data=market_data,
            account_balance=10000.0
        )
        
        assert isinstance(trades, Trades)
        assert len(trades.entries) == 2
        assert len(trades.exits) == 0
        
        # Check entry details
        assert trades.entries[0].strategy_name == "conservative"
        assert trades.entries[0].direction == "long"
        assert trades.entries[1].strategy_name == "aggressive"
        assert trades.entries[1].direction == "short"
    
    def test_manage_trades_with_exits(self, manager):
        """Test managing trades with exit signals."""
        market_data = create_market_data_simple()
        
        strategy_results = {
            "conservative": Mock(
                entry=Mock(long=False, short=False),
                exit=Mock(long=True, short=False)
            ),
            "scalping": Mock(
                entry=Mock(long=False, short=False),
                exit=Mock(long=False, short=True)
            )
        }
        
        trades = manager.manage_trades(
            strategy_results=strategy_results,
            market_data=market_data
        )
        
        assert len(trades.entries) == 0
        assert len(trades.exits) == 2
        assert trades.exits[0].direction == "long"
        assert trades.exits[1].direction == "short"
    
    def test_manage_trades_mixed_signals(self, manager):
        """Test managing trades with both entry and exit signals."""
        market_data = create_market_data_simple()
        
        strategy_results = {
            "conservative": Mock(
                entry=Mock(long=True, short=False),
                exit=Mock(long=False, short=True)
            )
        }
        
        trades = manager.manage_trades(
            strategy_results=strategy_results,
            market_data=market_data
        )
        
        assert len(trades.entries) == 1
        assert len(trades.exits) == 1
    
    def test_manage_trades_unknown_strategy(self, manager):
        """Test managing trades with unknown strategy in results."""
        market_data = create_market_data_simple()
        
        strategy_results = {
            "unknown_strategy": Mock(
                entry=Mock(long=True, short=False),
                exit=Mock(long=False, short=False)
            )
        }
        
        # Should handle gracefully with warning
        trades = manager.manage_trades(
            strategy_results=strategy_results,
            market_data=market_data
        )
        
        assert len(trades.entries) == 0
        assert len(trades.exits) == 0
    
    def test_manage_trades_empty_market_data(self, manager):
        """Test managing trades with empty market data."""
        market_data = create_empty_market_data()
        
        strategy_results = {
            "conservative": Mock(
                entry=Mock(long=True, short=False),
                exit=Mock(long=False, short=False)
            )
        }
        
        with pytest.raises(CalculationError) as exc_info:
            manager.manage_trades(
                strategy_results=strategy_results,
                market_data=market_data
            )
        assert "Could not extract current price" in str(exc_info.value)


class TestExtractCurrentPrice:
    """Test _extract_current_price method."""
    
    @pytest.fixture
    def manager(self):
        """Create a RiskManager for testing."""
        strategy = create_basic_strategy()
        strategies = {"test": strategy}
        return EntryManager(strategies, "EURUSD", 10000.0)
    
    def test_extract_price_from_timeframe(self, manager):
        """Test extracting price from specific timeframe."""
        market_data = create_multi_timeframe_data()
        
        price = manager._extract_current_price(market_data, TimeFrameEnum.M1)
        assert price == 1.1000
        
        price = manager._extract_current_price(market_data, TimeFrameEnum.M5)
        assert price == 1.1
    
    def test_extract_price_fallback(self, manager):
        """Test price extraction fallback when timeframe not found."""
        market_data = {
            "60": [{"time": datetime.now(), "close": 1.2000}]
        }
        
        # Should fallback to any available price
        price = manager._extract_current_price(market_data, TimeFrameEnum.M1)
        assert price == 1.2000
    
    def test_extract_price_no_data(self, manager):
        """Test price extraction with no valid data."""
        market_data = {}
        
        with pytest.raises(CalculationError) as exc_info:
            manager._extract_current_price(market_data, TimeFrameEnum.M1)
        assert "Could not extract current price" in str(exc_info.value)
    
    def test_extract_price_invalid_format(self, manager):
        """Test price extraction with invalid data format."""
        market_data = {
            "1": "not_a_list"
        }
        
        with pytest.raises(CalculationError):
            manager._extract_current_price(market_data, TimeFrameEnum.M1)


class TestGetStrategyRiskSummary:
    """Test get_strategy_risk_summary method."""
    
    @pytest.fixture
    def manager(self):
        """Create a RiskManager for testing."""
        strategies = {
            "basic": create_basic_strategy(),
            "volatility": create_volatility_strategy(),
            "multi_target": create_multi_target_strategy()
        }
        return EntryManager(strategies, "EURUSD", 10000.0)
    
    def test_get_basic_strategy_summary(self, manager):
        """Test getting summary for basic strategy."""
        summary = manager.get_strategy_risk_summary("basic")
        
        assert summary["strategy_name"] == "basic"
        assert str(summary["position_sizing"]["type"]).split('.')[-1].lower() == "fixed"
        assert summary["position_sizing"]["value"] == 1000.0
        assert summary["stop_loss"]["type"] == "fixed"
        assert summary["take_profit"]["type"] == "fixed"
        assert "M1" in str(summary["timeframes"])
        assert "M5" in str(summary["timeframes"])
    
    def test_get_volatility_strategy_summary(self, manager):
        """Test getting summary for volatility strategy."""
        summary = manager.get_strategy_risk_summary("volatility")
        
        assert str(summary["position_sizing"]["type"]).split('.')[-1].lower() == "volatility"
        assert summary["stop_loss"]["type"] == "indicator"
        assert "H1" in str(summary["timeframes"])
    
    def test_get_multi_target_strategy_summary(self, manager):
        """Test getting summary for multi-target strategy."""
        summary = manager.get_strategy_risk_summary("multi_target")
        
        assert summary["take_profit"]["type"] == "multi_target"
        assert "targets" in summary["take_profit"]["config"]
    
    def test_get_summary_invalid_strategy(self, manager):
        """Test getting summary for non-existent strategy."""
        with pytest.raises(ValidationError) as exc_info:
            manager.get_strategy_risk_summary("non_existent")
        assert "Strategy 'non_existent' not found" in str(exc_info.value)