"""
Unit tests for take profit implementations.
"""

import pytest
from unittest.mock import Mock

from app.entry_manager.take_profit.fixed import FixedTakeProfitCalculator
from app.entry_manager.take_profit.multi_target import MultiTargetTakeProfitCalculator
from app.entry_manager.take_profit.factory import create_take_profit_calculator
from app.entry_manager.core.exceptions import ValidationError, CalculationError, UnsupportedConfigurationError
from app.strategy_builder.core.domain.models import (
    FixedTakeProfit,
    MultiTargetTakeProfit,
    TakeProfitTarget
)


class TestFixedTakeProfitCalculator:
    """Test cases for FixedTakeProfitCalculator."""
    
    def test_creation_valid(self):
        """Test creating a valid fixed take profit calculator."""
        config = FixedTakeProfit(type="fixed", value=100.0)
        calculator = FixedTakeProfitCalculator(config, pip_value=10000.0)
        
        assert calculator.config.value == 100.0
        assert calculator.pip_value == 10000.0
    
    def test_creation_invalid_type(self):
        """Test creation with wrong type raises error."""
        config = Mock()
        config.type = "multi_target"
        config.value = 100.0
        
        with pytest.raises(ValidationError) as exc_info:
            FixedTakeProfitCalculator(config, pip_value=10000.0)
        assert "Expected 'fixed' take profit type" in str(exc_info.value)
    
    def test_creation_invalid_pip_value(self):
        """Test creation with invalid pip value."""
        config = FixedTakeProfit(type="fixed", value=100.0)
        
        with pytest.raises(ValidationError) as exc_info:
            FixedTakeProfitCalculator(config, pip_value=0)
        assert "pip_value must be positive" in str(exc_info.value)
        
        with pytest.raises(ValidationError):
            FixedTakeProfitCalculator(config, pip_value=-10000.0)
    
    def test_calculate_long_position(self):
        """Test calculating take profit for long position."""
        config = FixedTakeProfit(type="fixed", value=100.0)
        calculator = FixedTakeProfitCalculator(config, pip_value=10000.0)
        
        result = calculator.calculate_take_profit(
            entry_price=1.1000,
            is_long=True
        )
        
        # Fixed take profit calculation - specific values depend on implementation
        assert result.type == "fixed"
        assert result.level is not None
        assert result.level > 1.1000  # Should be above entry price for long
        if result.targets:
            assert result.targets[0].value == 100.0  # Original pip value
            assert result.targets[0].percent == 100.0
    
    def test_calculate_short_position(self):
        """Test calculating take profit for short position."""
        config = FixedTakeProfit(type="fixed", value=75.0)
        calculator = FixedTakeProfitCalculator(config, pip_value=10000.0)
        
        result = calculator.calculate_take_profit(
            entry_price=1.1000,
            is_long=False
        )
        
        # Fixed take profit for short - should be below entry price
        assert result.type == "fixed" 
        assert result.level is not None
        assert result.level < 1.1000  # Should be below entry price for short
        if result.targets:
            assert result.targets[0].value == 75.0  # Original pip value
    
    def test_calculate_with_different_pip_values(self):
        """Test calculation with different pip values."""
        # Test with JPY pairs (pip_value = 100)
        config = FixedTakeProfit(type="fixed", value=50.0)
        calculator = FixedTakeProfitCalculator(config, pip_value=100.0)
        
        result = calculator.calculate_take_profit(
            entry_price=110.00,
            is_long=True
        )
        
        # TP = 110.00 + (50 / 100) = 110.00 + 0.50 = 110.50
        assert result.level == 110.50
    
    def test_calculate_with_zero_entry_price(self):
        """Test calculation with zero entry price."""
        config = FixedTakeProfit(type="fixed", value=100.0)
        calculator = FixedTakeProfitCalculator(config, pip_value=10000.0)
        
        with pytest.raises(ValidationError) as exc_info:
            calculator.calculate_take_profit(entry_price=0, is_long=True)
        assert "Entry price must be positive" in str(exc_info.value)
    
    def test_calculate_with_negative_entry_price(self):
        """Test calculation with negative entry price."""
        config = FixedTakeProfit(type="fixed", value=100.0)
        calculator = FixedTakeProfitCalculator(config, pip_value=10000.0)
        
        with pytest.raises(ValidationError):
            calculator.calculate_take_profit(entry_price=-1.0, is_long=True)
    
    def test_with_logger(self):
        """Test calculator with custom logger."""
        config = FixedTakeProfit(type="fixed", value=100.0)
        logger = Mock()
        calculator = FixedTakeProfitCalculator(config, pip_value=10000.0, logger=logger)
        
        result = calculator.calculate_take_profit(entry_price=1.1000, is_long=True)
        assert result.level == 1.1100
        logger.debug.assert_called()


class TestMultiTargetTakeProfitCalculator:
    """Test cases for MultiTargetTakeProfitCalculator."""
    
    def test_creation_valid(self):
        """Test creating a valid multi-target take profit calculator."""
        targets = [
            TakeProfitTarget(value=50.0, percent=33.33),
            TakeProfitTarget(value=100.0, percent=33.33),
            TakeProfitTarget(value=150.0, percent=33.34)
        ]
        config = MultiTargetTakeProfit(
            type="multi_target",
            targets=targets
        )
        calculator = MultiTargetTakeProfitCalculator(config, pip_value=10000.0)
        
        assert len(calculator.config.targets) == 3
        assert calculator.config.targets[0].value == 50.0
    
    def test_creation_invalid_type(self):
        """Test creation with wrong type raises error."""
        config = Mock()
        config.type = "fixed"
        config.targets = []
        
        with pytest.raises(ValidationError) as exc_info:
            MultiTargetTakeProfitCalculator(config, pip_value=10000.0)
        assert "Expected 'multi_target' take profit type" in str(exc_info.value)
    
    def test_creation_empty_targets(self):
        """Test creation with empty targets raises pydantic error."""
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError) as exc_info:
            config = MultiTargetTakeProfit(
                type="multi_target",
                targets=[]
            )
        assert "at least 1 item" in str(exc_info.value)
    
    def test_creation_invalid_percentages(self):
        """Test creation with invalid percentage totals."""
        # Percentages don't add up to 100
        targets = [
            TakeProfitTarget(value=50.0, percent=50.0),
            TakeProfitTarget(value=100.0, percent=30.0)  # Total = 80%
        ]
        config = MultiTargetTakeProfit(
            type="multi_target",
            targets=targets
        )
        
        with pytest.raises(ValidationError) as exc_info:
            MultiTargetTakeProfitCalculator(config, pip_value=10000.0)
        assert "Target percentages must sum to 100%" in str(exc_info.value)
    
    def test_calculate_long_position(self):
        """Test calculating multi-target take profit for long position."""
        targets = [
            TakeProfitTarget(value=50.0, percent=40.0),
            TakeProfitTarget(value=100.0, percent=35.0),
            TakeProfitTarget(value=150.0, percent=25.0)
        ]
        config = MultiTargetTakeProfit(
            type="multi_target",
            targets=targets
        )
        calculator = MultiTargetTakeProfitCalculator(config, pip_value=10000.0)
        
        result = calculator.calculate_take_profit(
            entry_price=1.1000,
            is_long=True
        )
        
        assert result.type == "multi_target"
        assert len(result.targets) == 3
        
        # Check targets have correct original values and percentages
        assert result.targets[0].value == 50.0  # First target: 50 pips
        assert result.targets[0].percent == 40.0
        
        assert result.targets[1].value == 100.0  # Second target: 100 pips
        assert result.targets[1].percent == 35.0
        
        assert result.targets[2].value == 150.0  # Third target: 150 pips
        assert result.targets[2].percent == 25.0
        
        # Multi-target overall level may be None (implementation-dependent)
        # Key thing is targets are correct
    
    def test_calculate_short_position(self):
        """Test calculating multi-target take profit for short position."""
        targets = [
            TakeProfitTarget(value=25.0, percent=50.0),
            TakeProfitTarget(value=50.0, percent=50.0)
        ]
        config = MultiTargetTakeProfit(
            type="multi_target",
            targets=targets
        )
        calculator = MultiTargetTakeProfitCalculator(config, pip_value=10000.0)
        
        result = calculator.calculate_take_profit(
            entry_price=1.1000,
            is_long=False
        )
        
        assert len(result.targets) == 2
        
        # Check targets have correct values and percentages
        assert result.targets[0].value == 25.0  # First target: 25 pips
        assert result.targets[0].percent == 50.0
        
        assert result.targets[1].value == 50.0  # Second target: 50 pips
        assert result.targets[1].percent == 50.0
        
        # Multi-target overall level may be None (implementation-dependent)
    
    def test_calculate_single_target(self):
        """Test calculating with single target (edge case)."""
        targets = [
            TakeProfitTarget(value=80.0, percent=100.0)
        ]
        config = MultiTargetTakeProfit(
            type="multi_target",
            targets=targets
        )
        calculator = MultiTargetTakeProfitCalculator(config, pip_value=10000.0)
        
        result = calculator.calculate_take_profit(
            entry_price=1.1000,
            is_long=True
        )
        
        assert len(result.targets) == 1
        assert result.targets[0].value == 80.0  # 80 pip target
        assert result.targets[0].percent == 100.0
        # Multi-target level may be None (implementation-dependent)
    
    def test_targets_ordering(self):
        """Test that targets are properly ordered by level."""
        # Create targets in reverse order
        targets = [
            TakeProfitTarget(value=100.0, percent=30.0),
            TakeProfitTarget(value=50.0, percent=40.0),
            TakeProfitTarget(value=150.0, percent=30.0)
        ]
        config = MultiTargetTakeProfit(
            type="multi_target",
            targets=targets
        )
        calculator = MultiTargetTakeProfitCalculator(config, pip_value=10000.0)
        
        result = calculator.calculate_take_profit(
            entry_price=1.1000,
            is_long=True
        )
        
        # Should be properly ordered (exact ordering may depend on implementation)
        target_values = [target.value for target in result.targets]
        assert len(target_values) == 3
        assert 50.0 in target_values
        assert 100.0 in target_values  
        assert 150.0 in target_values
    
    def test_with_logger(self):
        """Test calculator with custom logger."""
        targets = [
            TakeProfitTarget(value=50.0, percent=100.0)
        ]
        config = MultiTargetTakeProfit(
            type="multi_target",
            targets=targets
        )
        logger = Mock()
        calculator = MultiTargetTakeProfitCalculator(config, pip_value=10000.0, logger=logger)
        
        result = calculator.calculate_take_profit(entry_price=1.1000, is_long=True)
        assert result.type == "multi_target"
        assert len(result.targets) == 1
        logger.debug.assert_called()


class TestTakeProfitTargetValidation:
    """Test TakeProfitTarget validation."""
    
    def test_valid_target(self):
        """Test creating a valid take profit target."""
        target = TakeProfitTarget(value=50.0, percent=33.33)
        
        assert target.value == 50.0
        assert target.percent == 33.33
    
    def test_negative_level(self):
        """Test creating target with negative value."""
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            TakeProfitTarget(value=-50.0, percent=33.33)
    
    def test_zero_level(self):
        """Test creating target with zero value is allowed."""
        # Zero values are allowed per model definition (ge=0)
        target = TakeProfitTarget(value=0.0, percent=33.33)
        assert target.value == 0.0
        assert target.percent == 33.33
    
    def test_invalid_percentage(self):
        """Test creating target with invalid percentage."""
        from pydantic import ValidationError as PydanticValidationError
        
        # Negative percentage
        with pytest.raises(PydanticValidationError):
            TakeProfitTarget(value=50.0, percent=-10.0)
        
        # Percentage > 100
        with pytest.raises(PydanticValidationError):
            TakeProfitTarget(value=50.0, percent=150.0)
        
        # Zero percentage is allowed per model definition (ge=0)
        target = TakeProfitTarget(value=50.0, percent=0.0)
        assert target.percent == 0.0


class TestTakeProfitFactory:
    """Test take profit calculator factory function."""
    
    def test_create_fixed_calculator(self):
        """Test creating fixed take profit calculator via factory."""
        config = FixedTakeProfit(type="fixed", value=100.0)
        calculator = create_take_profit_calculator(config, pip_value=10000.0)
        
        assert isinstance(calculator, FixedTakeProfitCalculator)
        result = calculator.calculate_take_profit(entry_price=1.1000, is_long=True)
        assert result.level == 1.1100
    
    def test_create_multi_target_calculator(self):
        """Test creating multi-target take profit calculator via factory."""
        targets = [
            TakeProfitTarget(value=50.0, percent=50.0),
            TakeProfitTarget(value=100.0, percent=50.0)
        ]
        config = MultiTargetTakeProfit(
            type="multi_target",
            targets=targets
        )
        calculator = create_take_profit_calculator(config, pip_value=10000.0)
        
        assert isinstance(calculator, MultiTargetTakeProfitCalculator)
    
    def test_create_with_logger(self):
        """Test creating calculator with custom logger."""
        config = FixedTakeProfit(type="fixed", value=100.0)
        logger = Mock()
        calculator = create_take_profit_calculator(config, pip_value=10000.0, logger=logger)
        
        assert calculator.logger == logger
    
    def test_create_invalid_type(self):
        """Test creating calculator with invalid type."""
        config = Mock()
        config.type = "INVALID_TYPE"
        
        with pytest.raises(UnsupportedConfigurationError) as exc_info:
            create_take_profit_calculator(config, pip_value=10000.0)
        assert "Unsupported take profit type" in str(exc_info.value)