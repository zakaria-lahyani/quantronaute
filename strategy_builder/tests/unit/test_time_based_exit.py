"""
Unit tests for time-based exit functionality.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock

from strategy_builder.core.evaluators.logic import LogicEvaluator
from strategy_builder.core.domain.models import ExitRules, TimeBasedExit
from strategy_builder.core.domain.enums import LogicModeEnum
from strategy_builder.infrastructure.logging import create_null_logger


class TestTimeBasedExit(unittest.TestCase):
    """Test cases for time-based exit functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_condition_evaluator = Mock()
        self.mock_condition_evaluator.evaluate.return_value = True
        
        # Position data for testing
        self.position_data = {
            'entry_time': datetime.now() - timedelta(hours=2),  # Position opened 2 hours ago
            'strategy_name': 'test_strategy',
            'direction': 'long'
        }
        
        self.logic_evaluator = LogicEvaluator(
            self.mock_condition_evaluator,
            self.position_data
        )
    
    def test_max_duration_exceeded(self):
        """Test exit when maximum duration is exceeded."""
        exit_rules = ExitRules(
            mode=LogicModeEnum.ANY,
            conditions=[],  # No regular conditions
            time_based=TimeBasedExit(max_duration="1h")  # Max 1 hour, but position is 2 hours old
        )
        
        result = self.logic_evaluator.evaluate_exit_rules(exit_rules)
        self.assertTrue(result)  # Should trigger exit due to max duration
    
    def test_max_duration_not_exceeded(self):
        """Test no exit when maximum duration is not exceeded."""
        exit_rules = ExitRules(
            mode=LogicModeEnum.ANY,
            conditions=[],  # No regular conditions
            time_based=TimeBasedExit(max_duration="4h")  # Max 4 hours, position is 2 hours old
        )
        
        result = self.logic_evaluator.evaluate_exit_rules(exit_rules)
        self.assertFalse(result)  # Should not trigger exit
    
    def test_min_duration_validation(self):
        """Test minimum duration validation."""
        # Position opened 30 minutes ago
        recent_position_data = {
            'entry_time': datetime.now() - timedelta(minutes=30),
            'strategy_name': 'test_strategy',
            'direction': 'long'
        }
        
        logic_evaluator = LogicEvaluator(
            self.mock_condition_evaluator,
            recent_position_data
        )
        
        exit_rules = ExitRules(
            mode=LogicModeEnum.ANY,
            conditions=[],
            time_based=TimeBasedExit(
                max_duration="4h",
                min_duration="1h"  # Min 1 hour, but position is only 30 minutes old
            )
        )
        
        result = logic_evaluator.evaluate_exit_rules(exit_rules)
        self.assertFalse(result)  # Should not trigger exit due to min duration
    
    def test_parse_duration_formats(self):
        """Test duration parsing for different formats."""
        # Test minutes
        duration = self.logic_evaluator._parse_duration("30m")
        self.assertEqual(duration, timedelta(minutes=30))
        
        # Test hours
        duration = self.logic_evaluator._parse_duration("2h")
        self.assertEqual(duration, timedelta(hours=2))
        
        # Test days
        duration = self.logic_evaluator._parse_duration("1d")
        self.assertEqual(duration, timedelta(days=1))
        
        # Test weeks
        duration = self.logic_evaluator._parse_duration("1w")
        self.assertEqual(duration, timedelta(weeks=1))
    
    def test_invalid_duration_format(self):
        """Test error handling for invalid duration formats."""
        with self.assertRaises(ValueError):
            self.logic_evaluator._parse_duration("invalid")
        
        with self.assertRaises(ValueError):
            self.logic_evaluator._parse_duration("2x")  # Invalid unit
    
    def test_no_position_data(self):
        """Test behavior when no position data is available."""
        logic_evaluator = LogicEvaluator(self.mock_condition_evaluator)  # No position data
        
        exit_rules = ExitRules(
            mode=LogicModeEnum.ANY,
            conditions=[],
            time_based=TimeBasedExit(max_duration="1h")
        )
        
        result = logic_evaluator.evaluate_exit_rules(exit_rules)
        self.assertFalse(result)  # Should not trigger exit without position data
    
    def test_combined_conditions_and_time_based(self):
        """Test combination of regular conditions and time-based exit."""
        # Mock condition evaluator to return False for regular conditions
        self.mock_condition_evaluator.evaluate.return_value = False
        
        from strategy_builder.core.domain.models import Condition
        from strategy_builder.core.domain.enums import ConditionOperatorEnum, TimeFrameEnum
        
        exit_rules = ExitRules(
            mode=LogicModeEnum.ANY,
            conditions=[
                Condition(
                    signal="profit",
                    operator=ConditionOperatorEnum.GT,
                    value=100,
                    timeframe=TimeFrameEnum.M1
                )
            ],
            time_based=TimeBasedExit(max_duration="1h")  # Should trigger
        )
        
        result = self.logic_evaluator.evaluate_exit_rules(exit_rules)
        self.assertTrue(result)  # Should trigger due to time-based exit even though condition is False


if __name__ == '__main__':
    unittest.main()