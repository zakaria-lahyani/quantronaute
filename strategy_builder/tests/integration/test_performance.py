"""
Performance and stress tests for the strategy engine.

Tests system performance under various load conditions:
1. Multiple strategies with large datasets
2. Complex condition trees
3. Time-based exit performance
4. Memory usage validation
5. Concurrent evaluation scenarios
"""

import unittest
import time
from datetime import datetime, timedelta
from collections import deque
import pandas as pd
import tempfile
import os
import yaml

from ...factory import StrategyEngineFactory
from ...infrastructure.logging import create_null_logger


class TestPerformanceAndStress(unittest.TestCase):
    """Performance and stress tests for the strategy engine."""
    
    def setUp(self):
        """Set up performance test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.schema_file = None
        self.strategy_files = []
        
        # Create large market dataset for performance testing
        self.large_market_data = self.create_large_market_data()
        
        # Create test schema and strategies
        self.create_test_schema()
        self.create_performance_test_strategies()
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def create_large_market_data(self):
        """Create large market dataset for performance testing."""
        print("📊 Creating large market dataset...")
        
        # Create 1000 data points for each timeframe
        data_points = 1000
        
        market_data = {}
        for timeframe in ["1", "5", "60"]:
            data_series = []
            
            for i in range(data_points):
                # Generate realistic market data
                base_price = 1.2345 + (i * 0.0001)
                data_point = pd.Series({
                    'close': base_price + (i % 10) * 0.0001,
                    'high': base_price + 0.0005,
                    'low': base_price - 0.0005,
                    'volume': 1000 + (i * 10),
                    'rsi': 30 + (i % 40),
                    'previous_rsi': 30 + ((i-1) % 40),
                    'ma_20': base_price,
                    'previous_ma_20': base_price - 0.0001,
                    'signal_strength': 0.5 + (i % 50) / 100,
                    'previous_signal_strength': 0.5 + ((i-1) % 50) / 100,
                    'atr': 0.001 + (i % 10) * 0.0001,
                    'bb_upper': base_price + 0.002,
                    'bb_lower': base_price - 0.002,
                })
                data_series.append(data_point)
            
            market_data[timeframe] = deque(data_series, maxlen=data_points)
        
        print(f"✅ Created market data with {data_points} points per timeframe")
        return market_data
    
    def create_test_schema(self):
        """Create test schema."""
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
        
        self.schema_file = os.path.join(self.temp_dir, "perf_schema.json")
        import json
        with open(self.schema_file, 'w') as f:
            json.dump(schema, f)
    
    def create_performance_test_strategies(self):
        """Create multiple strategies for performance testing."""
        strategies = []
        
        # Strategy 1: Simple strategy
        strategies.append({
            "name": "Perf Test Simple",
            "timeframes": ["1", "5"],
            "entry": {
                "long": {
                    "mode": "all",
                    "conditions": [
                        {"signal": "rsi", "operator": "<=", "value": 30, "timeframe": "1"},
                        {"signal": "close", "operator": ">", "value": "ma_20", "timeframe": "1"}
                    ]
                }
            },
            "exit": {
                "long": {
                    "mode": "any",
                    "conditions": [
                        {"signal": "rsi", "operator": ">=", "value": 70, "timeframe": "1"}
                    ],
                    "time_based": {"max_duration": "1h"}
                }
            },
            "risk": {
                "sl": {"type": "fixed", "value": 50.0},
                "tp": {"type": "fixed", "value": 100.0}
            }
        })
        
        # Strategy 2: Complex tree strategy
        strategies.append({
            "name": "Perf Test Complex",
            "timeframes": ["1", "5", "60"],
            "entry": {
                "long": {
                    "mode": "complex",
                    "tree": {
                        "operator": "and",
                        "conditions": [
                            {
                                "operator": "or",
                                "conditions": [
                                    {"signal": "rsi", "operator": "crosses_above", "value": 30, "timeframe": "1"},
                                    {"signal": "signal_strength", "operator": ">=", "value": 0.8, "timeframe": "5"}
                                ]
                            },
                            {"signal": "volume", "operator": ">", "value": 1000, "timeframe": "1"},
                            {
                                "operator": "not",
                                "conditions": [
                                    {"signal": "rsi", "operator": ">=", "value": 80, "timeframe": "60"}
                                ]
                            }
                        ]
                    }
                },
                "short": {
                    "mode": "any",
                    "conditions": [
                        {"signal": "rsi", "operator": ">=", "value": 70, "timeframe": "1"},
                        {"signal": "bb_upper", "operator": "crosses_below", "value": "close", "timeframe": "5"}
                    ]
                }
            },
            "exit": {
                "long": {
                    "mode": "complex",
                    "tree": {
                        "operator": "or",
                        "conditions": [
                            {"signal": "rsi", "operator": "<=", "value": 20, "timeframe": "1"},
                            {
                                "operator": "and",
                                "conditions": [
                                    {"signal": "atr", "operator": ">", "value": 0.002, "timeframe": "5"},
                                    {"signal": "volume", "operator": "<", "value": 500, "timeframe": "1"}
                                ]
                            }
                        ]
                    },
                    "time_based": {"max_duration": "2h", "min_duration": "15m"}
                }
            },
            "risk": {
                "sl": {"type": "trailing", "step": 0.5, "activation_price": 1.0},
                "tp": {
                    "type": "multi_target",
                    "targets": [
                        {"value": 1.0, "percent": 30},
                        {"value": 2.0, "percent": 40},
                        {"value": 3.0, "percent": 30}
                    ]
                }
            }
        })
        
        # Strategy 3: Multiple conditions strategy
        strategies.append({
            "name": "Perf Test Multi Conditions",
            "timeframes": ["1", "5"],
            "entry": {
                "long": {
                    "mode": "all",
                    "conditions": [
                        {"signal": "rsi", "operator": "<=", "value": 40, "timeframe": "1"},
                        {"signal": "signal_strength", "operator": ">=", "value": 0.7, "timeframe": "1"},
                        {"signal": "close", "operator": ">", "value": "ma_20", "timeframe": "1"},
                        {"signal": "volume", "operator": ">", "value": 1000, "timeframe": "1"},
                        {"signal": "atr", "operator": "<=", "value": 0.002, "timeframe": "5"}
                    ]
                }
            },
            "exit": {
                "long": {
                    "mode": "any",
                    "conditions": [
                        {"signal": "rsi", "operator": ">=", "value": 60, "timeframe": "1"},
                        {"signal": "signal_strength", "operator": "<=", "value": 0.3, "timeframe": "1"},
                        {"signal": "close", "operator": "<=", "value": "ma_20", "timeframe": "1"}
                    ]
                }
            },
            "risk": {
                "sl": {"type": "fixed", "value": 30.0},
                "tp": {"type": "fixed", "value": 90.0}
            }
        })
        
        # Save all strategies
        for i, strategy in enumerate(strategies):
            strategy_file = os.path.join(self.temp_dir, f"perf_strategy_{i+1}.yaml")
            with open(strategy_file, 'w') as f:
                yaml.dump(strategy, f)
            self.strategy_files.append(strategy_file)
    
    def test_large_dataset_performance(self):
        """Test performance with large market datasets."""
        print("\n⚡ Testing performance with large datasets...")
        
        # Create engine
        start_time = time.time()
        engine = StrategyEngineFactory.create_engine_for_testing(
            schema_path=self.schema_file,
            config_paths=self.strategy_files
        )
        load_time = time.time() - start_time
        
        print(f"✅ Strategy loading time: {load_time:.3f}s")
        self.assertLess(load_time, 5.0, "Strategy loading should be under 5 seconds")
        
        # Test evaluation performance
        start_time = time.time()
        results = engine.evaluate(self.large_market_data)
        eval_time = time.time() - start_time
        
        print(f"✅ Evaluation time for {len(results.strategies)} strategies: {eval_time:.3f}s")
        self.assertLess(eval_time, 10.0, "Evaluation should be under 10 seconds")
        
        # Verify all strategies evaluated
        self.assertEqual(len(results.strategies), 3)
        for strategy_name, result in results.strategies.items():
            self.assertIsNotNone(result.entry)
            self.assertIsNotNone(result.exit)
            print(f"✅ {strategy_name}: Entry signals generated")
    
    def test_multiple_evaluations_performance(self):
        """Test performance of multiple consecutive evaluations."""
        print("\n⚡ Testing multiple consecutive evaluations...")
        
        engine = StrategyEngineFactory.create_engine_for_testing(
            schema_path=self.schema_file,
            config_paths=self.strategy_files
        )
        
        # Run 10 consecutive evaluations
        evaluation_times = []
        num_evaluations = 10
        
        for i in range(num_evaluations):
            start_time = time.time()
            results = engine.evaluate(self.large_market_data)
            eval_time = time.time() - start_time
            evaluation_times.append(eval_time)
            
            # Verify results are consistent
            self.assertEqual(len(results.strategies), 3)
        
        avg_time = sum(evaluation_times) / len(evaluation_times)
        max_time = max(evaluation_times)
        min_time = min(evaluation_times)
        
        print(f"✅ Average evaluation time: {avg_time:.3f}s")
        print(f"✅ Min evaluation time: {min_time:.3f}s")
        print(f"✅ Max evaluation time: {max_time:.3f}s")
        
        # Performance assertions
        self.assertLess(avg_time, 2.0, "Average evaluation time should be under 2 seconds")
        self.assertLess(max_time, 5.0, "Max evaluation time should be under 5 seconds")
    
    def test_time_based_exit_performance(self):
        """Test performance of time-based exit calculations."""
        print("\n⚡ Testing time-based exit performance...")
        
        engine = StrategyEngineFactory.create_engine_for_testing(
            schema_path=self.schema_file,
            config_paths=self.strategy_files
        )
        
        # Create multiple position scenarios
        position_scenarios = []
        for hours_ago in [0.5, 1, 2, 3, 5, 10, 24, 48]:
            position_scenarios.append({
                'entry_time': datetime.now() - timedelta(hours=hours_ago),
                'strategy_name': 'Perf Test Simple',
                'direction': 'long'
            })
        
        # Test performance with different position ages
        from ...core.services.executor import create_strategy_executor
        from ...core.evaluators.factory import create_evaluator_factory
        
        strategy = engine.get_strategy_info("Perf Test Simple")
        logger = create_null_logger()
        evaluator_factory = create_evaluator_factory(logger)
        
        start_time = time.time()
        
        for position_data in position_scenarios:
            executor = create_strategy_executor(
                strategy, 
                self.large_market_data, 
                evaluator_factory, 
                position_data
            )
            
            # Test both entry and exit evaluation
            entry_result = executor.check_entry()
            exit_result = executor.check_exit()
            
            self.assertIsNotNone(entry_result)
            self.assertIsNotNone(exit_result)
        
        total_time = time.time() - start_time
        avg_time_per_scenario = total_time / len(position_scenarios)
        
        print(f"✅ Time-based exit evaluation for {len(position_scenarios)} scenarios: {total_time:.3f}s")
        print(f"✅ Average time per scenario: {avg_time_per_scenario:.3f}s")
        
        self.assertLess(avg_time_per_scenario, 0.1, "Each scenario should evaluate in under 0.1 seconds")
    
    def test_complex_tree_evaluation_performance(self):
        """Test performance of complex condition tree evaluation."""
        print("\n⚡ Testing complex tree evaluation performance...")
        
        engine = StrategyEngineFactory.create_engine_for_testing(
            schema_path=self.schema_file,
            config_paths=self.strategy_files
        )
        
        # Focus on the complex strategy
        start_time = time.time()
        result = engine.evaluate_single_strategy("Perf Test Complex", self.large_market_data)
        eval_time = time.time() - start_time
        
        print(f"✅ Complex tree evaluation time: {eval_time:.3f}s")
        self.assertLess(eval_time, 1.0, "Complex tree evaluation should be under 1 second")
        
        # Verify the complex strategy produces valid results
        self.assertIsNotNone(result.entry.long)
        self.assertIsNotNone(result.entry.short)
        self.assertIsNotNone(result.exit.long)
        
        print(f"✅ Complex strategy signals - Entry: long={result.entry.long}, short={result.entry.short}")
    
    def test_memory_usage_stability(self):
        """Test memory usage remains stable during multiple evaluations."""
        print("\n🧠 Testing memory usage stability...")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        engine = StrategyEngineFactory.create_engine_for_testing(
            schema_path=self.schema_file,
            config_paths=self.strategy_files
        )
        
        # Run multiple evaluations and track memory
        memory_readings = []
        for i in range(20):
            results = engine.evaluate(self.large_market_data)
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_readings.append(current_memory)
            
            # Verify results are still valid
            self.assertEqual(len(results.strategies), 3)
        
        final_memory = memory_readings[-1]
        max_memory = max(memory_readings)
        memory_growth = final_memory - initial_memory
        
        print(f"✅ Initial memory: {initial_memory:.1f} MB")
        print(f"✅ Final memory: {final_memory:.1f} MB")
        print(f"✅ Max memory: {max_memory:.1f} MB")
        print(f"✅ Memory growth: {memory_growth:.1f} MB")
        
        # Memory should not grow excessively
        self.assertLess(memory_growth, 50, "Memory growth should be under 50 MB")
        self.assertLess(max_memory, initial_memory + 100, "Max memory should not exceed initial + 100 MB")
    
    def test_concurrent_strategy_evaluation(self):
        """Test concurrent evaluation scenarios."""
        print("\n🔄 Testing concurrent evaluation scenarios...")
        
        engine = StrategyEngineFactory.create_engine_for_testing(
            schema_path=self.schema_file,
            config_paths=self.strategy_files
        )
        
        # Simulate concurrent evaluations by running them in quick succession
        results_list = []
        start_time = time.time()
        
        for i in range(5):
            # Slightly modify market data for each evaluation
            modified_data = self.large_market_data.copy()
            for timeframe in modified_data:
                # Add small variation to the last data point
                last_point = modified_data[timeframe][-1].copy()
                last_point['close'] += i * 0.0001
                modified_data[timeframe].append(last_point)
            
            results = engine.evaluate(modified_data)
            results_list.append(results)
        
        total_time = time.time() - start_time
        avg_time = total_time / len(results_list)
        
        print(f"✅ Concurrent evaluations completed in: {total_time:.3f}s")
        print(f"✅ Average time per evaluation: {avg_time:.3f}s")
        
        # Verify all evaluations completed successfully
        for i, results in enumerate(results_list):
            self.assertEqual(len(results.strategies), 3)
            print(f"✅ Evaluation {i+1}: All strategies evaluated successfully")
        
        self.assertLess(avg_time, 2.0, "Average concurrent evaluation time should be under 2 seconds")


if __name__ == '__main__':
    unittest.main(verbosity=2)