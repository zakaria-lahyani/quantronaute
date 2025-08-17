"""
Unit tests for data validation and serialization.
"""

import pytest
import json
from datetime import datetime
from dataclasses import asdict
from typing import Any, Dict
import copy

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


class TestDataValidation:
    """Test suite for data validation."""
    
    def test_stop_loss_level_required(self):
        """Test that stop loss level is required."""
        # This should work
        sl = StopLossResult(type="fixed", level=2995.0)
        assert sl.level == 2995.0
        
        # Python doesn't enforce required fields at runtime
        # But we can test for proper usage
        with pytest.raises(TypeError):
            # Missing required 'level' argument
            StopLossResult(type="fixed")
    
    def test_entry_decision_required_fields(self):
        """Test that all required fields must be provided."""
        # Missing required fields should raise TypeError
        with pytest.raises(TypeError):
            EntryDecision(
                symbol='XAUUSD',
                strategy_name='test'
                # Missing other required fields
            )
        
        # All required fields provided
        entry = EntryDecision(
            symbol='XAUUSD',
            strategy_name='test',
            magic=12345,
            direction='long',
            entry_signals='BUY',
            entry_price=3000.0,
            position_size=1.0,
            stop_loss=StopLossResult(type='fixed', level=2995.0),
            take_profit=TakeProfitResult(type='fixed', level=3010.0),
            decision_time=datetime.now()
        )
        assert entry.symbol == 'XAUUSD'
    
    def test_tp_level_validation(self):
        """Test TPLevel field validation."""
        # Valid TPLevel
        tp = TPLevel(level=3010.0, value=1.0, percent=60.0)
        assert tp.level == 3010.0
        assert tp.value == 1.0
        assert tp.percent == 60.0
        
        # Test with negative values (Python doesn't prevent this, but we can test)
        tp_negative = TPLevel(level=-3010.0, value=-1.0, percent=-60.0)
        assert tp_negative.level == -3010.0  # Allowed but probably invalid
        
        # Test with zero values
        tp_zero = TPLevel(level=0.0, value=0.0, percent=0.0)
        assert tp_zero.level == 0.0
    
    def test_percent_values_validation(self):
        """Test percent field validation."""
        # Valid percent in TPLevel
        tp = TPLevel(level=3010.0, value=1.0, percent=60.0)
        assert tp.percent == 60.0
        
        # Percent over 100 (Python allows this)
        tp_over = TPLevel(level=3010.0, value=1.0, percent=150.0)
        assert tp_over.percent == 150.0
        
        # For TakeProfitResult
        tp_result = TakeProfitResult(type="fixed", level=3010.0, percent=100.0)
        assert tp_result.percent == 100.0
    
    def test_multi_target_total_percent(self):
        """Test that multi-target percentages can be validated."""
        targets = [
            TPLevel(level=3010.0, value=1.0, percent=60.0),
            TPLevel(level=3020.0, value=2.0, percent=40.0)
        ]
        
        tp = TakeProfitResult(type="multi_target", targets=targets)
        
        # Calculate total percent
        total_percent = sum(target.percent for target in tp.targets)
        assert total_percent == 100.0
        
        # Test with invalid total
        invalid_targets = [
            TPLevel(level=3010.0, value=1.0, percent=60.0),
            TPLevel(level=3020.0, value=2.0, percent=30.0)  # Total = 90%
        ]
        
        tp_invalid = TakeProfitResult(type="multi_target", targets=invalid_targets)
        total_invalid = sum(target.percent for target in tp_invalid.targets)
        assert total_invalid == 90.0  # Allowed but may be invalid
    
    def test_position_size_validation(self):
        """Test position size validation."""
        # Valid position size
        entry = EntryDecision(
            symbol='XAUUSD',
            strategy_name='test',
            magic=12345,
            direction='long',
            entry_signals='BUY',
            entry_price=3000.0,
            position_size=1.0,
            stop_loss=StopLossResult(type='fixed', level=2995.0),
            take_profit=TakeProfitResult(type='fixed', level=3010.0),
            decision_time=datetime.now()
        )
        assert entry.position_size == 1.0
        
        # Zero position size (allowed but probably invalid)
        entry_zero = EntryDecision(
            symbol='XAUUSD',
            strategy_name='test',
            magic=12345,
            direction='long',
            entry_signals='BUY',
            entry_price=3000.0,
            position_size=0.0,
            stop_loss=StopLossResult(type='fixed', level=2995.0),
            take_profit=TakeProfitResult(type='fixed', level=3010.0),
            decision_time=datetime.now()
        )
        assert entry_zero.position_size == 0.0


class TestSerialization:
    """Test suite for serialization and deserialization."""
    
    def datetime_handler(self, obj):
        """JSON handler for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    def test_signal_result_json_serialization(self):
        """Test SignalResult JSON serialization."""
        signal = SignalResult(long=True, short=False)
        signal_dict = asdict(signal)
        
        # Serialize to JSON
        json_str = json.dumps(signal_dict)
        assert isinstance(json_str, str)
        
        # Deserialize from JSON
        loaded_dict = json.loads(json_str)
        assert loaded_dict == signal_dict
        
        # Reconstruct object
        reconstructed = SignalResult(**loaded_dict)
        assert reconstructed == signal
    
    def test_tp_level_json_serialization(self):
        """Test TPLevel JSON serialization."""
        tp = TPLevel(level=3010.0, value=1.0, percent=60.0, move_stop=3005.0)
        tp_dict = asdict(tp)
        
        json_str = json.dumps(tp_dict)
        loaded_dict = json.loads(json_str)
        
        reconstructed = TPLevel(**loaded_dict)
        assert reconstructed.level == tp.level
        assert reconstructed.value == tp.value
        assert reconstructed.percent == tp.percent
        assert reconstructed.move_stop == tp.move_stop
    
    def test_entry_decision_json_serialization(self):
        """Test EntryDecision JSON serialization with datetime."""
        entry = EntryDecision(
            symbol='XAUUSD',
            strategy_name='test',
            magic=12345,
            direction='long',
            entry_signals='BUY',
            entry_price=3000.0,
            position_size=1.0,
            stop_loss=StopLossResult(type='fixed', level=2995.0),
            take_profit=TakeProfitResult(type='fixed', level=3010.0),
            decision_time=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        entry_dict = asdict(entry)
        
        # Serialize with datetime handler
        json_str = json.dumps(entry_dict, default=self.datetime_handler)
        assert isinstance(json_str, str)
        
        # Deserialize
        loaded_dict = json.loads(json_str)
        
        # Convert datetime string back to datetime
        loaded_dict['decision_time'] = datetime.fromisoformat(loaded_dict['decision_time'])
        
        # Reconstruct nested objects
        loaded_dict['stop_loss'] = StopLossResult(**loaded_dict['stop_loss'])
        loaded_dict['take_profit'] = TakeProfitResult(**loaded_dict['take_profit'])
        
        reconstructed = EntryDecision(**loaded_dict)
        assert reconstructed.symbol == entry.symbol
        assert reconstructed.decision_time == entry.decision_time
    
    def test_multi_target_serialization(self):
        """Test serialization of multi-target take profit."""
        targets = [
            TPLevel(level=3010.0, value=1.0, percent=60.0),
            TPLevel(level=3020.0, value=2.0, percent=40.0)
        ]
        
        tp = TakeProfitResult(type="multi_target", targets=targets)
        tp_dict = asdict(tp)
        
        json_str = json.dumps(tp_dict)
        loaded_dict = json.loads(json_str)
        
        # Reconstruct targets
        if loaded_dict['targets']:
            loaded_dict['targets'] = [TPLevel(**t) for t in loaded_dict['targets']]
        
        reconstructed = TakeProfitResult(**loaded_dict)
        assert len(reconstructed.targets) == 2
        assert reconstructed.targets[0].level == 3010.0
        assert reconstructed.targets[1].level == 3020.0
    
    def test_trades_serialization(self):
        """Test Trades serialization with multiple entries and exits."""
        entries = [
            EntryDecision(
                symbol='XAUUSD',
                strategy_name='gold',
                magic=12345,
                direction='long',
                entry_signals='BUY',
                entry_price=3000.0,
                position_size=1.0,
                stop_loss=StopLossResult(type='fixed', level=2995.0),
                take_profit=TakeProfitResult(type='fixed', level=3010.0),
                decision_time=datetime(2024, 1, 1, 12, 0, 0)
            )
        ]
        
        exits = [
            ExitDecision(
                symbol='BTCUSD',
                strategy_name='btc',
                magic=67890,
                direction='short',
                decision_time=datetime(2024, 1, 1, 13, 0, 0)
            )
        ]
        
        trades = Trades(entries=entries, exits=exits)
        trades_dict = asdict(trades)
        
        json_str = json.dumps(trades_dict, default=self.datetime_handler)
        loaded_dict = json.loads(json_str)
        
        assert len(loaded_dict['entries']) == 1
        assert len(loaded_dict['exits']) == 1
        assert loaded_dict['entries'][0]['symbol'] == 'XAUUSD'
        assert loaded_dict['exits'][0]['symbol'] == 'BTCUSD'
    
    def test_all_strategies_evaluation_serialization(self):
        """Test AllStrategiesEvaluationResult serialization."""
        strategies = {
            "strategy1": StrategyEvaluationResult(
                strategy_name="strategy1",
                entry=SignalResult(long=True, short=False),
                exit=SignalResult(long=False, short=True)
            ),
            "strategy2": StrategyEvaluationResult(
                strategy_name="strategy2",
                entry=SignalResult(long=False, short=True),
                exit=SignalResult(long=True, short=False)
            )
        }
        
        all_results = AllStrategiesEvaluationResult(strategies=strategies)
        all_dict = asdict(all_results)
        
        json_str = json.dumps(all_dict)
        loaded_dict = json.loads(json_str)
        
        assert "strategy1" in loaded_dict['strategies']
        assert "strategy2" in loaded_dict['strategies']
        assert loaded_dict['strategies']['strategy1']['entry']['long'] is True
        assert loaded_dict['strategies']['strategy2']['entry']['short'] is True
    
    def test_deep_copy(self):
        """Test deep copying of dataclasses."""
        original = EntryDecision(
            symbol='XAUUSD',
            strategy_name='test',
            magic=12345,
            direction='long',
            entry_signals='BUY',
            entry_price=3000.0,
            position_size=1.0,
            stop_loss=StopLossResult(type='fixed', level=2995.0),
            take_profit=TakeProfitResult(
                type='multi_target',
                targets=[
                    TPLevel(level=3010.0, value=1.0, percent=60.0),
                    TPLevel(level=3020.0, value=2.0, percent=40.0)
                ]
            ),
            decision_time=datetime.now()
        )
        
        # Deep copy
        copied = copy.deepcopy(original)
        
        # Verify it's a different object
        assert copied is not original
        assert copied.stop_loss is not original.stop_loss
        assert copied.take_profit is not original.take_profit
        
        # But values are the same
        assert copied.symbol == original.symbol
        assert copied.stop_loss.level == original.stop_loss.level
        
        # Modify copy doesn't affect original
        copied.symbol = 'BTCUSD'
        copied.stop_loss.level = 2990.0
        
        assert original.symbol == 'XAUUSD'
        assert original.stop_loss.level == 2995.0


class TestDataIntegrity:
    """Test suite for data integrity and consistency."""
    
    def test_stop_loss_below_entry_for_long(self):
        """Test that stop loss is below entry for long positions."""
        entry = EntryDecision(
            symbol='XAUUSD',
            strategy_name='test',
            magic=12345,
            direction='long',
            entry_signals='BUY',
            entry_price=3000.0,
            position_size=1.0,
            stop_loss=StopLossResult(type='fixed', level=2995.0),  # Below entry
            take_profit=TakeProfitResult(type='fixed', level=3010.0),  # Above entry
            decision_time=datetime.now()
        )
        
        # For long position, stop should be below entry
        assert entry.stop_loss.level < entry.entry_price
        # Take profit should be above entry
        assert entry.take_profit.level > entry.entry_price
    
    def test_stop_loss_above_entry_for_short(self):
        """Test that stop loss is above entry for short positions."""
        entry = EntryDecision(
            symbol='BTCUSD',
            strategy_name='test',
            magic=67890,
            direction='short',
            entry_signals='SELL',
            entry_price=117400.0,
            position_size=1.0,
            stop_loss=StopLossResult(type='fixed', level=117900.0),  # Above entry
            take_profit=TakeProfitResult(type='fixed', level=116900.0),  # Below entry
            decision_time=datetime.now()
        )
        
        # For short position, stop should be above entry
        assert entry.stop_loss.level > entry.entry_price
        # Take profit should be below entry
        assert entry.take_profit.level < entry.entry_price
    
    def test_multi_target_ordering(self):
        """Test that multi-target levels are properly ordered."""
        targets = [
            TPLevel(level=3010.0, value=1.0, percent=40.0),
            TPLevel(level=3015.0, value=1.5, percent=30.0),
            TPLevel(level=3020.0, value=2.0, percent=30.0)
        ]
        
        tp = TakeProfitResult(type="multi_target", targets=targets)
        
        # Check that targets are in ascending order for long
        levels = [t.level for t in tp.targets]
        assert levels == sorted(levels)
        
        # Check that values are in ascending order (risk/reward)
        values = [t.value for t in tp.targets]
        assert values == sorted(values)
    
    def test_exit_decision_matches_entry(self):
        """Test that exit decision fields match corresponding entry."""
        entry = EntryDecision(
            symbol='XAUUSD',
            strategy_name='gold_strategy',
            magic=12345,
            direction='long',
            entry_signals='BUY',
            entry_price=3000.0,
            position_size=1.0,
            stop_loss=StopLossResult(type='fixed', level=2995.0),
            take_profit=TakeProfitResult(type='fixed', level=3010.0),
            decision_time=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        exit_decision = ExitDecision(
            symbol='XAUUSD',  # Same symbol
            strategy_name='gold_strategy',  # Same strategy
            magic=12345,  # Same magic
            direction='long',  # Same direction
            decision_time=datetime(2024, 1, 1, 13, 0, 0)  # Later time
        )
        
        # Verify matching fields
        assert exit_decision.symbol == entry.symbol
        assert exit_decision.strategy_name == entry.strategy_name
        assert exit_decision.magic == entry.magic
        assert exit_decision.direction == entry.direction
        assert exit_decision.decision_time > entry.decision_time
    
    def test_trades_consistency(self):
        """Test that Trades maintain consistency between entries and exits."""
        entries = [
            EntryDecision(
                symbol='XAUUSD',
                strategy_name='gold',
                magic=12345,
                direction='long',
                entry_signals='BUY',
                entry_price=3000.0,
                position_size=1.0,
                stop_loss=StopLossResult(type='fixed', level=2995.0),
                take_profit=TakeProfitResult(type='fixed', level=3010.0),
                decision_time=datetime(2024, 1, 1, 12, 0, 0)
            ),
            EntryDecision(
                symbol='BTCUSD',
                strategy_name='btc',
                magic=67890,
                direction='short',
                entry_signals='SELL',
                entry_price=117400.0,
                position_size=0.5,
                stop_loss=StopLossResult(type='fixed', level=117900.0),
                take_profit=TakeProfitResult(type='fixed', level=116900.0),
                decision_time=datetime(2024, 1, 1, 12, 30, 0)
            )
        ]
        
        exits = [
            ExitDecision(
                symbol='XAUUSD',
                strategy_name='gold',
                magic=12345,
                direction='long',
                decision_time=datetime(2024, 1, 1, 13, 0, 0)
            )
        ]
        
        trades = Trades(entries=entries, exits=exits)
        
        # Find matching entry for exit
        exit_decision = trades.exits[0]
        matching_entries = [
            e for e in trades.entries 
            if e.symbol == exit_decision.symbol 
            and e.magic == exit_decision.magic
        ]
        
        assert len(matching_entries) == 1
        assert matching_entries[0].strategy_name == exit_decision.strategy_name