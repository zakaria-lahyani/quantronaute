"""
Unit tests for Data Transfer Objects (DTOs).
"""

import pytest
from datetime import datetime
from dataclasses import asdict, fields
from typing import get_type_hints
import json

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


class TestSignalResult:
    """Test suite for SignalResult DTO."""
    
    def test_initialization_default(self):
        """Test default initialization."""
        signal = SignalResult()
        assert signal.long is None
        assert signal.short is None
    
    def test_initialization_with_values(self):
        """Test initialization with values."""
        signal = SignalResult(long=True, short=False)
        assert signal.long is True
        assert signal.short is False
    
    def test_partial_initialization(self):
        """Test partial initialization."""
        signal_long = SignalResult(long=True)
        assert signal_long.long is True
        assert signal_long.short is None
        
        signal_short = SignalResult(short=True)
        assert signal_short.long is None
        assert signal_short.short is True
    
    def test_dataclass_conversion(self):
        """Test conversion to dict."""
        signal = SignalResult(long=True, short=False)
        signal_dict = asdict(signal)
        
        assert signal_dict == {'long': True, 'short': False}
    
    def test_equality(self):
        """Test equality comparison."""
        signal1 = SignalResult(long=True, short=False)
        signal2 = SignalResult(long=True, short=False)
        signal3 = SignalResult(long=False, short=True)
        
        assert signal1 == signal2
        assert signal1 != signal3


class TestStrategyEvaluationResult:
    """Test suite for StrategyEvaluationResult DTO."""
    
    def test_initialization(self):
        """Test initialization with all fields."""
        entry_signal = SignalResult(long=True, short=False)
        exit_signal = SignalResult(long=False, short=True)
        
        result = StrategyEvaluationResult(
            strategy_name="test_strategy",
            entry=entry_signal,
            exit=exit_signal
        )
        
        assert result.strategy_name == "test_strategy"
        assert result.entry == entry_signal
        assert result.exit == exit_signal
    
    def test_nested_dataclass_conversion(self):
        """Test conversion to dict with nested dataclasses."""
        result = StrategyEvaluationResult(
            strategy_name="test_strategy",
            entry=SignalResult(long=True, short=False),
            exit=SignalResult(long=False, short=True)
        )
        
        result_dict = asdict(result)
        
        expected = {
            'strategy_name': 'test_strategy',
            'entry': {'long': True, 'short': False},
            'exit': {'long': False, 'short': True}
        }
        
        assert result_dict == expected


class TestAllStrategiesEvaluationResult:
    """Test suite for AllStrategiesEvaluationResult DTO."""
    
    def test_initialization(self):
        """Test initialization with multiple strategies."""
        strategy1 = StrategyEvaluationResult(
            strategy_name="strategy1",
            entry=SignalResult(long=True),
            exit=SignalResult(short=True)
        )
        
        strategy2 = StrategyEvaluationResult(
            strategy_name="strategy2",
            entry=SignalResult(short=True),
            exit=SignalResult(long=True)
        )
        
        all_results = AllStrategiesEvaluationResult(
            strategies={
                "strategy1": strategy1,
                "strategy2": strategy2
            }
        )
        
        assert len(all_results.strategies) == 2
        assert all_results.strategies["strategy1"] == strategy1
        assert all_results.strategies["strategy2"] == strategy2
    
    def test_empty_strategies(self):
        """Test initialization with empty strategies."""
        all_results = AllStrategiesEvaluationResult(strategies={})
        assert all_results.strategies == {}
        assert len(all_results.strategies) == 0


class TestTPLevel:
    """Test suite for TPLevel DTO."""
    
    def test_initialization_required_fields(self):
        """Test initialization with required fields only."""
        tp = TPLevel(level=3010.0, value=1.0, percent=60.0)
        
        assert tp.level == 3010.0
        assert tp.value == 1.0
        assert tp.percent == 60.0
        assert tp.move_stop is None
    
    def test_initialization_all_fields(self):
        """Test initialization with all fields."""
        tp = TPLevel(level=3010.0, value=1.0, percent=60.0, move_stop=3005.0)
        
        assert tp.level == 3010.0
        assert tp.value == 1.0
        assert tp.percent == 60.0
        assert tp.move_stop == 3005.0
    
    def test_dataclass_conversion(self):
        """Test conversion to dict."""
        tp = TPLevel(level=3010.0, value=1.0, percent=60.0, move_stop=3005.0)
        tp_dict = asdict(tp)
        
        expected = {
            'level': 3010.0,
            'value': 1.0,
            'percent': 60.0,
            'move_stop': 3005.0
        }
        
        assert tp_dict == expected


class TestTakeProfitResult:
    """Test suite for TakeProfitResult DTO."""
    
    def test_fixed_tp_initialization(self):
        """Test initialization for fixed take profit."""
        tp = TakeProfitResult(
            type="fixed",
            level=3010.0,
            percent=100.0
        )
        
        assert tp.type == "fixed"
        assert tp.level == 3010.0
        assert tp.percent == 100.0
        assert tp.source is None
        assert tp.targets is None
    
    def test_multi_target_tp_initialization(self):
        """Test initialization for multi-target take profit."""
        targets = [
            TPLevel(level=3010.0, value=1.0, percent=60.0),
            TPLevel(level=3020.0, value=2.0, percent=40.0)
        ]
        
        tp = TakeProfitResult(
            type="multi_target",
            targets=targets
        )
        
        assert tp.type == "multi_target"
        assert tp.targets == targets
        assert len(tp.targets) == 2
        assert tp.level is None
        assert tp.source is None
    
    def test_indicator_tp_initialization(self):
        """Test initialization for indicator-based take profit."""
        tp = TakeProfitResult(
            type="indicator",
            source="ema_20"
        )
        
        assert tp.type == "indicator"
        assert tp.source == "ema_20"
        assert tp.level is None
        assert tp.targets is None
    
    def test_invalid_type_literal(self):
        """Test that type field accepts only valid literals."""
        # This should work
        tp = TakeProfitResult(type="fixed", level=3010.0)
        assert tp.type == "fixed"
        
        # Type hints don't prevent assignment in Python, but IDEs will warn
        # The Literal type is mainly for documentation and IDE support


class TestStopLossResult:
    """Test suite for StopLossResult DTO."""
    
    def test_fixed_stop_loss(self):
        """Test initialization for fixed stop loss."""
        sl = StopLossResult(
            type="fixed",
            level=2995.0,
            trailing=False
        )
        
        assert sl.type == "fixed"
        assert sl.level == 2995.0
        assert sl.trailing is False
        assert sl.step is None
        assert sl.source is None
    
    def test_trailing_stop_loss(self):
        """Test initialization for trailing stop loss."""
        sl = StopLossResult(
            type="fixed",
            level=2995.0,
            trailing=True,
            step=0.5
        )
        
        assert sl.type == "fixed"
        assert sl.level == 2995.0
        assert sl.trailing is True
        assert sl.step == 0.5
        assert sl.source is None
    
    def test_indicator_stop_loss(self):
        """Test initialization for indicator-based stop loss."""
        sl = StopLossResult(
            type="indicator",
            level=2990.0,
            source="atr_stop"
        )
        
        assert sl.type == "indicator"
        assert sl.level == 2990.0
        assert sl.source == "atr_stop"
        assert sl.trailing is None
        assert sl.step is None
    
    def test_dataclass_conversion(self):
        """Test conversion to dict."""
        sl = StopLossResult(
            type="fixed",
            level=2995.0,
            trailing=True,
            step=0.5
        )
        
        sl_dict = asdict(sl)
        
        expected = {
            'type': 'fixed',
            'level': 2995.0,
            'trailing': True,
            'step': 0.5,
            'source': None
        }
        
        assert sl_dict == expected


class TestEntryDecision:
    """Test suite for EntryDecision DTO."""
    
    @pytest.fixture
    def sample_entry_decision(self):
        """Create a sample entry decision."""
        return EntryDecision(
            symbol='XAUUSD',
            strategy_name='test_strategy',
            magic=12345,
            direction='long',
            entry_signals='BUY',
            entry_price=3000.0,
            position_size=1.0,
            stop_loss=StopLossResult(type='fixed', level=2995.0, trailing=False),
            take_profit=TakeProfitResult(type='fixed', level=3010.0, percent=100.0),
            decision_time=datetime(2024, 1, 1, 12, 0, 0)
        )
    
    def test_initialization(self, sample_entry_decision):
        """Test initialization with all required fields."""
        entry = sample_entry_decision
        
        assert entry.symbol == 'XAUUSD'
        assert entry.strategy_name == 'test_strategy'
        assert entry.magic == 12345
        assert entry.direction == 'long'
        assert entry.entry_signals == 'BUY'
        assert entry.entry_price == 3000.0
        assert entry.position_size == 1.0
        assert entry.stop_loss.level == 2995.0
        assert entry.take_profit.level == 3010.0
        assert entry.decision_time == datetime(2024, 1, 1, 12, 0, 0)
    
    def test_entry_signals_literals(self):
        """Test that entry_signals accepts valid literals."""
        valid_signals = ['BUY', 'SELL', 'BUY_LIMIT', 'SELL_LIMIT']
        
        for signal in valid_signals:
            entry = EntryDecision(
                symbol='XAUUSD',
                strategy_name='test',
                magic=12345,
                direction='long',
                entry_signals=signal,
                entry_price=3000.0,
                position_size=1.0,
                stop_loss=StopLossResult(type='fixed', level=2995.0),
                take_profit=TakeProfitResult(type='fixed', level=3010.0),
                decision_time=datetime.now()
            )
            assert entry.entry_signals == signal
    
    def test_nested_dataclasses(self, sample_entry_decision):
        """Test that nested dataclasses are properly stored."""
        entry = sample_entry_decision
        
        # Check stop loss
        assert isinstance(entry.stop_loss, StopLossResult)
        assert entry.stop_loss.type == 'fixed'
        assert entry.stop_loss.level == 2995.0
        
        # Check take profit
        assert isinstance(entry.take_profit, TakeProfitResult)
        assert entry.take_profit.type == 'fixed'
        assert entry.take_profit.level == 3010.0
    
    def test_dataclass_conversion(self, sample_entry_decision):
        """Test conversion to dict."""
        entry_dict = asdict(sample_entry_decision)
        
        assert entry_dict['symbol'] == 'XAUUSD'
        assert entry_dict['strategy_name'] == 'test_strategy'
        assert entry_dict['magic'] == 12345
        assert entry_dict['stop_loss']['level'] == 2995.0
        assert entry_dict['take_profit']['level'] == 3010.0
    
    def test_multi_target_take_profit(self):
        """Test entry decision with multi-target take profit."""
        targets = [
            TPLevel(level=3010.0, value=1.0, percent=60.0, move_stop=3005.0),
            TPLevel(level=3020.0, value=2.0, percent=40.0)
        ]
        
        entry = EntryDecision(
            symbol='XAUUSD',
            strategy_name='multi_tp_strategy',
            magic=12345,
            direction='long',
            entry_signals='BUY',
            entry_price=3000.0,
            position_size=1.0,
            stop_loss=StopLossResult(type='fixed', level=2995.0),
            take_profit=TakeProfitResult(type='multi_target', targets=targets),
            decision_time=datetime.now()
        )
        
        assert entry.take_profit.type == 'multi_target'
        assert len(entry.take_profit.targets) == 2
        assert entry.take_profit.targets[0].level == 3010.0
        assert entry.take_profit.targets[0].move_stop == 3005.0


class TestExitDecision:
    """Test suite for ExitDecision DTO."""
    
    def test_initialization(self):
        """Test initialization with all required fields."""
        exit_decision = ExitDecision(
            symbol='BTCUSD',
            strategy_name='btc_strategy',
            magic=67890,
            direction='short',
            decision_time=datetime(2024, 1, 1, 13, 0, 0)
        )
        
        assert exit_decision.symbol == 'BTCUSD'
        assert exit_decision.strategy_name == 'btc_strategy'
        assert exit_decision.magic == 67890
        assert exit_decision.direction == 'short'
        assert exit_decision.decision_time == datetime(2024, 1, 1, 13, 0, 0)
    
    def test_direction_literals(self):
        """Test that direction accepts valid literals."""
        valid_directions = ['long', 'short']
        
        for direction in valid_directions:
            exit_decision = ExitDecision(
                symbol='XAUUSD',
                strategy_name='test',
                magic=12345,
                direction=direction,
                decision_time=datetime.now()
            )
            assert exit_decision.direction == direction
    
    def test_dataclass_conversion(self):
        """Test conversion to dict."""
        exit_decision = ExitDecision(
            symbol='EURUSD',
            strategy_name='eur_strategy',
            magic=11111,
            direction='long',
            decision_time=datetime(2024, 1, 1, 14, 0, 0)
        )
        
        exit_dict = asdict(exit_decision)
        
        expected = {
            'symbol': 'EURUSD',
            'strategy_name': 'eur_strategy',
            'magic': 11111,
            'direction': 'long',
            'decision_time': datetime(2024, 1, 1, 14, 0, 0)
        }
        
        assert exit_dict == expected
    
    def test_equality(self):
        """Test equality comparison."""
        time = datetime.now()
        
        exit1 = ExitDecision(
            symbol='XAUUSD',
            strategy_name='test',
            magic=12345,
            direction='long',
            decision_time=time
        )
        
        exit2 = ExitDecision(
            symbol='XAUUSD',
            strategy_name='test',
            magic=12345,
            direction='long',
            decision_time=time
        )
        
        exit3 = ExitDecision(
            symbol='BTCUSD',  # Different symbol
            strategy_name='test',
            magic=12345,
            direction='long',
            decision_time=time
        )
        
        assert exit1 == exit2
        assert exit1 != exit3


class TestTrades:
    """Test suite for Trades DTO."""
    
    @pytest.fixture
    def sample_entries(self):
        """Create sample entry decisions."""
        return [
            EntryDecision(
                symbol='XAUUSD',
                strategy_name='gold_strategy',
                magic=12345,
                direction='long',
                entry_signals='BUY',
                entry_price=3000.0,
                position_size=1.0,
                stop_loss=StopLossResult(type='fixed', level=2995.0),
                take_profit=TakeProfitResult(type='fixed', level=3010.0),
                decision_time=datetime.now()
            ),
            EntryDecision(
                symbol='BTCUSD',
                strategy_name='btc_strategy',
                magic=67890,
                direction='short',
                entry_signals='SELL',
                entry_price=117400.0,
                position_size=0.5,
                stop_loss=StopLossResult(type='fixed', level=117900.0),
                take_profit=TakeProfitResult(type='fixed', level=116900.0),
                decision_time=datetime.now()
            )
        ]
    
    @pytest.fixture
    def sample_exits(self):
        """Create sample exit decisions."""
        return [
            ExitDecision(
                symbol='EURUSD',
                strategy_name='eur_strategy',
                magic=11111,
                direction='long',
                decision_time=datetime.now()
            ),
            ExitDecision(
                symbol='GBPUSD',
                strategy_name='gbp_strategy',
                magic=22222,
                direction='short',
                decision_time=datetime.now()
            )
        ]
    
    def test_initialization(self, sample_entries, sample_exits):
        """Test initialization with entries and exits."""
        trades = Trades(entries=sample_entries, exits=sample_exits)
        
        assert len(trades.entries) == 2
        assert len(trades.exits) == 2
        assert trades.entries == sample_entries
        assert trades.exits == sample_exits
    
    def test_empty_initialization(self):
        """Test initialization with empty lists."""
        trades = Trades(entries=[], exits=[])
        
        assert trades.entries == []
        assert trades.exits == []
        assert len(trades.entries) == 0
        assert len(trades.exits) == 0
    
    def test_only_entries(self, sample_entries):
        """Test initialization with only entries."""
        trades = Trades(entries=sample_entries, exits=[])
        
        assert len(trades.entries) == 2
        assert len(trades.exits) == 0
    
    def test_only_exits(self, sample_exits):
        """Test initialization with only exits."""
        trades = Trades(entries=[], exits=sample_exits)
        
        assert len(trades.entries) == 0
        assert len(trades.exits) == 2
    
    def test_dataclass_conversion(self, sample_entries, sample_exits):
        """Test conversion to dict."""
        trades = Trades(entries=sample_entries, exits=sample_exits)
        trades_dict = asdict(trades)
        
        assert 'entries' in trades_dict
        assert 'exits' in trades_dict
        assert len(trades_dict['entries']) == 2
        assert len(trades_dict['exits']) == 2
        
        # Check nested structure
        assert trades_dict['entries'][0]['symbol'] == 'XAUUSD'
        assert trades_dict['exits'][0]['symbol'] == 'EURUSD'