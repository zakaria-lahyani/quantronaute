"""
Pytest configuration and fixtures for data package tests.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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


# Fixture groups for different testing scenarios

@pytest.fixture
def base_datetime():
    """Provide a consistent base datetime for tests."""
    return datetime(2024, 1, 1, 12, 0, 0)


@pytest.fixture
def sample_signal_results():
    """Create sample signal results."""
    return {
        'bullish': SignalResult(long=True, short=False),
        'bearish': SignalResult(long=False, short=True),
        'neutral': SignalResult(long=False, short=False),
        'conflicted': SignalResult(long=True, short=True),
        'empty': SignalResult()
    }


@pytest.fixture
def sample_tp_levels():
    """Create sample take profit levels."""
    return [
        TPLevel(level=3010.0, value=0.5, percent=30.0, move_stop=3005.0),
        TPLevel(level=3020.0, value=1.0, percent=40.0, move_stop=3010.0),
        TPLevel(level=3030.0, value=1.5, percent=30.0)
    ]


@pytest.fixture
def sample_take_profits(sample_tp_levels):
    """Create various take profit configurations."""
    return {
        'fixed': TakeProfitResult(
            type='fixed',
            level=3010.0,
            percent=100.0
        ),
        'multi_target': TakeProfitResult(
            type='multi_target',
            targets=sample_tp_levels
        ),
        'indicator': TakeProfitResult(
            type='indicator',
            source='ema_20'
        ),
        'minimal': TakeProfitResult(
            type='fixed',
            level=3010.0
        )
    }


@pytest.fixture
def sample_stop_losses():
    """Create various stop loss configurations."""
    return {
        'fixed': StopLossResult(
            type='fixed',
            level=2995.0,
            trailing=False
        ),
        'trailing': StopLossResult(
            type='fixed',
            level=2995.0,
            trailing=True,
            step=5.0
        ),
        'indicator': StopLossResult(
            type='indicator',
            level=2990.0,
            source='atr_stop'
        ),
        'tight': StopLossResult(
            type='fixed',
            level=2998.0,
            trailing=False
        )
    }


@pytest.fixture
def gold_entry_decision(base_datetime, sample_stop_losses, sample_take_profits):
    """Create a standard gold entry decision."""
    return EntryDecision(
        symbol='XAUUSD',
        strategy_name='gold_momentum',
        magic=12345,
        direction='long',
        entry_signals='BUY',
        entry_price=3000.0,
        position_size=1.0,
        stop_loss=sample_stop_losses['fixed'],
        take_profit=sample_take_profits['fixed'],
        decision_time=base_datetime
    )


@pytest.fixture
def bitcoin_entry_decision(base_datetime, sample_stop_losses, sample_take_profits):
    """Create a standard bitcoin entry decision."""
    return EntryDecision(
        symbol='BTCUSD',
        strategy_name='btc_breakout',
        magic=67890,
        direction='short',
        entry_signals='SELL',
        entry_price=117000.0,
        position_size=0.1,
        stop_loss=StopLossResult(type='fixed', level=117500.0),
        take_profit=TakeProfitResult(type='fixed', level=116000.0),
        decision_time=base_datetime + timedelta(minutes=30)
    )


@pytest.fixture
def forex_entry_decision(base_datetime, sample_take_profits):
    """Create a forex entry decision with multi-target TP."""
    return EntryDecision(
        symbol='EURUSD',
        strategy_name='eur_scalping',
        magic=11111,
        direction='long',
        entry_signals='BUY_LIMIT',
        entry_price=1.0800,
        position_size=100000.0,
        stop_loss=StopLossResult(type='fixed', level=1.0750),
        take_profit=sample_take_profits['multi_target'],
        decision_time=base_datetime + timedelta(hours=1)
    )


@pytest.fixture
def sample_entry_decisions(gold_entry_decision, bitcoin_entry_decision, forex_entry_decision):
    """Create a list of sample entry decisions."""
    return [gold_entry_decision, bitcoin_entry_decision, forex_entry_decision]


@pytest.fixture
def sample_exit_decisions(base_datetime):
    """Create sample exit decisions."""
    return [
        ExitDecision(
            symbol='XAUUSD',
            strategy_name='gold_momentum',
            magic=12345,
            direction='long',
            decision_time=base_datetime + timedelta(hours=2)
        ),
        ExitDecision(
            symbol='BTCUSD',
            strategy_name='btc_breakout',
            magic=67890,
            direction='short',
            decision_time=base_datetime + timedelta(hours=1, minutes=45)
        ),
        ExitDecision(
            symbol='EURUSD',
            strategy_name='eur_scalping',
            magic=11111,
            direction='long',
            decision_time=base_datetime + timedelta(hours=3)
        )
    ]


@pytest.fixture
def sample_trades(sample_entry_decisions, sample_exit_decisions):
    """Create a Trades object with sample data."""
    return Trades(entries=sample_entry_decisions, exits=sample_exit_decisions)


@pytest.fixture
def strategy_evaluation_results(sample_signal_results):
    """Create sample strategy evaluation results."""
    return {
        'trend_following': StrategyEvaluationResult(
            strategy_name='trend_following',
            entry=sample_signal_results['bullish'],
            exit=sample_signal_results['neutral']
        ),
        'mean_reversion': StrategyEvaluationResult(
            strategy_name='mean_reversion',
            entry=sample_signal_results['bearish'],
            exit=sample_signal_results['neutral']
        ),
        'momentum': StrategyEvaluationResult(
            strategy_name='momentum',
            entry=sample_signal_results['neutral'],
            exit=sample_signal_results['bullish']
        ),
        'breakout': StrategyEvaluationResult(
            strategy_name='breakout',
            entry=sample_signal_results['conflicted'],
            exit=sample_signal_results['neutral']
        )
    }


@pytest.fixture
def all_strategies_result(strategy_evaluation_results):
    """Create AllStrategiesEvaluationResult with sample data."""
    return AllStrategiesEvaluationResult(strategies=strategy_evaluation_results)


# Data validation fixtures

@pytest.fixture
def valid_entry_data():
    """Provide valid entry decision data for testing."""
    return {
        'symbol': 'XAUUSD',
        'strategy_name': 'test_strategy',
        'magic': 12345,
        'direction': 'long',
        'entry_signals': 'BUY',
        'entry_price': 3000.0,
        'position_size': 1.0,
        'stop_loss': StopLossResult(type='fixed', level=2995.0),
        'take_profit': TakeProfitResult(type='fixed', level=3010.0),
        'decision_time': datetime.now()
    }


@pytest.fixture
def invalid_entry_data():
    """Provide invalid entry decision data for testing."""
    return {
        'missing_symbol': {
            # 'symbol': 'XAUUSD',  # Missing
            'strategy_name': 'test',
            'magic': 12345,
            'direction': 'long',
            'entry_signals': 'BUY',
            'entry_price': 3000.0,
            'position_size': 1.0,
            'stop_loss': StopLossResult(type='fixed', level=2995.0),
            'take_profit': TakeProfitResult(type='fixed', level=3010.0),
            'decision_time': datetime.now()
        },
        'negative_position_size': {
            'symbol': 'XAUUSD',
            'strategy_name': 'test',
            'magic': 12345,
            'direction': 'long',
            'entry_signals': 'BUY',
            'entry_price': 3000.0,
            'position_size': -1.0,  # Negative
            'stop_loss': StopLossResult(type='fixed', level=2995.0),
            'take_profit': TakeProfitResult(type='fixed', level=3010.0),
            'decision_time': datetime.now()
        }
    }


# Performance and load testing fixtures

@pytest.fixture
def large_dataset():
    """Create a large dataset for performance testing."""
    entries = []
    exits = []
    
    symbols = ['XAUUSD', 'BTCUSD', 'EURUSD', 'GBPUSD', 'USDJPY']
    strategies = ['trend', 'momentum', 'breakout', 'scalping', 'swing']
    
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    
    for i in range(100):  # 100 trades
        symbol = symbols[i % len(symbols)]
        strategy = strategies[i % len(strategies)]
        
        entry = EntryDecision(
            symbol=symbol,
            strategy_name=f"{strategy}_strategy",
            magic=10000 + i,
            direction='long' if i % 2 == 0 else 'short',
            entry_signals='BUY' if i % 2 == 0 else 'SELL',
            entry_price=1000.0 + i * 10,
            position_size=round(0.1 + (i % 10) * 0.1, 1),
            stop_loss=StopLossResult(
                type='fixed',
                level=990.0 + i * 10 if i % 2 == 0 else 1010.0 + i * 10
            ),
            take_profit=TakeProfitResult(
                type='fixed',
                level=1015.0 + i * 10 if i % 2 == 0 else 985.0 + i * 10
            ),
            decision_time=base_time + timedelta(hours=i, minutes=i*5)
        )
        entries.append(entry)
        
        exit_decision = ExitDecision(
            symbol=symbol,
            strategy_name=f"{strategy}_strategy",
            magic=10000 + i,
            direction='long' if i % 2 == 0 else 'short',
            decision_time=entry.decision_time + timedelta(hours=2 + i % 5)
        )
        exits.append(exit_decision)
    
    return Trades(entries=entries, exits=exits)


@pytest.fixture
def symbol_configurations():
    """Define symbol-specific configurations for testing."""
    return {
        'XAUUSD': {
            'typical_price': 3000.0,
            'pip_value': 0.01,
            'point_value': 100.0,
            'min_stop_distance': 5.0,
            'typical_spread': 0.3
        },
        'BTCUSD': {
            'typical_price': 117000.0,
            'pip_value': 1.0,
            'point_value': 1.0,
            'min_stop_distance': 50.0,
            'typical_spread': 5.0
        },
        'EURUSD': {
            'typical_price': 1.0800,
            'pip_value': 0.0001,
            'point_value': 10.0,  # For standard lot
            'min_stop_distance': 0.0010,
            'typical_spread': 0.0001
        }
    }


@pytest.fixture
def market_scenarios():
    """Define different market scenarios for testing."""
    return {
        'trending_up': {
            'description': 'Strong uptrend',
            'expected_signals': {'long': True, 'short': False},
            'volatility': 'low',
            'direction': 'up'
        },
        'trending_down': {
            'description': 'Strong downtrend',
            'expected_signals': {'long': False, 'short': True},
            'volatility': 'low',
            'direction': 'down'
        },
        'ranging': {
            'description': 'Sideways market',
            'expected_signals': {'long': False, 'short': False},
            'volatility': 'medium',
            'direction': 'sideways'
        },
        'volatile': {
            'description': 'High volatility market',
            'expected_signals': {'long': True, 'short': True},
            'volatility': 'high',
            'direction': 'mixed'
        }
    }


# Utility fixtures

@pytest.fixture
def json_serializer():
    """Provide a JSON serializer that handles datetime objects."""
    import json
    from datetime import datetime
    
    def datetime_handler(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    def serialize(obj):
        return json.dumps(obj, default=datetime_handler, indent=2)
    
    def deserialize(json_str):
        return json.loads(json_str)
    
    return {'serialize': serialize, 'deserialize': deserialize}


@pytest.fixture
def data_validator():
    """Provide data validation utilities."""
    def validate_entry_decision(entry: EntryDecision) -> List[str]:
        """Validate an entry decision and return list of issues."""
        issues = []
        
        # Basic field validation
        if not entry.symbol:
            issues.append("Symbol is required")
        
        if entry.position_size <= 0:
            issues.append("Position size must be positive")
        
        if entry.entry_price <= 0:
            issues.append("Entry price must be positive")
        
        # Logic validation
        if entry.direction == 'long':
            if entry.stop_loss and entry.stop_loss.level >= entry.entry_price:
                issues.append("Stop loss should be below entry price for long positions")
            
            if entry.take_profit and entry.take_profit.level and entry.take_profit.level <= entry.entry_price:
                issues.append("Take profit should be above entry price for long positions")
        
        elif entry.direction == 'short':
            if entry.stop_loss and entry.stop_loss.level <= entry.entry_price:
                issues.append("Stop loss should be above entry price for short positions")
            
            if entry.take_profit and entry.take_profit.level and entry.take_profit.level >= entry.entry_price:
                issues.append("Take profit should be below entry price for short positions")
        
        # Multi-target validation
        if entry.take_profit and entry.take_profit.type == 'multi_target':
            if not entry.take_profit.targets:
                issues.append("Multi-target TP requires targets")
            else:
                total_percent = sum(t.percent for t in entry.take_profit.targets)
                if abs(total_percent - 100.0) > 0.01:
                    issues.append(f"Multi-target TP percentages should sum to 100%, got {total_percent}%")
        
        return issues
    
    return {'validate_entry': validate_entry_decision}


@pytest.fixture(autouse=True)
def reset_test_state():
    """Reset any global state between tests."""
    # This runs before each test automatically
    yield
    # Cleanup after test if needed
    pass