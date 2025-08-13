"""
Mock strategy configurations for testing the entry manager.
"""

from app.strategy_builder.core.domain.models import (
    TradingStrategy,
    RiskManagement,
    PositionSizing,
    FixedStopLoss,
    IndicatorBasedSlTp,
    TrailingStopLossOnly,
    FixedTakeProfit,
    MultiTargetTakeProfit,
    TakeProfitTarget,
    EntryDirectionalRules,
    EntryRules,
    ExitDirectionalRules,
    ExitRules,
    Condition
)
from app.strategy_builder.core.domain.enums import (
    TimeFrameEnum,
    LogicModeEnum,
    PositionSizingTypeEnum,
    ConditionOperatorEnum
)


def create_basic_strategy(
    name: str = "test_strategy",
    position_sizing_type: PositionSizingTypeEnum = PositionSizingTypeEnum.FIXED,
    position_sizing_value: float = 1000.0,
    stop_loss_type: str = "fixed",
    stop_loss_value: float = 50.0,
    take_profit_type: str = "fixed",
    take_profit_value: float = 100.0
) -> TradingStrategy:
    """Create a basic strategy for testing."""
    return TradingStrategy(
        name=name,
        timeframes=[TimeFrameEnum.M1, TimeFrameEnum.M5],
        entry=EntryDirectionalRules(
            long=EntryRules(
                mode=LogicModeEnum.ALL,
                conditions=[
                    Condition(
                        signal="RSI",
                        operator=ConditionOperatorEnum.GT,
                        value=30.0,
                        timeframe=TimeFrameEnum.M1
                    )
                ]
            ),
            short=EntryRules(
                mode=LogicModeEnum.ALL,
                conditions=[
                    Condition(
                        signal="RSI",
                        operator=ConditionOperatorEnum.LT,
                        value=70.0,
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
                        signal="RSI",
                        operator=ConditionOperatorEnum.GT,
                        value=70.0,
                        timeframe=TimeFrameEnum.M1
                    )
                ]
            ),
            short=ExitRules(
                mode=LogicModeEnum.ANY,
                conditions=[
                    Condition(
                        signal="RSI",
                        operator=ConditionOperatorEnum.LT,
                        value=30.0,
                        timeframe=TimeFrameEnum.M1
                    )
                ]
            )
        ),
        risk=RiskManagement(
            position_sizing=PositionSizing(
                type=position_sizing_type,
                value=position_sizing_value
            ),
            sl=FixedStopLoss(
                type=stop_loss_type,
                value=stop_loss_value
            ),
            tp=FixedTakeProfit(
                type=take_profit_type,
                value=take_profit_value
            )
        )
    )


def create_percentage_strategy(
    name: str = "percentage_strategy",
    percentage: float = 2.5,
    account_balance: float = 10000.0
) -> TradingStrategy:
    """Create a strategy with percentage position sizing."""
    return TradingStrategy(
        name=name,
        timeframes=[TimeFrameEnum.M15],
        entry=EntryDirectionalRules(
            long=EntryRules(
                mode=LogicModeEnum.ALL,
                conditions=[
                    Condition(
                        signal="MA_Cross",
                        operator=ConditionOperatorEnum.EQ,
                        value=1.0,
                        timeframe=TimeFrameEnum.M15
                    )
                ]
            )
        ),
        risk=RiskManagement(
            position_sizing=PositionSizing(
                type=PositionSizingTypeEnum.PERCENTAGE,
                value=percentage
            ),
            sl=FixedStopLoss(
                type="fixed",
                value=30.0
            ),
            tp=FixedTakeProfit(
                type="fixed",
                value=60.0
            )
        )
    )


def create_volatility_strategy(
    name: str = "volatility_strategy",
    base_size: float = 1000.0,
    atr_distance: float = 0.0
) -> TradingStrategy:
    """Create a strategy with volatility-based position sizing."""
    position_sizing = PositionSizing(
        type=PositionSizingTypeEnum.VOLATILITY,
        value=base_size
    )
    if atr_distance > 0:
        position_sizing.atr_distance = atr_distance
    
    return TradingStrategy(
        name=name,
        timeframes=[TimeFrameEnum.H1],
        entry=EntryDirectionalRules(
            long=EntryRules(
                mode=LogicModeEnum.ALL,
                conditions=[
                    Condition(
                        signal="Breakout",
                        operator=ConditionOperatorEnum.EQ,
                        value=1.0,
                        timeframe=TimeFrameEnum.H1
                    )
                ]
            )
        ),
        risk=RiskManagement(
            position_sizing=position_sizing,
            sl=IndicatorBasedSlTp(
                type="indicator",
                source="ATR",
                offset=1.5,
                timeframe=TimeFrameEnum.H1
            ),
            tp=FixedTakeProfit(
                type="fixed",
                value=150.0
            )
        )
    )


def create_trailing_stop_strategy(
    name: str = "trailing_strategy",
    trail_distance: float = 20.0,
    trail_step: float = 5.0
) -> TradingStrategy:
    """Create a strategy with trailing stop loss."""
    return TradingStrategy(
        name=name,
        timeframes=[TimeFrameEnum.M30],
        entry=EntryDirectionalRules(
            long=EntryRules(
                mode=LogicModeEnum.ALL,
                conditions=[
                    Condition(
                        signal="Momentum",
                        operator=ConditionOperatorEnum.GT,
                        value=0.0,
                        timeframe=TimeFrameEnum.M30
                    )
                ]
            )
        ),
        risk=RiskManagement(
            position_sizing=PositionSizing(
                type=PositionSizingTypeEnum.FIXED,
                value=2000.0
            ),
            sl=TrailingStopLossOnly(
                type="trailing",
                step=trail_step
            ),
            tp=FixedTakeProfit(
                type="fixed",
                value=100.0
            )
        )
    )


def create_multi_target_strategy(
    name: str = "multi_target_strategy"
) -> TradingStrategy:
    """Create a strategy with multiple take profit targets."""
    return TradingStrategy(
        name=name,
        timeframes=[TimeFrameEnum.H4],
        entry=EntryDirectionalRules(
            long=EntryRules(
                mode=LogicModeEnum.ALL,
                conditions=[
                    Condition(
                        signal="MACD",
                        operator=ConditionOperatorEnum.GT,
                        value=0.0,
                        timeframe=TimeFrameEnum.H4
                    )
                ]
            )
        ),
        risk=RiskManagement(
            position_sizing=PositionSizing(
                type=PositionSizingTypeEnum.FIXED,
                value=3000.0
            ),
            sl=FixedStopLoss(
                type="fixed",
                value=40.0
            ),
            tp=MultiTargetTakeProfit(
                type="multi_target",
                targets=[
                    TakeProfitTarget(value=50.0, percent=33.33),
                    TakeProfitTarget(value=100.0, percent=33.33),
                    TakeProfitTarget(value=150.0, percent=33.34)
                ]
            )
        )
    )


def create_invalid_strategy_no_risk(name: str = "invalid_no_risk") -> dict:
    """Create an invalid strategy without risk management (as dict)."""
    return {
        "name": name,
        "timeframes": ["M1"],
        "entry": {
            "long": {
                "mode": "ALL",
                "conditions": [
                    {
                        "signal": "RSI",
                        "operator": ">",
                        "value": 30.0,
                        "timeframe": "M1"
                    }
                ]
            }
        }
        # Missing risk management
    }


def create_invalid_strategy_no_sl(name: str = "invalid_no_sl") -> dict:
    """Create an invalid strategy without stop loss (as dict)."""
    return {
        "name": name,
        "timeframes": ["M1"],
        "entry": {
            "long": {
                "mode": "ALL",
                "conditions": [
                    {
                        "signal": "RSI",
                        "operator": ">",
                        "value": 30.0,
                        "timeframe": "M1"
                    }
                ]
            }
        },
        "risk": {
            "position_sizing": {
                "type": "FIXED",
                "value": 1000.0
            },
            # Missing stop loss
            "tp": {
                "type": "fixed",
                "value": 100.0
            }
        }
    }


def create_multiple_strategies() -> dict:
    """Create multiple strategies for testing strategy management."""
    return {
        "conservative": create_basic_strategy(
            name="conservative",
            position_sizing_value=500.0,
            stop_loss_value=20.0,
            take_profit_value=40.0
        ),
        "aggressive": create_basic_strategy(
            name="aggressive",
            position_sizing_value=2000.0,
            stop_loss_value=100.0,
            take_profit_value=200.0
        ),
        "scalping": create_basic_strategy(
            name="scalping",
            position_sizing_value=1500.0,
            stop_loss_value=10.0,
            take_profit_value=15.0
        )
    }