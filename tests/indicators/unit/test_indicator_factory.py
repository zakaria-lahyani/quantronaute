import pytest
from unittest.mock import Mock, patch, MagicMock
from app.indicators.indicator_factory import IndicatorFactory
from app.indicators.indicator_handler import IndicatorHandler


class TestIndicatorFactory:
    """Test suite for IndicatorFactory class."""

    def test_factory_initialization(self):
        """Test factory initializes with correct configuration."""
        config = {
            'rsi_14': {'period': 14},
            'sma_20': {'period': 20}
        }
        
        factory = IndicatorFactory(config)
        
        assert factory.config == config
        assert isinstance(factory.config, dict)

    def test_factory_initialization_empty_config(self):
        """Test factory handles empty configuration."""
        config = {}
        
        factory = IndicatorFactory(config)
        
        assert factory.config == config
        assert len(factory.config) == 0

    @patch('app.indicators.indicator_factory.INDICATOR_CLASSES')
    @patch('app.indicators.indicator_factory.DEFAULT_PARAMETERS')
    def test_create_handlers_success(self, mock_default_params, mock_indicator_classes):
        """Test successful handler creation."""
        # Setup mocks
        mock_rsi_class = Mock()
        mock_rsi_instance = Mock()
        mock_rsi_class.return_value = mock_rsi_instance
        
        mock_sma_class = Mock()
        mock_sma_instance = Mock()
        mock_sma_class.return_value = mock_sma_instance
        
        mock_indicator_classes.get.side_effect = lambda key: {
            'rsi': mock_rsi_class,
            'sma': mock_sma_class
        }.get(key)
        
        mock_default_params.get.side_effect = lambda key, default: {
            'rsi': {'period': 10},
            'sma': {'period': 15}
        }.get(key, default)
        
        config = {
            'rsi_14': {'period': 14},
            'sma_20': {'period': 20}
        }
        
        factory = IndicatorFactory(config)
        
        with patch.object(IndicatorHandler, '__init__', return_value=None) as mock_handler_init:
            handlers = factory.create_handlers()
        
        # Verify results
        assert len(handlers) == 2
        assert 'rsi_14' in handlers
        assert 'sma_20' in handlers
        
        # Verify classes were called with merged parameters
        mock_rsi_class.assert_called_once_with(period=14)
        mock_sma_class.assert_called_once_with(period=20)
        
        # Verify handler creation
        assert mock_handler_init.call_count == 2

    @patch('app.indicators.indicator_factory.INDICATOR_CLASSES')
    @patch('app.indicators.indicator_factory.DEFAULT_PARAMETERS')
    def test_create_handlers_with_parameter_merging(self, mock_default_params, mock_indicator_classes):
        """Test parameter merging with defaults."""
        # Setup mock indicator class
        mock_macd_class = Mock()
        mock_macd_instance = Mock()
        mock_macd_class.return_value = mock_macd_instance
        
        mock_indicator_classes.get.return_value = mock_macd_class
        mock_default_params.get.return_value = {
            'fast': 12,
            'slow': 26,
            'signal': 9
        }
        
        config = {
            'macd_1h': {'signal': 7}  # Override only signal parameter
        }
        
        factory = IndicatorFactory(config)
        
        with patch.object(IndicatorHandler, '__init__', return_value=None):
            handlers = factory.create_handlers()
        
        # Verify merged parameters were used
        expected_params = {
            'fast': 12,   # From defaults
            'slow': 26,   # From defaults
            'signal': 7   # Overridden
        }
        mock_macd_class.assert_called_once_with(**expected_params)

    @patch('app.indicators.indicator_factory.INDICATOR_CLASSES')
    @patch('app.indicators.indicator_factory.DEFAULT_PARAMETERS')
    def test_create_handlers_skips_unknown_indicators(self, mock_default_params, mock_indicator_classes):
        """Test factory skips unknown indicator types."""
        # Setup mocks - only rsi is known
        mock_rsi_class = Mock()
        mock_rsi_instance = Mock()
        mock_rsi_class.return_value = mock_rsi_instance
        
        mock_indicator_classes.get.side_effect = lambda key: {
            'rsi': mock_rsi_class
        }.get(key)  # Returns None for unknown indicators
        
        mock_default_params.get.return_value = {'period': 14}
        
        config = {
            'rsi_14': {'period': 14},
            'unknown_5m': {'param': 123}  # Unknown indicator
        }
        
        factory = IndicatorFactory(config)
        
        with patch.object(IndicatorHandler, '__init__', return_value=None):
            handlers = factory.create_handlers()
        
        # Only known indicator should be created
        assert len(handlers) == 1
        assert 'rsi_14' in handlers
        assert 'unknown_5m' not in handlers

    @patch('app.indicators.indicator_factory.INDICATOR_CLASSES')
    @patch('app.indicators.indicator_factory.DEFAULT_PARAMETERS')
    def test_create_handlers_with_no_defaults(self, mock_default_params, mock_indicator_classes):
        """Test handler creation when no defaults are available."""
        mock_custom_class = Mock()
        mock_custom_instance = Mock()
        mock_custom_class.return_value = mock_custom_instance
        
        mock_indicator_classes.get.return_value = mock_custom_class
        mock_default_params.get.return_value = {}  # No defaults
        
        config = {
            'custom_1m': {'param1': 'value1', 'param2': 'value2'}
        }
        
        factory = IndicatorFactory(config)
        
        with patch.object(IndicatorHandler, '__init__', return_value=None):
            handlers = factory.create_handlers()
        
        # Should use only user parameters
        mock_custom_class.assert_called_once_with(param1='value1', param2='value2')

    @patch('app.indicators.indicator_factory.INDICATOR_CLASSES')
    @patch('app.indicators.indicator_factory.DEFAULT_PARAMETERS')
    def test_create_handlers_complex_name_parsing(self, mock_default_params, mock_indicator_classes):
        """Test complex indicator name parsing."""
        mock_bb_class = Mock()
        mock_bb_instance = Mock()
        mock_bb_class.return_value = mock_bb_instance
        
        mock_indicator_classes.get.return_value = mock_bb_class
        mock_default_params.get.return_value = {'window': 20, 'std': 2}
        
        config = {
            'bb_1h_custom': {'std': 2.5},  # Complex name with multiple underscores
            'bb': {'window': 15}           # Simple name
        }
        
        factory = IndicatorFactory(config)
        
        with patch.object(IndicatorHandler, '__init__', return_value=None):
            handlers = factory.create_handlers()
        
        # Both should be created as they start with 'bb'
        assert len(handlers) == 2
        assert 'bb_1h_custom' in handlers
        assert 'bb' in handlers

    @patch('app.indicators.indicator_factory.INDICATOR_CLASSES')
    @patch('app.indicators.indicator_factory.DEFAULT_PARAMETERS')
    def test_create_handlers_indicator_class_exception(self, mock_default_params, mock_indicator_classes):
        """Test handling of indicator class instantiation exceptions."""
        # Mock indicator class that raises exception
        mock_bad_class = Mock(side_effect=ValueError("Invalid parameters"))
        
        mock_indicator_classes.get.return_value = mock_bad_class
        mock_default_params.get.return_value = {'period': 14}
        
        config = {
            'bad_indicator': {'period': 14}
        }
        
        factory = IndicatorFactory(config)
        
        # Should raise the exception from indicator class
        with pytest.raises(ValueError, match="Invalid parameters"):
            factory.create_handlers()

    @patch('app.indicators.indicator_factory.INDICATOR_CLASSES')
    @patch('app.indicators.indicator_factory.DEFAULT_PARAMETERS')
    def test_create_handlers_handler_creation_exception(self, mock_default_params, mock_indicator_classes):
        """Test handling of handler creation exceptions."""
        mock_rsi_class = Mock()
        mock_rsi_instance = Mock()
        mock_rsi_class.return_value = mock_rsi_instance
        
        mock_indicator_classes.get.return_value = mock_rsi_class
        mock_default_params.get.return_value = {'period': 14}
        
        config = {
            'rsi_14': {'period': 14}
        }
        
        factory = IndicatorFactory(config)
        
        # Mock IndicatorHandler to raise exception
        with patch.object(IndicatorHandler, '__init__', side_effect=RuntimeError("Handler creation failed")):
            with pytest.raises(RuntimeError, match="Handler creation failed"):
                factory.create_handlers()

    @patch('app.indicators.indicator_factory.INDICATOR_CLASSES')
    @patch('app.indicators.indicator_factory.DEFAULT_PARAMETERS')
    def test_create_handlers_multiple_same_base_type(self, mock_default_params, mock_indicator_classes):
        """Test creating multiple handlers for same base indicator type."""
        mock_sma_class = Mock()
        
        def create_sma_instance(*args, **kwargs):
            instance = Mock()
            instance.period = kwargs.get('period', 20)
            return instance
        
        mock_sma_class.side_effect = create_sma_instance
        
        mock_indicator_classes.get.return_value = mock_sma_class
        mock_default_params.get.return_value = {'period': 20}
        
        config = {
            'sma_10': {'period': 10},
            'sma_20': {'period': 20},
            'sma_50': {'period': 50}
        }
        
        factory = IndicatorFactory(config)
        
        with patch.object(IndicatorHandler, '__init__', return_value=None):
            handlers = factory.create_handlers()
        
        # Should create all three handlers
        assert len(handlers) == 3
        assert 'sma_10' in handlers
        assert 'sma_20' in handlers
        assert 'sma_50' in handlers
        
        # Verify each was called with correct parameters
        expected_calls = [
            ({'period': 10},),
            ({'period': 20},),
            ({'period': 50},)
        ]
        actual_calls = [call.kwargs for call in mock_sma_class.call_args_list]
        for expected in expected_calls:
            assert expected[0] in actual_calls

    def test_create_handlers_empty_config(self):
        """Test creating handlers with empty configuration."""
        config = {}
        
        factory = IndicatorFactory(config)
        handlers = factory.create_handlers()
        
        assert handlers == {}
        assert len(handlers) == 0

    @patch('app.indicators.indicator_factory.INDICATOR_CLASSES')
    @patch('app.indicators.indicator_factory.DEFAULT_PARAMETERS')
    def test_create_handlers_preserves_handler_instances(self, mock_default_params, mock_indicator_classes):
        """Test that created handlers are proper IndicatorHandler instances."""
        mock_rsi_class = Mock()
        mock_rsi_instance = Mock()
        mock_rsi_class.return_value = mock_rsi_instance
        
        mock_indicator_classes.get.return_value = mock_rsi_class
        mock_default_params.get.return_value = {'period': 14}
        
        config = {
            'rsi_14': {'period': 14}
        }
        
        factory = IndicatorFactory(config)
        
        # Create real IndicatorHandler instances
        handlers = factory.create_handlers()
        
        assert len(handlers) == 1
        assert 'rsi_14' in handlers
        assert isinstance(handlers['rsi_14'], IndicatorHandler)
        assert handlers['rsi_14'].name == 'rsi_14'
        assert handlers['rsi_14'].indicator == mock_rsi_instance

    @patch('app.indicators.indicator_factory.INDICATOR_CLASSES')
    @patch('app.indicators.indicator_factory.DEFAULT_PARAMETERS')
    def test_create_handlers_parameter_types_preserved(self, mock_default_params, mock_indicator_classes):
        """Test that parameter types are preserved during merging."""
        mock_class = Mock()
        mock_instance = Mock()
        mock_class.return_value = mock_instance
        
        mock_indicator_classes.get.return_value = mock_class
        mock_default_params.get.return_value = {
            'int_param': 10,
            'float_param': 2.5,
            'str_param': 'default',
            'bool_param': True
        }
        
        config = {
            'test_indicator': {
                'int_param': 20,
                'float_param': 3.0,
                'str_param': 'custom',
                'bool_param': False
            }
        }
        
        factory = IndicatorFactory(config)
        
        with patch.object(IndicatorHandler, '__init__', return_value=None):
            factory.create_handlers()
        
        # Verify types are preserved
        call_args = mock_class.call_args[1]
        assert isinstance(call_args['int_param'], int)
        assert isinstance(call_args['float_param'], float)
        assert isinstance(call_args['str_param'], str)
        assert isinstance(call_args['bool_param'], bool)
        
        # Verify values
        assert call_args['int_param'] == 20
        assert call_args['float_param'] == 3.0
        assert call_args['str_param'] == 'custom'
        assert call_args['bool_param'] == False


class TestIndicatorFactoryIntegration:
    """Integration tests for IndicatorFactory with real registry data."""
    
    def test_factory_with_real_registry_data(self):
        """Test factory works with actual registry configuration."""
        # Import real registry data
        from app.indicators.registry import INDICATOR_CLASSES, DEFAULT_PARAMETERS
        
        # Use a simple config with known indicators
        config = {
            'rsi_14': {'period': 14},
            'sma_20': {'period': 20}
        }
        
        factory = IndicatorFactory(config)
        
        # This should work with real registry data
        handlers = factory.create_handlers()
        
        # Verify handlers were created (exact count depends on what's in registry)
        assert isinstance(handlers, dict)
        
        # If RSI and SMA are in registry, they should be created
        if 'rsi' in INDICATOR_CLASSES:
            assert 'rsi_14' in handlers
            assert isinstance(handlers['rsi_14'], IndicatorHandler)
            
        if 'sma' in INDICATOR_CLASSES:
            assert 'sma_20' in handlers
            assert isinstance(handlers['sma_20'], IndicatorHandler)

    def test_factory_handles_unknown_indicators_gracefully(self):
        """Test factory gracefully handles unknown indicators from real registry."""
        config = {
            'definitely_unknown_indicator_xyz': {'param': 123},
            'another_fake_indicator': {'value': 456}
        }
        
        factory = IndicatorFactory(config)
        handlers = factory.create_handlers()
        
        # Should return empty dict for unknown indicators
        assert handlers == {}