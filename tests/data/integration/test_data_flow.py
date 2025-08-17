"""
Integration tests for data flow and end-to-end data scenarios.
"""

import pytest
from datetime import datetime, timedelta
from dataclasses import asdict, replace
import json
from typing import List, Dict

from app.strategy_builder.data.dtos import (
    SignalResult,
    StrategyEvaluationResult,
    AllStrategiesEvaluationResult,
    TPLevel,
    TakeProfitResult,
    StopLossResult,
    EntryDecision,
    ExitDecision,
    Trades
)


class TestDataFlow:
    """Integration tests for complete data flow scenarios."""
    
    def test_signal_to_strategy_evaluation_flow(self):
        """Test flow from signal generation to strategy evaluation."""
        # Step 1: Generate signals
        entry_signal = SignalResult(long=True, short=False)
        exit_signal = SignalResult(long=False, short=True)
        
        # Step 2: Create strategy evaluation
        strategy_result = StrategyEvaluationResult(
            strategy_name="momentum_strategy",
            entry=entry_signal,
            exit=exit_signal
        )
        
        # Step 3: Aggregate into all strategies result
        all_strategies = AllStrategiesEvaluationResult(
            strategies={
                "momentum_strategy": strategy_result
            }
        )
        
        # Verify flow
        assert "momentum_strategy" in all_strategies.strategies
        retrieved_strategy = all_strategies.strategies["momentum_strategy"]
        assert retrieved_strategy.entry.long is True
        assert retrieved_strategy.exit.short is True
        assert retrieved_strategy.strategy_name == "momentum_strategy"
    
    def test_strategy_evaluation_to_entry_decision_flow(self):
        """Test flow from strategy evaluation to entry decision creation."""
        # Step 1: Strategy evaluation indicates entry
        strategy_result = StrategyEvaluationResult(
            strategy_name="breakout_strategy",
            entry=SignalResult(long=True, short=False),
            exit=SignalResult(long=False, short=False)
        )
        
        # Step 2: Create entry decision based on strategy result
        if strategy_result.entry.long:
            entry_decision = EntryDecision(
                symbol='EURUSD',
                strategy_name=strategy_result.strategy_name,
                magic=55555,
                direction='long',
                entry_signals='BUY',
                entry_price=1.0800,
                position_size=100000.0,
                stop_loss=StopLossResult(
                    type='fixed',
                    level=1.0750,
                    trailing=False
                ),
                take_profit=TakeProfitResult(
                    type='multi_target',
                    targets=[
                        TPLevel(level=1.0825, value=0.5, percent=50.0),
                        TPLevel(level=1.0850, value=1.0, percent=50.0)
                    ]
                ),
                decision_time=datetime.now()
            )
            
            # Verify flow
            assert entry_decision.strategy_name == strategy_result.strategy_name
            assert entry_decision.direction == 'long'
            assert entry_decision.entry_signals == 'BUY'
            assert len(entry_decision.take_profit.targets) == 2
    
    def test_multiple_strategies_parallel_evaluation(self):
        """Test parallel evaluation of multiple strategies."""
        # Multiple strategies with different signals
        strategies = {
            "trend_following": StrategyEvaluationResult(
                strategy_name="trend_following",
                entry=SignalResult(long=True, short=False),
                exit=SignalResult(long=False, short=False)
            ),
            "mean_reversion": StrategyEvaluationResult(
                strategy_name="mean_reversion",
                entry=SignalResult(long=False, short=True),
                exit=SignalResult(long=False, short=False)
            ),
            "momentum": StrategyEvaluationResult(
                strategy_name="momentum",
                entry=SignalResult(long=False, short=False),
                exit=SignalResult(long=True, short=False)
            )
        }
        
        all_results = AllStrategiesEvaluationResult(strategies=strategies)
        
        # Generate entry decisions from active strategies
        entry_decisions = []
        base_time = datetime.now()
        
        for name, strategy in all_results.strategies.items():
            if strategy.entry.long:
                entry_decisions.append(EntryDecision(
                    symbol='XAUUSD',
                    strategy_name=name,
                    magic=hash(name) % 100000,
                    direction='long',
                    entry_signals='BUY',
                    entry_price=3000.0,
                    position_size=1.0,
                    stop_loss=StopLossResult(type='fixed', level=2990.0),
                    take_profit=TakeProfitResult(type='fixed', level=3020.0),
                    decision_time=base_time
                ))
            elif strategy.entry.short:
                entry_decisions.append(EntryDecision(
                    symbol='XAUUSD',
                    strategy_name=name,
                    magic=hash(name) % 100000,
                    direction='short',
                    entry_signals='SELL',
                    entry_price=3000.0,
                    position_size=1.0,
                    stop_loss=StopLossResult(type='fixed', level=3010.0),
                    take_profit=TakeProfitResult(type='fixed', level=2980.0),
                    decision_time=base_time
                ))
        
        # Verify results
        assert len(entry_decisions) == 2  # trend_following (long) + mean_reversion (short)
        
        long_entries = [e for e in entry_decisions if e.direction == 'long']
        short_entries = [e for e in entry_decisions if e.direction == 'short']
        
        assert len(long_entries) == 1
        assert len(short_entries) == 1
        assert long_entries[0].strategy_name == "trend_following"
        assert short_entries[0].strategy_name == "mean_reversion"
    
    def test_entry_to_exit_lifecycle(self):
        """Test complete lifecycle from entry to exit."""
        # Step 1: Create entry decision
        entry_time = datetime(2024, 1, 1, 12, 0, 0)
        entry_decision = EntryDecision(
            symbol='BTCUSD',
            strategy_name='scalping_strategy',
            magic=99999,
            direction='long',
            entry_signals='BUY',
            entry_price=117000.0,
            position_size=0.1,
            stop_loss=StopLossResult(
                type='fixed',
                level=116500.0,
                trailing=True,
                step=50.0
            ),
            take_profit=TakeProfitResult(
                type='multi_target',
                targets=[
                    TPLevel(level=117250.0, value=0.5, percent=60.0, move_stop=117100.0),
                    TPLevel(level=117500.0, value=1.0, percent=40.0)
                ]
            ),
            decision_time=entry_time
        )
        
        # Step 2: Simulate time passing and price movement
        # First TP target hit, move stop loss
        updated_stop = StopLossResult(
            type='fixed',
            level=117100.0,  # Moved to breakeven as per TP1
            trailing=True,
            step=50.0
        )
        
        # Step 3: Create exit decision
        exit_time = entry_time + timedelta(hours=2)
        exit_decision = ExitDecision(
            symbol=entry_decision.symbol,
            strategy_name=entry_decision.strategy_name,
            magic=entry_decision.magic,
            direction=entry_decision.direction,
            decision_time=exit_time
        )
        
        # Step 4: Create trades collection
        trades = Trades(entries=[entry_decision], exits=[exit_decision])
        
        # Verify lifecycle
        assert len(trades.entries) == 1
        assert len(trades.exits) == 1
        
        # Verify matching
        entry = trades.entries[0]
        exit = trades.exits[0]
        
        assert entry.symbol == exit.symbol
        assert entry.strategy_name == exit.strategy_name
        assert entry.magic == exit.magic
        assert entry.direction == exit.direction
        assert exit.decision_time > entry.decision_time
    
    def test_multi_symbol_multi_strategy_flow(self):
        """Test complex scenario with multiple symbols and strategies."""
        base_time = datetime.now()
        
        # Define symbols and their prices
        symbols_data = {
            'XAUUSD': {'price': 3000.0, 'stop_offset': 10.0, 'tp_offset': 15.0},
            'BTCUSD': {'price': 117000.0, 'stop_offset': 500.0, 'tp_offset': 750.0},
            'EURUSD': {'price': 1.0800, 'stop_offset': 0.0050, 'tp_offset': 0.0075}
        }
        
        # Multiple strategies evaluate each symbol
        all_entries = []
        all_exits = []
        
        strategies = ["trend", "momentum", "breakout"]
        
        for i, strategy in enumerate(strategies):
            for j, (symbol, data) in enumerate(symbols_data.items()):
                # Alternate between long and short
                is_long = (i + j) % 2 == 0
                
                if is_long:
                    direction = 'long'
                    signals = 'BUY'
                    stop_level = data['price'] - data['stop_offset']
                    tp_level = data['price'] + data['tp_offset']
                else:
                    direction = 'short'
                    signals = 'SELL'
                    stop_level = data['price'] + data['stop_offset']
                    tp_level = data['price'] - data['tp_offset']
                
                # Create entry
                entry = EntryDecision(
                    symbol=symbol,
                    strategy_name=f"{strategy}_strategy",
                    magic=10000 + i * 100 + j,
                    direction=direction,
                    entry_signals=signals,
                    entry_price=data['price'],
                    position_size=1.0 if symbol == 'XAUUSD' else 0.1,
                    stop_loss=StopLossResult(type='fixed', level=stop_level),
                    take_profit=TakeProfitResult(type='fixed', level=tp_level),
                    decision_time=base_time + timedelta(minutes=i*5 + j)
                )
                all_entries.append(entry)
                
                # Create corresponding exit (some time later)
                exit_decision = ExitDecision(
                    symbol=symbol,
                    strategy_name=f"{strategy}_strategy",
                    magic=entry.magic,
                    direction=direction,
                    decision_time=base_time + timedelta(hours=1, minutes=i*5 + j)
                )
                all_exits.append(exit_decision)
        
        # Create master trades collection
        all_trades = Trades(entries=all_entries, exits=all_exits)
        
        # Verify complexity
        assert len(all_trades.entries) == 9  # 3 strategies * 3 symbols
        assert len(all_trades.exits) == 9
        
        # Group by symbol
        by_symbol = {}
        for entry in all_trades.entries:
            if entry.symbol not in by_symbol:
                by_symbol[entry.symbol] = []
            by_symbol[entry.symbol].append(entry)
        
        assert len(by_symbol) == 3  # 3 symbols
        for symbol_entries in by_symbol.values():
            assert len(symbol_entries) == 3  # 3 strategies per symbol
        
        # Group by strategy
        by_strategy = {}
        for entry in all_trades.entries:
            if entry.strategy_name not in by_strategy:
                by_strategy[entry.strategy_name] = []
            by_strategy[entry.strategy_name].append(entry)
        
        assert len(by_strategy) == 3  # 3 strategies
        for strategy_entries in by_strategy.values():
            assert len(strategy_entries) == 3  # 3 symbols per strategy
    
    def test_data_transformation_pipeline(self):
        """Test data transformation through processing pipeline."""
        # Step 1: Raw signal data
        raw_signals = {
            "rsi_oversold": True,
            "macd_bullish": True,
            "volume_spike": False,
            "trend_up": True
        }
        
        # Step 2: Transform to SignalResult
        signal = SignalResult(
            long=raw_signals["rsi_oversold"] and raw_signals["macd_bullish"] and raw_signals["trend_up"],
            short=False
        )
        
        # Step 3: Strategy evaluation
        strategy = StrategyEvaluationResult(
            strategy_name="multi_indicator",
            entry=signal,
            exit=SignalResult(long=False, short=False)
        )
        
        # Step 4: Risk management and position sizing
        risk_percent = 2.0  # 2% risk
        account_balance = 10000.0
        entry_price = 3000.0
        stop_price = 2980.0
        
        risk_amount = account_balance * (risk_percent / 100)
        points_at_risk = entry_price - stop_price
        position_size = risk_amount / (points_at_risk * 100)  # $100 per point for gold
        
        # Step 5: Create final entry decision
        if strategy.entry.long:
            entry_decision = EntryDecision(
                symbol='XAUUSD',
                strategy_name=strategy.strategy_name,
                magic=88888,
                direction='long',
                entry_signals='BUY',
                entry_price=entry_price,
                position_size=round(position_size, 2),
                stop_loss=StopLossResult(type='fixed', level=stop_price),
                take_profit=TakeProfitResult(
                    type='multi_target',
                    targets=[
                        TPLevel(level=3015.0, value=0.75, percent=50.0),  # 1:0.75 R:R
                        TPLevel(level=3040.0, value=2.0, percent=50.0)    # 1:2 R:R
                    ]
                ),
                decision_time=datetime.now()
            )
            
            # Verify pipeline result
            # Risk = 200, Points = 20, Point value = 100
            # Position size = 200 / (20 * 100) = 0.1
            assert entry_decision.position_size == 0.1
            assert entry_decision.direction == 'long'
            assert len(entry_decision.take_profit.targets) == 2
    
    def test_error_handling_in_data_flow(self):
        """Test error handling and data validation in flow."""
        # Test 1: Missing required fields
        with pytest.raises(TypeError):
            # Missing required fields should raise error
            EntryDecision(symbol='XAUUSD')
        
        # Test 2: Invalid take profit without targets
        tp_without_targets = TakeProfitResult(type='multi_target', targets=None)
        
        entry = EntryDecision(
            symbol='XAUUSD',
            strategy_name='test',
            magic=12345,
            direction='long',
            entry_signals='BUY',
            entry_price=3000.0,
            position_size=1.0,
            stop_loss=StopLossResult(type='fixed', level=2995.0),
            take_profit=tp_without_targets,
            decision_time=datetime.now()
        )
        
        # This doesn't fail at creation but would in processing
        assert entry.take_profit.targets is None
        
        # Test 3: Inconsistent data
        inconsistent_entry = EntryDecision(
            symbol='XAUUSD',
            strategy_name='test',
            magic=12345,
            direction='long',  # Long direction
            entry_signals='SELL',  # But sell signal (inconsistent)
            entry_price=3000.0,
            position_size=1.0,
            stop_loss=StopLossResult(type='fixed', level=3010.0),  # Stop above entry for long
            take_profit=TakeProfitResult(type='fixed', level=2990.0),  # TP below entry for long
            decision_time=datetime.now()
        )
        
        # Data is created but inconsistent
        assert inconsistent_entry.direction == 'long'
        assert inconsistent_entry.entry_signals == 'SELL'
        assert inconsistent_entry.stop_loss.level > inconsistent_entry.entry_price
        assert inconsistent_entry.take_profit.level < inconsistent_entry.entry_price
    
    def test_data_aggregation_and_reporting(self):
        """Test data aggregation for reporting purposes."""
        # Create sample trades data
        entries = []
        exits = []
        
        # Multiple entries across different symbols and strategies
        symbols = ['XAUUSD', 'BTCUSD', 'EURUSD']
        strategies = ['trend', 'momentum']
        
        base_time = datetime.now()
        
        for i, symbol in enumerate(symbols):
            for j, strategy in enumerate(strategies):
                entry = EntryDecision(
                    symbol=symbol,
                    strategy_name=f"{strategy}_strategy",
                    magic=1000 + i*10 + j,
                    direction='long' if (i+j) % 2 == 0 else 'short',
                    entry_signals='BUY' if (i+j) % 2 == 0 else 'SELL',
                    entry_price=1000.0 + i*500 + j*100,
                    position_size=1.0,
                    stop_loss=StopLossResult(type='fixed', level=900.0 + i*500 + j*100),
                    take_profit=TakeProfitResult(type='fixed', level=1100.0 + i*500 + j*100),
                    decision_time=base_time + timedelta(hours=i, minutes=j*30)
                )
                entries.append(entry)
                
                # Corresponding exit
                exit_decision = ExitDecision(
                    symbol=symbol,
                    strategy_name=f"{strategy}_strategy",
                    magic=entry.magic,
                    direction=entry.direction,
                    decision_time=entry.decision_time + timedelta(hours=2)
                )
                exits.append(exit_decision)
        
        trades = Trades(entries=entries, exits=exits)
        
        # Aggregation 1: By symbol
        symbol_stats = {}
        for entry in trades.entries:
            if entry.symbol not in symbol_stats:
                symbol_stats[entry.symbol] = {'count': 0, 'long': 0, 'short': 0}
            symbol_stats[entry.symbol]['count'] += 1
            if entry.direction == 'long':
                symbol_stats[entry.symbol]['long'] += 1
            else:
                symbol_stats[entry.symbol]['short'] += 1
        
        assert len(symbol_stats) == 3
        assert symbol_stats['XAUUSD']['count'] == 2
        
        # Aggregation 2: By strategy
        strategy_stats = {}
        for entry in trades.entries:
            if entry.strategy_name not in strategy_stats:
                strategy_stats[entry.strategy_name] = {'count': 0, 'total_size': 0.0}
            strategy_stats[entry.strategy_name]['count'] += 1
            strategy_stats[entry.strategy_name]['total_size'] += entry.position_size
        
        assert len(strategy_stats) == 2
        assert strategy_stats['trend_strategy']['count'] == 3
        assert strategy_stats['momentum_strategy']['count'] == 3
        
        # Aggregation 3: Time-based
        time_stats = {}
        for entry in trades.entries:
            hour = entry.decision_time.hour
            if hour not in time_stats:
                time_stats[hour] = 0
            time_stats[hour] += 1
        
        # Should have entries spread across different hours
        assert len(time_stats) > 1