"""
Unit tests for ConditionEvaluator.
"""

import unittest
import pandas as pd
from collections import deque

from app.strategy_builder.core.domain.enums import TimeFrameEnum, ConditionOperatorEnum
from app.strategy_builder.core.domain.models import Condition
from app.strategy_builder.core.evaluators.condition import ConditionEvaluator
from app.strategy_builder.infrastructure.logging import create_null_logger
from tests.strategy_builder.fixtures.mock_data import create_mock_market_data


class TestConditionEvaluator(unittest.TestCase):
    """Test cases for ConditionEvaluator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = create_null_logger()
        self.market_data = create_mock_market_data()
        self.evaluator = ConditionEvaluator(self.market_data, self.logger)
    
    def test_evaluate_simple_comparison(self):
        """Test simple comparison conditions."""
        condition = Condition(
            signal="rsi",
            operator=ConditionOperatorEnum.GT,
            value=60.0,
            timeframe=TimeFrameEnum.M1
        )
        
        result = self.evaluator.evaluate(condition)
        self.assertTrue(result)  # RSI is 67.2 > 60.0
    
    def test_evaluate_crosses_above(self):
        """Test crosses above condition."""
        condition = Condition(
            signal="rsi",
            operator=ConditionOperatorEnum.CROSSES_ABOVE,
            value=66.0,
            timeframe=TimeFrameEnum.M1
        )
        
        result = self.evaluator.evaluate(condition)
        self.assertTrue(result)  # RSI crossed from 65.5 to 67.2 above 66.0
    
    def test_evaluate_missing_timeframe(self):
        """Test evaluation with missing timeframe data."""
        condition = Condition(
            signal="rsi",
            operator=ConditionOperatorEnum.GT,
            value=60.0,
            timeframe=TimeFrameEnum.D1  # Not in mock data
        )
        
        result = self.evaluator.evaluate(condition)
        self.assertFalse(result)
    
    def test_evaluate_missing_signal(self):
        """Test evaluation with missing signal."""
        condition = Condition(
            signal="nonexistent_signal",
            operator=ConditionOperatorEnum.GT,
            value=60.0,
            timeframe=TimeFrameEnum.M1
        )
        
        result = self.evaluator.evaluate(condition)
        self.assertFalse(result)
    
    def test_evaluate_column_reference_value(self):
        """Test evaluation with column reference as value."""
        condition = Condition(
            signal="close",
            operator=ConditionOperatorEnum.GT,
            value="ma_20",  # Column reference
            timeframe=TimeFrameEnum.M1
        )
        
        result = self.evaluator.evaluate(condition)
        self.assertTrue(result)  # close (1.2348) > ma_20 (1.2342)
    
    def test_evaluate_changes_to(self):
        """Test changes_to condition."""
        # Add specific data for this test
        test_data = deque([
            pd.Series({
                'signal_strength': 0.75,
                'previous_signal_strength': 0.80
            })
        ], maxlen=100)
        
        evaluator = ConditionEvaluator({TimeFrameEnum.M1: test_data}, self.logger)
        
        condition = Condition(
            signal="signal_strength",
            operator=ConditionOperatorEnum.CHANGES_TO,
            value=0.75,
            timeframe=TimeFrameEnum.M1
        )
        
        result = evaluator.evaluate(condition)
        self.assertTrue(result)  # Changed from 0.80 to 0.75
    
    def test_evaluate_remains(self):
        """Test remains condition."""
        # Add specific data for this test
        test_data = deque([
            pd.Series({
                'signal_strength': 0.85,
                'previous_signal_strength': 0.85
            })
        ], maxlen=100)
        
        evaluator = ConditionEvaluator({TimeFrameEnum.M1: test_data}, self.logger)
        
        condition = Condition(
            signal="signal_strength",
            operator=ConditionOperatorEnum.REMAINS,
            value=0.85,
            timeframe=TimeFrameEnum.M1
        )
        
        result = evaluator.evaluate(condition)
        self.assertTrue(result)  # Remained at 0.85


if __name__ == '__main__':
    unittest.main()