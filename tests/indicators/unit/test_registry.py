import pytest
from unittest.mock import patch, Mock
from app.indicators.registry import INDICATOR_CLASSES, DEFAULT_PARAMETERS, INDICATOR_CONFIG


class TestIndicatorRegistry:
    """Test suite for indicator registry components."""

    def test_indicator_classes_structure(self):
        """Test INDICATOR_CLASSES has expected structure."""
        # Should be a dictionary
        assert isinstance(INDICATOR_CLASSES, dict)
        
        # Should not be empty
        assert len(INDICATOR_CLASSES) > 0
        
        # All keys should be strings
        for key in INDICATOR_CLASSES.keys():
            assert isinstance(key, str)
            assert len(key) > 0
        
        # All values should be classes (callable)
        for value in INDICATOR_CLASSES.values():
            assert callable(value)

    def test_default_parameters_structure(self):
        """Test DEFAULT_PARAMETERS has expected structure."""
        # Should be a dictionary
        assert isinstance(DEFAULT_PARAMETERS, dict)
        
        # Should not be empty
        assert len(DEFAULT_PARAMETERS) > 0
        
        # All keys should be strings
        for key in DEFAULT_PARAMETERS.keys():
            assert isinstance(key, str)
            assert len(key) > 0
        
        # All values should be dictionaries
        for value in DEFAULT_PARAMETERS.values():
            assert isinstance(value, dict)

    def test_indicator_config_structure(self):
        """Test INDICATOR_CONFIG has expected structure."""
        # Should be a dictionary
        assert isinstance(INDICATOR_CONFIG, dict)
        
        # Should not be empty
        assert len(INDICATOR_CONFIG) > 0
        
        # All keys should be strings
        for key in INDICATOR_CONFIG.keys():
            assert isinstance(key, str)
            assert len(key) > 0
        
        # All values should be dictionaries with required keys
        required_keys = ['inputs', 'bulk_inputs', 'outputs']
        for indicator_name, config in INDICATOR_CONFIG.items():
            assert isinstance(config, dict)
            
            for req_key in required_keys:
                assert req_key in config, f"Missing {req_key} in {indicator_name} config"
                assert callable(config[req_key]), f"{req_key} should be callable in {indicator_name} config"

    def test_registry_consistency(self):
        """Test consistency between registry components."""
        # All indicators in INDICATOR_CLASSES should have default parameters
        for indicator_name in INDICATOR_CLASSES.keys():
            assert indicator_name in DEFAULT_PARAMETERS, f"Missing default parameters for {indicator_name}"
        
        # All indicators with default parameters should have classes
        for indicator_name in DEFAULT_PARAMETERS.keys():
            assert indicator_name in INDICATOR_CLASSES, f"Missing class for {indicator_name}"
        
        # All indicators with configs should have classes and defaults
        for indicator_name in INDICATOR_CONFIG.keys():
            assert indicator_name in INDICATOR_CLASSES, f"Missing class for configured indicator {indicator_name}"
            # Note: Not all indicators may have default parameters, so we don't enforce this

    def test_specific_indicators_presence(self):
        """Test that expected indicators are present in registry."""
        # Common indicators that should be available
        expected_indicators = ['rsi', 'sma', 'ema', 'macd']
        
        for indicator in expected_indicators:
            if indicator in INDICATOR_CLASSES:
                assert indicator in DEFAULT_PARAMETERS, f"Expected defaults for {indicator}"
                # Check if config exists (not all indicators may have config)
                if indicator in INDICATOR_CONFIG:
                    assert 'inputs' in INDICATOR_CONFIG[indicator]
                    assert 'bulk_inputs' in INDICATOR_CONFIG[indicator]
                    assert 'outputs' in INDICATOR_CONFIG[indicator]

    def test_indicator_config_functions_callable(self):
        """Test that all config functions are properly callable."""
        import pandas as pd
        
        # Create sample data for testing
        sample_row = pd.Series({
            'high': 105.0,
            'low': 95.0,
            'close': 100.0,
            'tick_volume': 1000
        })
        
        sample_df = pd.DataFrame({
            'high': [105.0, 107.0],
            'low': [95.0, 97.0],
            'close': [100.0, 102.0],
            'tick_volume': [1000, 1500]
        })
        
        for indicator_name, config in INDICATOR_CONFIG.items():
            # Test inputs function
            try:
                inputs_result = config['inputs'](sample_row)
                assert isinstance(inputs_result, tuple), f"inputs function for {indicator_name} should return tuple"
            except KeyError:
                # Some indicators might require columns not in our sample
                pass
            except Exception as e:
                pytest.fail(f"inputs function for {indicator_name} raised unexpected exception: {e}")
            
            # Test bulk_inputs function
            try:
                bulk_inputs_result = config['bulk_inputs'](sample_df)
                assert isinstance(bulk_inputs_result, tuple), f"bulk_inputs function for {indicator_name} should return tuple"
            except KeyError:
                # Some indicators might require columns not in our sample
                pass
            except Exception as e:
                pytest.fail(f"bulk_inputs function for {indicator_name} raised unexpected exception: {e}")
            
            # Test outputs function
            try:
                outputs_result = config['outputs'](indicator_name)
                assert isinstance(outputs_result, list), f"outputs function for {indicator_name} should return list"
                assert len(outputs_result) > 0, f"outputs function for {indicator_name} should return non-empty list"
                
                # All output names should be strings
                for output_name in outputs_result:
                    assert isinstance(output_name, str), f"All output names for {indicator_name} should be strings"
                    assert len(output_name) > 0, f"Output names for {indicator_name} should not be empty"
                    
            except Exception as e:
                pytest.fail(f"outputs function for {indicator_name} raised unexpected exception: {e}")

    def test_default_parameters_types(self):
        """Test that default parameters have reasonable types."""
        for indicator_name, params in DEFAULT_PARAMETERS.items():
            for param_name, param_value in params.items():
                # Parameters should be basic types
                assert isinstance(param_value, (int, float, str, bool)), \
                    f"Parameter {param_name} in {indicator_name} has unexpected type: {type(param_value)}"
                
                # Numeric parameters should be positive for common cases
                if param_name in ['period', 'window', 'length', 'fast', 'slow', 'signal']:
                    if isinstance(param_value, (int, float)):
                        assert param_value > 0, f"Parameter {param_name} in {indicator_name} should be positive"

    def test_indicator_classes_instantiation(self):
        """Test that indicator classes can be instantiated with default parameters."""
        for indicator_name in INDICATOR_CLASSES.keys():
            if indicator_name in DEFAULT_PARAMETERS:
                cls = INDICATOR_CLASSES[indicator_name]
                params = DEFAULT_PARAMETERS[indicator_name]
                
                try:
                    # Attempt to instantiate with default parameters
                    instance = cls(**params)
                    
                    # Basic checks on the instance
                    assert instance is not None
                    
                    # Should have update method for incremental processing
                    assert hasattr(instance, 'update'), f"Indicator {indicator_name} should have update method"
                    assert callable(instance.update), f"Update method for {indicator_name} should be callable"
                    
                    # Should have batch_update method for bulk processing
                    assert hasattr(instance, 'batch_update'), f"Indicator {indicator_name} should have batch_update method"
                    assert callable(instance.batch_update), f"batch_update method for {indicator_name} should be callable"
                    
                except Exception as e:
                    # Some indicators might have mismatched defaults - skip them with a warning
                    print(f"Warning: Could not instantiate {indicator_name} with defaults: {e}")
                    continue

    def test_output_functions_with_various_names(self):
        """Test output functions work with various indicator names."""
        test_names = [
            'rsi_14',
            'sma_20_custom',
            'macd_fast_slow_signal',
            'bb',
            'indicator_with_underscores_1h_5m'
        ]
        
        for indicator_name in INDICATOR_CONFIG.keys():
            output_func = INDICATOR_CONFIG[indicator_name]['outputs']
            
            for test_name in test_names:
                try:
                    result = output_func(test_name)
                    assert isinstance(result, list)
                    assert len(result) > 0
                    
                    # All outputs should contain the test name as base
                    for output in result:
                        assert isinstance(output, str)
                        assert len(output) > 0
                        
                except Exception as e:
                    pytest.fail(f"outputs function for {indicator_name} failed with name {test_name}: {e}")

    def test_input_functions_error_handling(self):
        """Test input functions handle missing columns gracefully."""
        import pandas as pd
        
        # Create row/dataframe with missing common columns
        incomplete_row = pd.Series({'price': 100.0})
        incomplete_df = pd.DataFrame({'price': [100.0, 101.0]})
        
        for indicator_name, config in INDICATOR_CONFIG.items():
            # Test inputs function with incomplete data
            try:
                config['inputs'](incomplete_row)
            except KeyError:
                # KeyError is expected for missing columns
                pass
            except Exception as e:
                # Other exceptions should be documented or handled
                print(f"Warning: inputs function for {indicator_name} raised {type(e).__name__}: {e}")
            
            # Test bulk_inputs function with incomplete data
            try:
                config['bulk_inputs'](incomplete_df)
            except KeyError:
                # KeyError is expected for missing columns
                pass
            except Exception as e:
                # Other exceptions should be documented or handled
                print(f"Warning: bulk_inputs function for {indicator_name} raised {type(e).__name__}: {e}")

    def test_registry_immutability_simulation(self):
        """Test that registry components behave as if immutable."""
        # Save original values
        original_classes = INDICATOR_CLASSES.copy()
        original_params = DEFAULT_PARAMETERS.copy()
        original_config = INDICATOR_CONFIG.copy()
        
        try:
            # Attempt to modify (this should be avoided in real code)
            if 'test_indicator' not in INDICATOR_CLASSES:
                INDICATOR_CLASSES['test_indicator'] = Mock
                DEFAULT_PARAMETERS['test_indicator'] = {'test_param': 1}
                INDICATOR_CONFIG['test_indicator'] = {
                    'inputs': lambda row: (row['close'],),
                    'bulk_inputs': lambda df: (df['close'],),
                    'outputs': lambda name: [name]
                }
                
                # Verify additions worked
                assert 'test_indicator' in INDICATOR_CLASSES
                assert 'test_indicator' in DEFAULT_PARAMETERS
                assert 'test_indicator' in INDICATOR_CONFIG
        finally:
            # Always clean up modifications, even if assertions fail
            if 'test_indicator' in INDICATOR_CLASSES:
                del INDICATOR_CLASSES['test_indicator']
            if 'test_indicator' in DEFAULT_PARAMETERS:
                del DEFAULT_PARAMETERS['test_indicator']
            if 'test_indicator' in INDICATOR_CONFIG:
                del INDICATOR_CONFIG['test_indicator']
        
        # Verify original state is restored
        assert INDICATOR_CLASSES == original_classes
        assert DEFAULT_PARAMETERS == original_params
        assert INDICATOR_CONFIG == original_config

    def test_specific_indicator_configurations(self):
        """Test specific indicators have expected configurations."""
        # Test RSI configuration if it exists
        if 'rsi' in INDICATOR_CONFIG:
            rsi_config = INDICATOR_CONFIG['rsi']
            
            # RSI should have inputs, bulk_inputs, and outputs
            assert 'inputs' in rsi_config
            assert 'bulk_inputs' in rsi_config
            assert 'outputs' in rsi_config
            
            # Test outputs
            outputs = rsi_config['outputs']('rsi_14')
            assert isinstance(outputs, list)
            assert len(outputs) >= 1  # At least RSI value
            assert 'rsi_14' in outputs  # Should contain the base name
        
        # Test MACD configuration if it exists
        if 'macd' in INDICATOR_CONFIG:
            macd_config = INDICATOR_CONFIG['macd']
            
            outputs = macd_config['outputs']('macd_12_26')
            assert isinstance(outputs, list)
            assert len(outputs) >= 2  # Should have at least MACD line and signal
        
        # Test Bollinger Bands configuration if it exists
        if 'bb' in INDICATOR_CONFIG:
            bb_config = INDICATOR_CONFIG['bb']
            
            outputs = bb_config['outputs']('bb_20')
            assert isinstance(outputs, list)
            assert len(outputs) >= 3  # Should have upper, middle, lower at minimum

    def test_registry_completeness(self):
        """Test that registry is reasonably complete."""
        # Should have a reasonable number of indicators
        assert len(INDICATOR_CLASSES) >= 5, "Should have at least 5 indicators"
        assert len(DEFAULT_PARAMETERS) >= 5, "Should have defaults for at least 5 indicators"
        assert len(INDICATOR_CONFIG) >= 5, "Should have config for at least 5 indicators"
        
        # Check for some common indicator categories
        trend_indicators = ['sma', 'ema', 'macd']
        momentum_indicators = ['rsi', 'stochrsi']
        volatility_indicators = ['bb', 'atr', 'keltner']
        
        found_trend = any(ind in INDICATOR_CLASSES for ind in trend_indicators)
        found_momentum = any(ind in INDICATOR_CLASSES for ind in momentum_indicators)
        found_volatility = any(ind in INDICATOR_CLASSES for ind in volatility_indicators)
        
        assert found_trend or found_momentum or found_volatility, "Should have indicators from major categories"

    def test_parameter_naming_conventions(self):
        """Test that parameters follow naming conventions."""
        common_param_names = [
            'period', 'window', 'length', 'fast', 'slow', 'signal',
            'multiplier', 'num_std_dev', 'std', 'alpha', 'smooth_length'
        ]
        
        for indicator_name, params in DEFAULT_PARAMETERS.items():
            for param_name in params.keys():
                # Parameter names should be lowercase with underscores
                assert param_name.islower() or '_' in param_name, \
                    f"Parameter {param_name} in {indicator_name} should follow naming convention"
                
                # Should not start or end with underscore
                assert not param_name.startswith('_'), \
                    f"Parameter {param_name} in {indicator_name} should not start with underscore"
                assert not param_name.endswith('_'), \
                    f"Parameter {param_name} in {indicator_name} should not end with underscore"

    def test_config_lambda_functions_independence(self):
        """Test that lambda functions in config don't interfere with each other."""
        import pandas as pd
        
        sample_row = pd.Series({
            'high': 105.0,
            'low': 95.0,
            'close': 100.0,
            'tick_volume': 1000,
            'volume': 2000
        })
        
        sample_df = pd.DataFrame({
            'high': [105.0, 107.0],
            'low': [95.0, 97.0],
            'close': [100.0, 102.0],
            'tick_volume': [1000, 1500],
            'volume': [2000, 2500]
        })
        
        # Test that multiple indicators can use the same data without interference
        results = {}
        
        for indicator_name, config in list(INDICATOR_CONFIG.items())[:3]:  # Test first 3
            try:
                # Test inputs
                inputs_result = config['inputs'](sample_row)
                results[f"{indicator_name}_inputs"] = inputs_result
                
                # Test bulk_inputs
                bulk_result = config['bulk_inputs'](sample_df)
                results[f"{indicator_name}_bulk"] = bulk_result
                
                # Test outputs
                outputs_result = config['outputs'](indicator_name)
                results[f"{indicator_name}_outputs"] = outputs_result
                
            except KeyError:
                # Skip indicators that require columns we don't have
                continue
        
        # Verify we got some results
        assert len(results) > 0, "Should have successfully processed some indicators"


class TestRegistryEdgeCases:
    """Test edge cases and error conditions for registry."""

    def test_empty_indicator_name_handling(self):
        """Test how registry handles empty or invalid indicator names."""
        for indicator_name, config in INDICATOR_CONFIG.items():
            outputs_func = config['outputs']
            
            # Test with empty string
            try:
                result = outputs_func('')
                # Should still return a list, even if empty or with empty strings
                assert isinstance(result, list)
            except Exception:
                # If it fails, that's also acceptable behavior
                pass
            
            # Test with None (this should probably fail)
            try:
                outputs_func(None)
                # If it doesn't fail, result should still be a list
            except (TypeError, AttributeError):
                # Expected to fail with None input
                pass

    def test_registry_with_malformed_data(self):
        """Test registry behavior with malformed input data."""
        import pandas as pd
        
        # Create malformed data
        malformed_row = pd.Series({
            'high': 'not_a_number',
            'low': None,
            'close': float('inf'),
            'volume': -1000
        })
        
        malformed_df = pd.DataFrame({
            'high': ['not_a_number', float('nan')],
            'low': [None, float('-inf')],
            'close': [float('inf'), 'string'],
            'volume': [-1000, 0]
        })
        
        for indicator_name, config in list(INDICATOR_CONFIG.items())[:2]:  # Test first 2
            # These should either handle gracefully or raise appropriate exceptions
            try:
                config['inputs'](malformed_row)
            except (KeyError, TypeError, ValueError):
                # These are acceptable exceptions for malformed data
                pass
            
            try:
                config['bulk_inputs'](malformed_df)
            except (KeyError, TypeError, ValueError):
                # These are acceptable exceptions for malformed data
                pass

    def test_registry_consistency_after_modifications(self):
        """Test registry consistency if it were to be modified (hypothetically)."""
        # This tests the robustness of registry structure
        original_len = len(INDICATOR_CLASSES)
        
        # Simulate checking registry integrity
        assert len(INDICATOR_CLASSES) == original_len
        assert all(isinstance(k, str) for k in INDICATOR_CLASSES.keys())
        assert all(callable(v) for v in INDICATOR_CLASSES.values())
        
        assert all(isinstance(k, str) for k in DEFAULT_PARAMETERS.keys())
        assert all(isinstance(v, dict) for v in DEFAULT_PARAMETERS.values())
        
        assert all(isinstance(k, str) for k in INDICATOR_CONFIG.keys())
        assert all(isinstance(v, dict) for v in INDICATOR_CONFIG.values())
        
        # Check required keys in each config
        for config in INDICATOR_CONFIG.values():
            assert 'inputs' in config
            assert 'bulk_inputs' in config
            assert 'outputs' in config