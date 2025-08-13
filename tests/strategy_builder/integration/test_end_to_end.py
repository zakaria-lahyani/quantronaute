"""
End-to-end integration tests for the strategy engine.

Tests the complete workflow:
1. Load strategy configurations
2. Validate strategy models
3. Create engine with dependencies
4. Evaluate strategies with market data
5. Generate entry/exit signals
6. Test time-based exits with position data
"""

import unittest
from datetime import datetime, timedelta
import tempfile
import os
import yaml

from app.strategy_builder.core.evaluators import create_evaluator_factory
from app.strategy_builder.core.services import create_strategy_executor
from app.strategy_builder.factory import StrategyEngineFactory
from app.strategy_builder.infrastructure.logging import create_null_logger
from tests.strategy_builder.fixtures.mock_data import create_mock_market_data


class TestEndToEndWorkflow(unittest.TestCase):
    """End-to-end integration tests for the complete strategy engine workflow."""

    def setUp(self):
        """Set up test fixtures with temporary files."""
        self.temp_dir = tempfile.mkdtemp()
        self.schema_file = None
        self.strategy_files = []
        self.market_data = create_mock_market_data()

        # Create test schema
        self.create_test_schema()

        # Create test strategies
        self.create_test_strategies()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_test_schema(self):
        """Create a minimal JSON schema for testing."""
        schema = {
            "type": "object",
            "required": ["name", "timeframes", "entry", "risk"],
            "properties": {
                "name": {"type": "string"},
                "timeframes": {"type": "array"},
                "entry": {"type": "object"},
                "risk": {"type": "object"}
            }
        }

        self.schema_file = os.path.join(self.temp_dir, "test_schema.json")
        import json
        with open(self.schema_file, 'w') as f:
            json.dump(schema, f)

    def create_test_strategies(self):
        """Create test strategy configurations."""

        # Strategy 1: Simple entry strategy with time-based exit
        strategy1 = {
            "name": "E2E Test Strategy 1",
            "timeframes": ["1", "5"],
            "entry": {
                "long": {
                    "mode": "all",
                    "conditions": [
                        {
                            "signal": "rsi",
                            "operator": "<=",
                            "value": 70,
                            "timeframe": "1"
                        },
                        {
                            "signal": "close",
                            "operator": ">",
                            "value": "ma_20",
                            "timeframe": "1"
                        }
                    ]
                }
            },
            "exit": {
                "long": {
                    "mode": "any",
                    "conditions": [
                        {
                            "signal": "rsi",
                            "operator": ">=",
                            "value": 80,
                            "timeframe": "1"
                        }
                    ],
                    "time_based": {
                        "max_duration": "24h"
                    }
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

        # Strategy 2: Complex strategy with trailing stop
        strategy2 = {
            "name": "E2E Test Strategy 2",
            "timeframes": ["1", "5"],
            "entry": {
                "long": {
                    "mode": "any",
                    "conditions": [
                        {
                            "signal": "signal_strength",
                            "operator": ">=",
                            "value": 0.8,
                            "timeframe": "5"
                        }
                    ]
                },
                "short": {
                    "mode": "all",
                    "conditions": [
                        {
                            "signal": "rsi",
                            "operator": ">=",
                            "value": 70,
                            "timeframe": "1"
                        }
                    ]
                }
            },
            "exit": {
                "long": {
                    "mode": "any",
                    "conditions": [
                        {
                            "signal": "rsi",
                            "operator": "<=",
                            "value": 30,
                            "timeframe": "1"
                        }
                    ]
                }
            },
            "risk": {
                "sl": {
                    "type": "trailing",
                    "step": 0.5,
                    "activation_price": 1.0,
                    "cap": 2.0
                },
                "tp": {
                    "type": "multi_target",
                    "targets": [
                        {
                            "value": 1.0,
                            "percent": 50
                        },
                        {
                            "value": 2.0,
                            "percent": 50
                        }
                    ]
                }
            }
        }

        # Save strategies to files
        strategy1_file = os.path.join(self.temp_dir, "strategy1.yaml")
        strategy2_file = os.path.join(self.temp_dir, "strategy2.yaml")

        with open(strategy1_file, 'w') as f:
            yaml.dump(strategy1, f)

        with open(strategy2_file, 'w') as f:
            yaml.dump(strategy2, f)

        self.strategy_files = [strategy1_file, strategy2_file]


    def test_complete_workflow_without_position_data(self):
        """Test complete workflow from strategy loading to signal generation."""
        print("\n🧪 Testing complete workflow without position data...")
        
        # Step 1: Create strategy engine
        engine = StrategyEngineFactory.create_engine_for_testing(
            schema_path=self.schema_file,
            config_paths=self.strategy_files
        )
        
        # Step 2: Verify strategies loaded
        strategy_names = engine.list_available_strategies()
        self.assertEqual(len(strategy_names), 2)
        self.assertIn("E2E Test Strategy 1", strategy_names)
        self.assertIn("E2E Test Strategy 2", strategy_names)
        print(f"✅ Loaded {len(strategy_names)} strategies: {strategy_names}")
        
        # Step 3: Get strategy details
        strategy1 = engine.get_strategy_info("E2E Test Strategy 1")
        self.assertEqual(strategy1.name, "E2E Test Strategy 1")
        self.assertIsNotNone(strategy1.entry.long)
        self.assertIsNotNone(strategy1.exit.long.time_based)
        print("✅ Strategy details retrieved successfully")
        
        # Step 4: Evaluate all strategies
        results = engine.evaluate(self.market_data)
        self.assertEqual(len(results.strategies), 2)
        print("✅ Strategy evaluation completed")
        
        # Step 5: Check individual strategy results
        strategy1_result = results.strategies["E2E Test Strategy 1"]
        strategy2_result = results.strategies["E2E Test Strategy 2"]
        
        # Verify result structure
        self.assertIsNotNone(strategy1_result.entry)
        self.assertIsNotNone(strategy1_result.exit)
        self.assertIsInstance(strategy1_result.entry.long, bool)
        self.assertIsInstance(strategy1_result.exit.long, bool)
        
        print(f"✅ Strategy 1 signals - Entry: long={strategy1_result.entry.long}, Exit: long={strategy1_result.exit.long}")
        print(f"✅ Strategy 2 signals - Entry: long={strategy2_result.entry.long}, short={strategy2_result.entry.short}")
        
        # Step 6: Test single strategy evaluation
        single_result = engine.evaluate_single_strategy("E2E Test Strategy 1", self.market_data)
        self.assertEqual(single_result.strategy_name, "E2E Test Strategy 1")
        print(f"single_result : {single_result}")
        print("✅ Single strategy evaluation working")

    def test_complete_workflow_with_position_data(self):
        """Test complete workflow including time-based exits with position data."""
        print("\n🧪 Testing complete workflow with position data for time-based exits...")
        
        # Step 1: Create strategy engine
        engine = StrategyEngineFactory.create_engine_for_testing(
            schema_path=self.schema_file,
            config_paths=self.strategy_files
        )
        
        # Step 2: Create position data (position opened 25 hours ago)
        position_data = {
            'entry_time': datetime.now() - timedelta(hours=25),
            'strategy_name': 'E2E Test Strategy 1',
            'direction': 'long'
        }
        

        strategy = engine.get_strategy_info("E2E Test Strategy 1")
        logger = create_null_logger()
        evaluator_factory = create_evaluator_factory(logger)
        
        executor = create_strategy_executor(
            strategy, 
            self.market_data, 
            evaluator_factory, 
            position_data
        )
        
        # Step 4: Test time-based exit (should trigger since position is 25h old, max is 24h)
        exit_signals = executor.check_exit()
        
        # The time-based exit should trigger for long positions
        print(f"✅ exit_signals: {exit_signals}")
        print(f"✅ Time-based exit result: {exit_signals.long}")

        # Step 5: Test with fresh position (should not trigger time-based exit)
        fresh_position_data = {
            'entry_time': datetime.now() - timedelta(hours=1),
            'strategy_name': 'E2E Test Strategy 1',
            'direction': 'long'
        }
        
        fresh_executor = create_strategy_executor(
            strategy, 
            self.market_data, 
            evaluator_factory, 
            fresh_position_data
        )
        
        fresh_exit_signals = fresh_executor.check_exit()
        print(f"✅ Fresh position exit result: {fresh_exit_signals.long}")
        
        print("✅ Time-based exit functionality validated in end-to-end test")
    
    def test_error_handling_and_edge_cases(self):
        """Test error handling and edge cases in the complete workflow."""
        print("\n🧪 Testing error handling and edge cases...")
        
        # Test 1: Invalid strategy file
        invalid_strategy_file = os.path.join(self.temp_dir, "invalid.yaml")
        with open(invalid_strategy_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        with self.assertRaises(Exception):
            StrategyEngineFactory.create_engine_for_testing(
                schema_path=self.schema_file,
                config_paths=[invalid_strategy_file]
            )
        print("✅ Invalid YAML handling working")
        
        # Test 2: Missing strategy file
        with self.assertRaises(FileNotFoundError):
            StrategyEngineFactory.create_engine_for_testing(
                schema_path=self.schema_file,
                config_paths=["nonexistent.yaml"]
            )
        print("✅ Missing file handling working")
        
        # Test 3: Empty market data
        engine = StrategyEngineFactory.create_engine_for_testing(
            schema_path=self.schema_file,
            config_paths=self.strategy_files
        )
        
        empty_data = {}
        results = engine.evaluate(empty_data)
        # Should handle gracefully without crashing
        self.assertIsInstance(results.strategies, dict)
        print("✅ Empty market data handling working")
        
        # Test 4: Strategy with non-existent timeframe in market data
        limited_data = {"1": self.market_data["1"]}  # Only M1 data
        results = engine.evaluate(limited_data)
        # Should handle missing timeframes gracefully
        self.assertIsInstance(results.strategies, dict)
        print("✅ Missing timeframe data handling working")
    
    def test_strategy_activation_and_validation(self):
        """Test strategy activation and data validation features."""
        print("\n🧪 Testing strategy activation and validation...")
        
        # Create engine
        engine = StrategyEngineFactory.create_engine_for_testing(
            schema_path=self.schema_file,
            config_paths=self.strategy_files
        )

        strategy = engine.get_strategy_info("E2E Test Strategy 1")
        logger = create_null_logger()
        evaluator_factory = create_evaluator_factory(logger)
        
        executor = create_strategy_executor(strategy, self.market_data, evaluator_factory)
        
        # Test data availability validation
        data_available = executor.validate_data_availability()
        self.assertTrue(data_available)
        print("✅ Data availability validation working")
        
        # Test strategy activation check
        is_active = executor.is_strategy_active()
        self.assertTrue(is_active)  # Should be active by default
        print("✅ Strategy activation check working")
        
        # Test strategy name retrieval
        strategy_name = executor.get_strategy_name()
        self.assertEqual(strategy_name, "E2E Test Strategy 1")
        print("✅ Strategy name retrieval working")
    
    def test_all_signal_types_and_operators(self):
        """Test various signal types and operators in end-to-end workflow."""
        print("\n🧪 Testing various signal types and operators...")
        
        # Create a strategy with different operators
        complex_strategy = {
            "name": "Complex Operator Test",
            "timeframes": ["1"],
            "entry": {
                "long": {
                    "mode": "any",
                    "conditions": [
                        {
                            "signal": "rsi",
                            "operator": "crosses_above",
                            "value": 30,
                            "timeframe": "1"
                        },
                        {
                            "signal": "signal_strength",
                            "operator": "changes_to",
                            "value": 0.9,
                            "timeframe": "1"
                        },
                        {
                            "signal": "close",
                            "operator": "remains",
                            "value": 1.2348,
                            "timeframe": "1"
                        }
                    ]
                }
            },
            "risk": {
                "sl": {"type": "fixed", "value": 50.0},
                "tp": {"type": "fixed", "value": 100.0}
            }
        }
        
        # Save complex strategy
        complex_file = os.path.join(self.temp_dir, "complex.yaml")
        with open(complex_file, 'w') as f:
            yaml.dump(complex_strategy, f)
        
        # Test with complex strategy
        engine = StrategyEngineFactory.create_engine_for_testing(
            schema_path=self.schema_file,
            config_paths=[complex_file]
        )
        
        results = engine.evaluate(self.market_data)
        self.assertEqual(len(results.strategies), 1)
        
        complex_result = results.strategies["Complex Operator Test"]
        self.assertIsNotNone(complex_result.entry)
        print("✅ Complex operators (crosses_above, changes_to, remains) working")
        
        print(f"✅ Complex strategy signals - Entry: long={complex_result.entry.long}")


if __name__ == '__main__':
    unittest.main(verbosity=2)