"""
Mock strategy configurations for testing.
"""
from app.strategy_builder.core.domain.enums import TimeFrameEnum, LogicModeEnum, ConditionOperatorEnum
from app.strategy_builder.core.domain.models import (
    TradingStrategy,
    EntryDirectionalRules,
    EntryRules,
    ExitDirectionalRules,
    ExitRules,
    Condition,
    RiskManagement,
    FixedStopLoss,
    FixedTakeProfit
)


def create_simple_strategy() -> TradingStrategy:
    """
    Create a simple strategy for testing.
    
    Returns:
        Simple TradingStrategy instance
    """
    return TradingStrategy(
        name="test_simple_strategy",
        timeframes=[TimeFrameEnum.M1, TimeFrameEnum.M5],
        entry=EntryDirectionalRules(
            long=EntryRules(
                mode=LogicModeEnum.ALL,
                conditions=[
                    Condition(
                        signal="rsi",
                        operator=ConditionOperatorEnum.LT,
                        value=30,
                        timeframe=TimeFrameEnum.M1
                    ),
                    Condition(
                        signal="close",
                        operator=ConditionOperatorEnum.GT,
                        value="ma_20",
                        timeframe=TimeFrameEnum.M1
                    )
                ]
            )
        ),
        risk=RiskManagement(
            sl=FixedStopLoss(type="fixed", value=50.0),
            tp=FixedTakeProfit(type="fixed", value=100.0)
        )
    )


def create_complex_strategy() -> TradingStrategy:
    """
    Create a complex strategy with multiple conditions for testing.
    
    Returns:
        Complex TradingStrategy instance
    """
    return TradingStrategy(
        name="test_complex_strategy",
        timeframes=[TimeFrameEnum.M1, TimeFrameEnum.M5, TimeFrameEnum.H1],
        entry=EntryDirectionalRules(
            long=EntryRules(
                mode=LogicModeEnum.ANY,
                conditions=[
                    Condition(
                        signal="rsi",
                        operator=ConditionOperatorEnum.CROSSES_ABOVE,
                        value=70,
                        timeframe=TimeFrameEnum.M1
                    ),
                    Condition(
                        signal="signal_strength",
                        operator=ConditionOperatorEnum.GTE,
                        value=0.8,
                        timeframe=TimeFrameEnum.M5
                    )
                ]
            ),
            short=EntryRules(
                mode=LogicModeEnum.ALL,
                conditions=[
                    Condition(
                        signal="rsi",
                        operator=ConditionOperatorEnum.GT,
                        value=70,
                        timeframe=TimeFrameEnum.M1
                    ),
                    Condition(
                        signal="close",
                        operator=ConditionOperatorEnum.LT,
                        value="ma_20",
                        timeframe=TimeFrameEnum.M1
                    )
                ]
            )
        ),
        exit=ExitDirectionalRules(
            long=ExitRules(
                mode=LogicModeEnum.ANY,
                conditions=[
                    Condition(
                        signal="rsi",
                        operator=ConditionOperatorEnum.GT,
                        value=80,
                        timeframe=TimeFrameEnum.M1
                    )
                ]
            )
        ),
        risk=RiskManagement(
            sl=FixedStopLoss(type="fixed", value=30.0),
            tp=FixedTakeProfit(type="fixed", value=60.0)
        )
    )


def create_strategy_config_dict() -> dict:
    """
    Create a strategy configuration as dictionary (for testing config loading).
    
    Returns:
        Strategy configuration dictionary
    """
    return {
        "name": "test_config_strategy",
        "timeframes": ["1", "5"],
        "entry": {
            "long": {
                "mode": "all",
                "conditions": [
                    {
                        "signal": "rsi",
                        "operator": "<",
                        "value": 30,
                        "timeframe": "1"
                    }
                ]
            }
        },
        "risk": {
            "sl": {
                "type": "fixed",
                "value": 50.0
            },
            "tp": {
                "type": "fixed", 
                "value": 100.0
            }
        }
    }


def create_invalid_strategy_config() -> dict:
    """
    Create an invalid strategy configuration for testing validation.
    
    Returns:
        Invalid strategy configuration dictionary
    """
    return {
        "name": "",  # Invalid: empty name
        "timeframes": [],  # Invalid: empty timeframes
        "entry": {
            "long": {
                "mode": "invalid_mode",  # Invalid mode
                "conditions": []
            }
        },
        "risk": {
            "sl": {
                "type": "fixed",
                "value": -10.0  # Invalid: negative value
            },
            "tp": {
                "type": "fixed",
                "value": -20.0  # Invalid: negative value
            }
        }
    }