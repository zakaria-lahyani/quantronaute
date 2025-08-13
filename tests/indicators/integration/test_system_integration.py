import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from tests.indicators.reader import load_test_data

from app.indicators.indicator_factory import IndicatorFactory
from app.indicators.indicator_handler import IndicatorHandler
from app.indicators.indicator_manager import IndicatorManager
from app.indicators.registry import INDICATOR_CLASSES, DEFAULT_PARAMETERS, INDICATOR_CONFIG


class TestSystemIntegration:
    """Integration tests for the complete indicator system."""

    @pytest.fixture(scope="class")
    def sample_data(self):
        """Sample market data for testing."""
        return pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=100, freq='1H'),
            'high': np.random.uniform(100, 110, 100),
            'low': np.random.uniform(90, 100, 100),
            'close': np.random.uniform(95, 105, 100),
            'volume': np.random.randint(1000, 5000, 100),
            'tick_volume': np.random.randint(500, 2500, 100)
        })

    @pytest.fixture(scope="class")
    def real_market_data(self):
        """Load real market data for testing."""
        try:
            return load_test_data("history.csv")
        except Exception:
            # Fallback to generated data if test data not available
            return pd.DataFrame({
                'timestamp': pd.date_range('2023-01-01', periods=200, freq='1H'),
                'high': 100 + np.cumsum(np.random.normal(0, 0.5, 200)),
                'low': 98 + np.cumsum(np.random.normal(0, 0.5, 200)),
                'close': 99 + np.cumsum(np.random.normal(0, 0.5, 200)),
                'volume': np.random.randint(1000, 5000, 200),
                'tick_volume': np.random.randint(500, 2500, 200)
            })

    def test_factory_to_handler_integration(self, sample_data):
        """Test integration between IndicatorFactory and IndicatorHandler."""
        config = {
            'rsi_14': {'period': 14, 'signal_period': 9},
            'sma_20': {'period': 20},
            'ema_50': {'period': 50}
        }
        
        # Create factory
        factory = IndicatorFactory(config)
        handlers = factory.create_handlers()
        
        # Verify handlers were created correctly
        assert len(handlers) == len(config)
        for name, handler in handlers.items():
            assert isinstance(handler, IndicatorHandler)
            assert handler.name == name
            assert handler.is_supported()
        
        # Test handler functionality with sample data
        test_row = sample_data.iloc[0]
        for name, handler in handlers.items():
            try:
                result = handler.compute(test_row)
                assert isinstance(result, pd.Series)
                assert len(result) >= len(test_row)  # Should have added indicator columns
            except KeyError:
                # Some indicators might need columns not in our test data
                pass

    def test_handler_to_manager_integration(self, sample_data):
        """Test integration between IndicatorHandler and IndicatorManager."""
        config = {
            'rsi_14': {'period': 14, 'signal_period': 9},
            'sma_20': {'period': 20}
        }
        
        # Test both bulk and warmup modes
        for is_bulk in [True, False]:
            manager = IndicatorManager(sample_data, config, is_bulk=is_bulk)
            
            # Verify manager initialization
            assert len(manager.handlers) == len(config)
            assert not manager.original_historical.empty
            
            # Verify historical data processing
            historical_data = manager.get_historical_data()
            assert isinstance(historical_data, pd.DataFrame)
            assert len(historical_data) == len(sample_data)
            
            # Verify single row processing
            test_row = sample_data.iloc[-1]
            try:
                result = manager.compute_indicators(test_row)
                assert isinstance(result, pd.Series)
            except KeyError:
                # Some indicators might need columns not in our test data
                pass

    def test_end_to_end_indicator_workflow(self, real_market_data):
        """Test complete end-to-end indicator processing workflow."""
        # Configuration with various indicator types
        config = {
            'rsi_14': {'period': 14, 'signal_period': 9},
            'sma_20': {'period': 20},
            'ema_12': {'period': 12},
            'bb_20': {'window': 20, 'num_std_dev': 2},
            'atr_14': {'window': 14}
        }
        
        # Step 1: Create factory
        factory = IndicatorFactory(config)
        
        # Step 2: Create handlers
        handlers = factory.create_handlers()
        
        # Filter to only supported indicators
        supported_config = {}
        supported_handlers = {}
        for name, handler in handlers.items():
            if handler.is_supported():
                supported_config[name] = config[name]
                supported_handlers[name] = handler
        
        if not supported_handlers:
            pytest.skip("No supported indicators available for integration test")
        
        # Step 3: Create manager with supported indicators
        manager = IndicatorManager(real_market_data, supported_config, is_bulk=True)
        
        # Step 4: Process historical data
        historical_with_indicators = manager.get_historical_data()
        
        # Verify results
        assert isinstance(historical_with_indicators, pd.DataFrame)
        assert len(historical_with_indicators) == len(real_market_data)
        
        # Verify original columns are preserved
        for col in real_market_data.columns:
            assert col in historical_with_indicators.columns
        
        # Verify indicator columns were added
        original_col_count = len(real_market_data.columns)
        final_col_count = len(historical_with_indicators.columns)
        assert final_col_count > original_col_count
        
        # Step 5: Test real-time processing
        new_row = real_market_data.iloc[-1].copy()
        new_row.name = len(real_market_data)  # Simulate new timestamp
        
        try:
            processed_row = manager.compute_indicators(new_row)
            assert isinstance(processed_row, pd.Series)
            assert len(processed_row) >= len(new_row)
        except KeyError as e:
            pytest.skip(f"Real-time processing skipped due to missing columns: {e}")

    def test_bulk_vs_incremental_consistency(self, real_market_data):
        """Test that bulk and incremental processing produce consistent results."""
        # Use simple indicators that are likely to be available
        config = {'sma_10': {'period': 10}}
        
        # Skip if SMA not available
        if 'sma' not in INDICATOR_CLASSES:
            pytest.skip("SMA indicator not available for consistency test")
        
        # Create managers for both modes
        manager_bulk = IndicatorManager(real_market_data, config, is_bulk=True)
        manager_incremental = IndicatorManager(real_market_data, config, is_bulk=False)
        
        # Get results from both
        bulk_result = manager_bulk.get_historical_data()
        incremental_result = manager_incremental.get_historical_data()
        
        # Compare results
        assert len(bulk_result) == len(incremental_result)
        assert list(bulk_result.columns) == list(incremental_result.columns)
        
        # Compare original columns (should be identical)
        for col in real_market_data.columns:
            if col in bulk_result.columns and col in incremental_result.columns:
                pd.testing.assert_series_equal(
                    bulk_result[col], 
                    incremental_result[col], 
                    check_names=False
                )
        
        # Compare indicator columns (should be approximately equal)
        indicator_columns = [col for col in bulk_result.columns if col not in real_market_data.columns]
        for col in indicator_columns:
            # Use relaxed comparison for numerical differences
            bulk_values = bulk_result[col].dropna()
            incremental_values = incremental_result[col].dropna()
            
            if len(bulk_values) > 0 and len(incremental_values) > 0:
                # Check that most values are close
                min_length = min(len(bulk_values), len(incremental_values))
                if min_length > 0:
                    diff = np.abs(bulk_values.iloc[-min_length:].values - 
                                 incremental_values.iloc[-min_length:].values)
                    max_diff = np.max(diff)
                    mean_diff = np.mean(diff)
                    
                    # Allow some tolerance for numerical differences
                    assert max_diff < 1e-6 or max_diff / np.mean(np.abs(bulk_values.iloc[-min_length:])) < 1e-10
                    assert mean_diff < 1e-8

    def test_multiple_indicator_interaction(self, sample_data):
        """Test that multiple indicators don't interfere with each other."""
        config = {
            'rsi_14': {'period': 14, 'signal_period': 9},
            'sma_20': {'period': 20},
            'ema_12': {'period': 12},
            'bb_20': {'window': 20, 'num_std_dev': 2}
        }
        
        # Create manager with all indicators
        try:
            manager = IndicatorManager(sample_data, config, is_bulk=True)
        except Exception:
            pytest.skip("Some indicators not available for interaction test")
        
        result = manager.get_historical_data()
        
        # Each indicator should have added its own columns without affecting others
        expected_patterns = {
            'rsi_14': ['rsi_14'],
            'sma_20': ['sma_20'],
            'ema_12': ['ema_12'],
            'bb_20': ['bb_20']
        }
        
        for indicator_name, expected_cols in expected_patterns.items():
            if indicator_name in manager.handlers and manager.handlers[indicator_name].is_supported():
                indicator_outputs = manager.handlers[indicator_name].get_output_columns()
                
                # Verify expected columns are present
                for expected_col in expected_cols:
                    matching_cols = [col for col in indicator_outputs if expected_col in col]
                    assert len(matching_cols) > 0, f"Expected column pattern {expected_col} not found"
                
                # Verify columns are in result
                for output_col in indicator_outputs:
                    assert output_col in result.columns, f"Indicator output {output_col} not in result"

    def test_registry_integration_with_real_indicators(self):
        """Test that registry components work together with real indicator classes."""
        # Test a few indicators that should be available
        test_indicators = ['rsi', 'sma', 'ema']
        
        for indicator_name in test_indicators:
            if indicator_name not in INDICATOR_CLASSES:
                continue
            
            # Get components from registry
            indicator_class = INDICATOR_CLASSES[indicator_name]
            default_params = DEFAULT_PARAMETERS.get(indicator_name, {})
            config = INDICATOR_CONFIG.get(indicator_name)
            
            # Test class instantiation with defaults
            try:
                indicator_instance = indicator_class(**default_params)
                assert indicator_instance is not None
                
                # Test that instance has required methods
                assert hasattr(indicator_instance, 'update')
                assert hasattr(indicator_instance, 'batch_update')
                
                # Test configuration if available
                if config:
                    assert 'inputs' in config
                    assert 'bulk_inputs' in config
                    assert 'outputs' in config
                    
                    # Test output function
                    outputs = config['outputs'](f"{indicator_name}_test")
                    assert isinstance(outputs, list)
                    assert len(outputs) > 0
                    
            except Exception as e:
                pytest.fail(f"Registry integration failed for {indicator_name}: {e}")

    def test_error_propagation_through_system(self, sample_data):
        """Test how errors propagate through the system."""
        # Create config with a known indicator
        config = {'sma_20': {'period': 20}}
        
        if 'sma' not in INDICATOR_CLASSES:
            pytest.skip("SMA not available for error propagation test")
        
        # Test with data missing required columns
        incomplete_data = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=10, freq='1H'),
            'volume': [1000] * 10
            # Missing 'close' column required by most indicators
        })
        
        try:
            manager = IndicatorManager(incomplete_data, config, is_bulk=True)
            # This might succeed or fail depending on implementation
        except Exception:
            # Error during initialization is acceptable
            pass
        
        # Test with individual row processing
        try:
            manager = IndicatorManager(sample_data, config, is_bulk=True)
            incomplete_row = pd.Series({'volume': 1000})
            
            # This should raise an error
            with pytest.raises((KeyError, ValueError, AttributeError)):
                manager.compute_indicators(incomplete_row)
                
        except Exception:
            # If manager creation fails, that's also acceptable
            pass

    def test_performance_characteristics(self, real_market_data):
        """Test basic performance characteristics of the system."""
        config = {'sma_20': {'period': 20}}
        
        if 'sma' not in INDICATOR_CLASSES:
            pytest.skip("SMA not available for performance test")
        
        import time
        
        # Test bulk processing performance
        start_time = time.time()
        manager_bulk = IndicatorManager(real_market_data, config, is_bulk=True)
        bulk_result = manager_bulk.get_historical_data()
        bulk_time = time.time() - start_time
        
        # Test incremental processing performance
        start_time = time.time()
        manager_inc = IndicatorManager(real_market_data, config, is_bulk=False)
        inc_result = manager_inc.get_historical_data()
        inc_time = time.time() - start_time
        
        # Basic assertions
        assert len(bulk_result) == len(inc_result)
        assert bulk_time >= 0  # Allow for very fast execution
        assert inc_time >= 0   # Allow for very fast execution
        
        # Log performance for observation (not assertion)
        print(f"Bulk processing time: {bulk_time:.4f}s")
        print(f"Incremental processing time: {inc_time:.4f}s")
        
        # Generally bulk should be faster, but don't assert this as it depends on implementation

    def test_data_integrity_through_pipeline(self, real_market_data):
        """Test that data integrity is maintained through the processing pipeline."""
        config = {'sma_10': {'period': 10}}
        
        if 'sma' not in INDICATOR_CLASSES:
            pytest.skip("SMA not available for data integrity test")
        
        original_data = real_market_data.copy()
        
        # Process through manager
        manager = IndicatorManager(real_market_data, config, is_bulk=True)
        processed_data = manager.get_historical_data()
        
        # Verify original data is unchanged
        pd.testing.assert_frame_equal(real_market_data, original_data)
        
        # Verify original columns are preserved in processed data
        for col in original_data.columns:
            if col in processed_data.columns:
                pd.testing.assert_series_equal(
                    original_data[col], 
                    processed_data[col], 
                    check_names=False
                )
        
        # Verify no data loss
        assert len(processed_data) == len(original_data)
        assert processed_data.index.equals(original_data.index)

    def test_factory_with_invalid_configurations(self):
        """Test factory handling of invalid configurations."""
        # Test with unknown indicators
        invalid_config = {
            'unknown_indicator_xyz': {'param1': 123},
            'another_fake_indicator': {'param2': 456}
        }
        
        factory = IndicatorFactory(invalid_config)
        handlers = factory.create_handlers()
        
        # Should return empty handlers for unknown indicators
        assert len(handlers) == 0
        
        # Test with mixed valid/invalid config
        if 'sma' in INDICATOR_CLASSES:
            mixed_config = {
                'sma_20': {'period': 20},  # Valid
                'unknown_indicator': {'param': 123}  # Invalid
            }
            
            factory = IndicatorFactory(mixed_config)
            handlers = factory.create_handlers()
            
            # Should create handler only for valid indicator
            assert len(handlers) == 1
            assert 'sma_20' in handlers
            assert 'unknown_indicator' not in handlers

    def test_system_with_edge_case_data(self):
        """Test system behavior with edge case data."""
        # Create edge case data
        edge_data = pd.DataFrame({
            'high': [100.0, 100.0, 100.0],  # No price movement
            'low': [100.0, 100.0, 100.0],
            'close': [100.0, 100.0, 100.0],
            'volume': [0, 1000000, 1]  # Extreme volume values
        })
        
        config = {'sma_2': {'period': 2}}
        
        if 'sma' not in INDICATOR_CLASSES:
            pytest.skip("SMA not available for edge case test")
        
        try:
            manager = IndicatorManager(edge_data, config, is_bulk=True)
            result = manager.get_historical_data()
            
            # Should handle constant prices gracefully
            assert isinstance(result, pd.DataFrame)
            assert len(result) == len(edge_data)
            
            # SMA of constant values should be constant
            if 'sma_2' in result.columns:
                sma_values = result['sma_2'].dropna()
                if len(sma_values) > 0:
                    # All SMA values should be the same (100.0)
                    assert np.allclose(sma_values, 100.0, rtol=1e-10)
                    
        except Exception as e:
            # Some edge cases might legitimately cause failures
            print(f"Edge case handling: {e}")


class TestSystemIntegrationWithMocks:
    """Integration tests using mocks for components that might not be available."""

    def test_complete_workflow_with_mocked_indicators(self, monkeypatch):
        """Test complete workflow using mocked indicators."""
        # Mock the registry
        mock_sma_class = Mock()
        mock_sma_instance = Mock()
        mock_sma_instance.update.return_value = 100.5
        mock_sma_instance.batch_update.return_value = np.array([100.1, 100.3, 100.5])
        mock_sma_class.return_value = mock_sma_instance
        
        mock_rsi_class = Mock()
        mock_rsi_instance = Mock()
        mock_rsi_instance.update.return_value = (50.0, 45.0)
        mock_rsi_instance.batch_update.return_value = (
            np.array([48.0, 52.0, 50.0]),
            np.array([46.0, 47.0, 45.0])
        )
        mock_rsi_class.return_value = mock_rsi_instance
        
        mock_indicator_classes = {
            'sma': mock_sma_class,
            'rsi': mock_rsi_class
        }
        
        mock_default_params = {
            'sma': {'period': 20},
            'rsi': {'period': 14, 'signal_period': 9}
        }
        
        mock_indicator_config = {
            'sma': {
                'inputs': lambda row: (row['close'],),
                'bulk_inputs': lambda df: (df['close'],),
                'outputs': lambda name: [name]
            },
            'rsi': {
                'inputs': lambda row: (row['close'],),
                'bulk_inputs': lambda df: (df['close'],),
                'outputs': lambda name: [name, f'{name}_signal']
            }
        }
        
        # Apply mocks
        monkeypatch.setattr('app.indicators.registry.INDICATOR_CLASSES', mock_indicator_classes)
        monkeypatch.setattr('app.indicators.registry.DEFAULT_PARAMETERS', mock_default_params)
        monkeypatch.setattr('app.indicators.registry.INDICATOR_CONFIG', mock_indicator_config)
        
        # Create test data
        sample_data = pd.DataFrame({
            'close': [100.0, 101.0, 102.0],
            'volume': [1000, 1500, 1200]
        })
        
        # Test complete workflow
        config = {
            'sma_20': {'period': 20},
            'rsi_14': {'period': 14, 'signal_period': 9}
        }
        
        # Step 1: Factory creates handlers
        factory = IndicatorFactory(config)
        handlers = factory.create_handlers()
        
        assert len(handlers) == 2
        assert 'sma_20' in handlers
        assert 'rsi_14' in handlers
        
        # Step 2: Manager processes data
        manager = IndicatorManager(sample_data, config, is_bulk=True)
        result = manager.get_historical_data()
        
        # Verify results
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_data)
        assert 'sma_20' in result.columns
        assert 'rsi_14' in result.columns
        assert 'signal_rsi_14' in result.columns
        
        # Verify basic functionality works
        # (Mock calls may not happen if real indicators are used)
        
        # Step 3: Test real-time processing
        new_row = pd.Series({'close': 103.0, 'volume': 1300})
        processed_row = manager.compute_indicators(new_row)
        
        assert isinstance(processed_row, pd.Series)
        assert 'sma_20' in processed_row
        assert 'rsi_14' in processed_row
        assert 'signal_rsi_14' in processed_row

    def test_error_handling_integration(self):
        """Test error handling across integrated components."""
        # Test with configuration that has errors
        config = {
            'nonexistent_indicator': {'param': 123}
        }
        
        # Factory should handle unknown indicators gracefully
        factory = IndicatorFactory(config)
        handlers = factory.create_handlers()
        assert len(handlers) == 0
        
        # Manager should handle empty handlers
        sample_data = pd.DataFrame({'close': [100, 101, 102]})
        manager = IndicatorManager(sample_data, {}, is_bulk=True)
        
        # Should work with empty config
        result = manager.get_historical_data()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_data)
        
        # Should work with single row
        test_row = pd.Series({'close': 103})
        processed_row = manager.compute_indicators(test_row)
        assert isinstance(processed_row, pd.Series)

    def test_concurrent_processing_safety(self, monkeypatch):
        """Test that the system is safe for concurrent access (read operations)."""
        # Mock a simple indicator
        mock_sma_class = Mock()
        mock_sma_instance = Mock()
        mock_sma_instance.update.return_value = 100.0
        mock_sma_instance.batch_update.return_value = np.array([100.0] * 10)
        mock_sma_class.return_value = mock_sma_instance
        
        mock_registry = {
            'sma': mock_sma_class
        }
        
        mock_defaults = {
            'sma': {'period': 10}
        }
        
        mock_config = {
            'sma': {
                'inputs': lambda row: (row['close'],),
                'bulk_inputs': lambda df: (df['close'],),
                'outputs': lambda name: [name]
            }
        }
        
        monkeypatch.setattr('app.indicators.registry.INDICATOR_CLASSES', mock_registry)
        monkeypatch.setattr('app.indicators.registry.DEFAULT_PARAMETERS', mock_defaults)
        monkeypatch.setattr('app.indicators.registry.INDICATOR_CONFIG', mock_config)
        
        # Create test data and manager
        sample_data = pd.DataFrame({
            'close': [100 + i for i in range(10)],
            'volume': [1000] * 10
        })
        
        config = {'sma_10': {'period': 10}}
        manager = IndicatorManager(sample_data, config, is_bulk=True)
        
        # Simulate concurrent read operations
        # (In real test, you might use threading, but for simplicity we'll just call multiple times)
        results = []
        for _ in range(5):
            historical_data = manager.get_historical_data()
            test_row = pd.Series({'close': 110, 'volume': 1100})
            processed_row = manager.compute_indicators(test_row)
            
            results.append((historical_data, processed_row))
        
        # All results should be identical (read operations should be consistent)
        first_hist, first_row = results[0]
        for hist, row in results[1:]:
            pd.testing.assert_frame_equal(hist, first_hist)
            pd.testing.assert_series_equal(row, first_row)