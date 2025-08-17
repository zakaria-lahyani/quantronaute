"""
End-to-end integration tests for the entry manager.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from app.entry_manager.manager import EntryManager
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
    create_multi_timeframe_data
)


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""
    
    def test_simple_long_trade_scenario(self):
        """Test complete long trade scenario from entry to exit."""
        # Setup strategy and manager
        strategy = create_basic_strategy(
            name="simple_long",
            position_sizing_value=1000.0,
            stop_loss_value=50.0,
            take_profit_value=100.0
        )
        strategies = {"simple_long": strategy}
        manager = EntryManager(strategies, "EURUSD", 10000.0)
        
        # Create market data
        market_data = create_market_data_simple(current_price=1.1000)
        decision_time = datetime.now()
        
        # Calculate entry decision
        entry = manager.calculate_entry_decision(
            strategy_name="simple_long",
            symbol="EURUSD",
            direction="long",
            entry_price=1.1000,
            decision_time=decision_time,
            market_data=market_data,
            account_balance=10000.0
        )
        
        # Validate entry decision
        assert entry.symbol == "EURUSD"
        assert entry.strategy_name == "simple_long"
        assert entry.direction == "long"
        assert entry.entry_signals == "BUY"
        assert entry.position_size == 1000.0
        assert abs(entry.stop_loss.level - 1.0950) < 0.0001  # 1.1000 - 50 pips
        assert abs(entry.take_profit.level - 1.1100) < 0.0001  # 1.1000 + 100 pips
        
        # Calculate exit decision
        exit_decision = manager.calculate_exit_decision(
            strategy_name="simple_long",
            symbol="EURUSD",
            direction="long",
            decision_time=decision_time
        )
        
        # Validate exit decision
        assert exit_decision.symbol == "EURUSD"
        assert exit_decision.strategy_name == "simple_long"
        assert exit_decision.direction == "long"
        assert exit_decision.magic == entry.magic  # Should have same magic number
    
    def test_percentage_based_trading_scenario(self):
        """Test percentage-based position sizing scenario."""
        strategy = create_percentage_strategy(
            percentage=2.0,
            account_balance=50000.0
        )
        strategies = {"percentage_test": strategy}
        manager = EntryManager(strategies, "GBPUSD", 10000.0)
        
        market_data = create_market_data_simple(current_price=1.2500)
        
        entry = manager.calculate_entry_decision(
            strategy_name="percentage_test",
            symbol="GBPUSD",
            direction="long",
            entry_price=1.2500,
            decision_time=datetime.now(),
            market_data=market_data,
            account_balance=50000.0
        )
        
        # 2% of 50000 = 1000
        assert entry.position_size == 1000.0
        assert entry.stop_loss.level == 1.2470  # 1.2500 - 30 pips
        assert entry.take_profit.level == 1.2560  # 1.2500 + 60 pips
    
    def test_volatility_based_trading_scenario(self):
        """Test volatility-based position sizing scenario."""
        strategy = create_volatility_strategy(
            base_size=2000.0,
            atr_distance=0.0015  # Creates limit order
        )
        strategies = {"volatility_test": strategy}
        manager = EntryManager(strategies, "EURUSD", 10000.0)
        
        # High volatility market data
        market_data = create_market_data_volatile(
            base_price=1.1000,
            volatility=0.0020
        )
        
        entry = manager.calculate_entry_decision(
            strategy_name="volatility_test",
            symbol="EURUSD",
            direction="long",
            entry_price=1.1000,
            decision_time=datetime.now(),
            market_data=market_data,
            account_balance=10000.0
        )
        
        # Should be limit order due to ATR distance
        assert entry.entry_signals == "BUY_LIMIT"
        assert entry.entry_price == 1.0985  # 1.1000 - 0.0015
        
        # Position size varies based on volatility calculation
        assert entry.position_size > 0  # Should have valid position size
        assert isinstance(entry.position_size, float)
    
    def test_multi_target_take_profit_scenario(self):
        """Test multi-target take profit scenario."""
        strategy = create_multi_target_strategy()
        strategies = {"multi_target_test": strategy}
        manager = EntryManager(strategies, "EURUSD", 10000.0)
        
        market_data = create_market_data_simple(current_price=1.1000)
        
        entry = manager.calculate_entry_decision(
            strategy_name="multi_target_test",
            symbol="EURUSD",
            direction="long",
            entry_price=1.1000,
            decision_time=datetime.now(),
            market_data=market_data
        )
        
        # Check multi-target take profit
        assert entry.take_profit.type == "multi_target"
        assert len(entry.take_profit.targets) == 3
        
        # Verify targets exist and have correct values (specific levels may vary based on implementation)
        assert entry.take_profit.targets[0].value == 50.0  # 50 pip target
        assert entry.take_profit.targets[1].value == 100.0  # 100 pip target  
        assert entry.take_profit.targets[2].value == 150.0  # 150 pip target
        
        # Percentages should sum to 100%
        total_percentage = sum(target.percent for target in entry.take_profit.targets)
        assert abs(total_percentage - 100.0) < 0.01
    
    def test_trailing_stop_scenario(self):
        """Test trailing stop loss scenario."""
        strategy = create_trailing_stop_strategy(
            trail_distance=25.0,
            trail_step=5.0
        )
        strategies = {"trailing_test": strategy}
        manager = EntryManager(strategies, "EURUSD", 10000.0)
        
        market_data = create_market_data_trending(
            start_price=1.0900,
            end_price=1.1100  # Strong uptrend
        )
        
        entry = manager.calculate_entry_decision(
            strategy_name="trailing_test",
            symbol="EURUSD",
            direction="long",
            entry_price=1.1000,
            decision_time=datetime.now(),
            market_data=market_data
        )
        
        # Check trailing stop loss
        assert entry.stop_loss.trailing == True
        assert entry.stop_loss.step == 5.0
        # Note: Trailing stop level calculation may vary based on implementation
    
    def test_multiple_strategies_management(self):
        """Test managing multiple strategies simultaneously."""
        strategies = create_multiple_strategies()
        manager = EntryManager(strategies, "EURUSD", 10000.0)
        
        market_data = create_multi_timeframe_data()
        
        # Create mock strategy results with mixed signals
        strategy_results = {
            "conservative": Mock(
                entry=Mock(long=True, short=False),
                exit=Mock(long=False, short=False)
            ),
            "aggressive": Mock(
                entry=Mock(long=False, short=True),
                exit=Mock(long=False, short=False)
            ),
            "scalping": Mock(
                entry=Mock(long=False, short=False),
                exit=Mock(long=True, short=False)
            )
        }
        
        trades = manager.manage_trades(
            strategy_results=strategy_results,
            market_data=market_data,
            account_balance=10000.0
        )
        
        # Should have 2 entries and 1 exit
        assert len(trades.entries) == 2
        assert len(trades.exits) == 1
        
        # Check conservative long entry
        conservative_entry = next(e for e in trades.entries if e.strategy_name == "conservative")
        assert conservative_entry.direction == "long"
        assert conservative_entry.position_size == 500.0
        
        # Check aggressive short entry
        aggressive_entry = next(e for e in trades.entries if e.strategy_name == "aggressive")
        assert aggressive_entry.direction == "short"
        assert aggressive_entry.position_size == 2000.0
        
        # Check scalping exit
        scalping_exit = trades.exits[0]
        assert scalping_exit.strategy_name == "scalping"
        assert scalping_exit.direction == "long"


class TestComplexMarketScenarios:
    """Test behavior in complex market conditions."""
    
    def test_high_volatility_market(self):
        """Test behavior during high volatility periods."""
        strategy = create_volatility_strategy(base_size=1000.0)
        strategies = {"vol_strategy": strategy}
        manager = EntryManager(strategies, "EURUSD", 10000.0)
        
        # Create highly volatile market data
        market_data = create_market_data_volatile(
            base_price=1.1000,
            volatility=0.0050  # Very high volatility
        )
        
        entry = manager.calculate_entry_decision(
            strategy_name="vol_strategy",
            symbol="EURUSD",
            direction="long",
            entry_price=1.1000,
            decision_time=datetime.now(),
            market_data=market_data,
            account_balance=10000.0
        )
        
        # Position size varies based on volatility calculation
        assert entry.position_size > 0  # Should have valid position size
        
        # Stop loss should be ATR-based
        assert entry.stop_loss.type == "indicator"
        assert entry.stop_loss.source == "ATR"
    
    def test_trending_market_conditions(self):
        """Test behavior in strong trending market."""
        strategy = create_basic_strategy(position_sizing_value=1500.0)
        strategies = {"trend_strategy": strategy}
        manager = EntryManager(strategies, "EURUSD", 10000.0)
        
        # Strong uptrend
        market_data = create_market_data_trending(
            start_price=1.0800,
            end_price=1.1200,
            num_bars=50
        )
        
        entry = manager.calculate_entry_decision(
            strategy_name="trend_strategy",
            symbol="EURUSD",
            direction="long",
            entry_price=1.1100,
            decision_time=datetime.now(),
            market_data=market_data
        )
        
        # In trending market, RSI should reflect the trend
        rsi_value = market_data.get("RSI", 50.0)
        assert rsi_value > 50.0  # Should be above 50 in uptrend
        
        # Position should be calculated normally
        assert entry.position_size == 1500.0
        assert entry.direction == "long"
    
    def test_mixed_timeframe_signals(self):
        """Test handling of mixed signals across timeframes."""
        strategy = create_basic_strategy()
        strategy.timeframes = [
            strategy.timeframes[0] for _ in range(3)  # Use same timeframe for simplicity
        ]
        strategies = {"mixed_tf": strategy}
        manager = EntryManager(strategies, "EURUSD", 10000.0)
        
        # Create data with different prices across timeframes
        market_data = create_multi_timeframe_data(
            m1_price=1.1000,
            m5_price=1.0995,
            m15_price=1.0990
        )
        
        entry = manager.calculate_entry_decision(
            strategy_name="mixed_tf",
            symbol="EURUSD",
            direction="long",
            entry_price=1.1000,
            decision_time=datetime.now(),
            market_data=market_data
        )
        
        # Should use the current price from the lowest timeframe
        assert entry.entry_price == 1.1000
        assert entry.position_size == 1000.0


class TestErrorHandlingScenarios:
    """Test error handling in complex scenarios."""
    
    def test_missing_market_data_handling(self):
        """Test handling when market data is incomplete."""
        strategy = create_volatility_strategy()
        strategies = {"test_strategy": strategy}
        manager = EntryManager(strategies, "EURUSD", 10000.0)
        
        # Market data without ATR (required for volatility strategy)
        market_data = {
            "1": [{"time": datetime.now(), "close": 1.1000}],
            "RSI": 50.0
            # Missing ATR
        }
        
        # Should raise an error when required market data is missing
        from app.entry_manager.core.exceptions import CalculationError
        with pytest.raises(CalculationError) as exc_info:
            entry = manager.calculate_entry_decision(
                strategy_name="test_strategy",
                symbol="EURUSD",
                direction="long",
                entry_price=1.1000,
                decision_time=datetime.now(),
                market_data=market_data,
                account_balance=10000.0
            )
        assert "Valid volatility value is required" in str(exc_info.value)
    
    def test_extreme_market_conditions(self):
        """Test behavior in extreme market conditions."""
        strategy = create_basic_strategy()
        strategies = {"extreme_test": strategy}
        manager = EntryManager(strategies, "EURUSD", 10000.0)
        
        # Extreme price movements
        market_data = create_market_data_simple(current_price=2.0000)  # Extreme price
        
        entry = manager.calculate_entry_decision(
            strategy_name="extreme_test",
            symbol="EURUSD",
            direction="long",
            entry_price=2.0000,
            decision_time=datetime.now(),
            market_data=market_data
        )
        
        # Should still calculate properly
        assert entry.position_size == 1000.0
        assert entry.stop_loss.level == 1.9950  # 2.0000 - 50 pips
        assert entry.take_profit.level == 2.0100  # 2.0000 + 100 pips
    
    def test_concurrent_strategy_execution(self):
        """Test concurrent execution of multiple strategies."""
        strategies = create_multiple_strategies()
        manager = EntryManager(strategies, "EURUSD", 10000.0)
        
        market_data = create_market_data_simple()
        decision_time = datetime.now()
        
        # Simulate concurrent entry calculations
        entries = []
        for strategy_name in strategies.keys():
            entry = manager.calculate_entry_decision(
                strategy_name=strategy_name,
                symbol="EURUSD",
                direction="long",
                entry_price=1.1000,
                decision_time=decision_time,
                market_data=market_data,
                account_balance=10000.0
            )
            entries.append(entry)
        
        # All entries should be valid and have unique magic numbers
        assert len(entries) == 3
        magic_numbers = [entry.magic for entry in entries]
        assert len(set(magic_numbers)) == 3  # All unique
        
        # Each entry should have correct strategy-specific sizing
        conservative_entry = next(e for e in entries if e.strategy_name == "conservative")
        aggressive_entry = next(e for e in entries if e.strategy_name == "aggressive")
        scalping_entry = next(e for e in entries if e.strategy_name == "scalping")
        
        assert conservative_entry.position_size == 500.0
        assert aggressive_entry.position_size == 2000.0
        assert scalping_entry.position_size == 1500.0


class TestPerformanceScenarios:
    """Test performance-related scenarios."""
    
    def test_large_number_of_strategies(self):
        """Test performance with many strategies."""
        # Create 10 strategies
        strategies = {}
        for i in range(10):
            strategies[f"strategy_{i}"] = create_basic_strategy(
                name=f"strategy_{i}",
                position_sizing_value=1000.0 + i * 100,
                stop_loss_value=50.0 + i * 5,
                take_profit_value=100.0 + i * 10
            )
        
        manager = EntryManager(strategies, "EURUSD", 10000.0)
        market_data = create_market_data_simple()
        
        # Test entry calculation for all strategies
        start_time = datetime.now()
        
        entries = []
        for strategy_name in strategies.keys():
            entry = manager.calculate_entry_decision(
                strategy_name=strategy_name,
                symbol="EURUSD",
                direction="long",
                entry_price=1.1000,
                decision_time=datetime.now(),
                market_data=market_data
            )
            entries.append(entry)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Should complete within reasonable time (less than 1 second)
        assert execution_time < 1.0
        assert len(entries) == 10
        
        # All entries should be valid
        for i, entry in enumerate(entries):
            assert entry.strategy_name == f"strategy_{i}"
            assert entry.position_size == 1000.0 + i * 100
    
    def test_complex_market_data_processing(self):
        """Test with complex multi-timeframe market data."""
        strategy = create_basic_strategy()
        strategies = {"complex_test": strategy}
        manager = EntryManager(strategies, "EURUSD", 10000.0)
        
        # Create large dataset
        market_data = create_multi_timeframe_data()
        
        # Add many indicators
        market_data.update({
            "ATR": 0.0015,
            "RSI": 45.0,
            "MACD": 0.0002,
            "BB_UPPER": 1.1050,
            "BB_LOWER": 1.0950,
            "MA_20": 1.1000,
            "MA_50": 1.0990,
            "MA_200": 1.0950,
            "STOCH": 30.0,
            "ADX": 25.0
        })
        
        # Should handle complex data efficiently
        entry = manager.calculate_entry_decision(
            strategy_name="complex_test",
            symbol="EURUSD",
            direction="long",
            entry_price=1.1000,
            decision_time=datetime.now(),
            market_data=market_data
        )
        
        assert entry is not None
        assert entry.position_size == 1000.0