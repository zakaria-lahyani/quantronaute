"""
Unit tests for position sizing implementations.
"""

import pytest
from unittest.mock import Mock
from pydantic import ValidationError as PydanticValidationError

from app.entry_manager.position_sizing.fixed import FixedPositionSizer
from app.entry_manager.position_sizing.percentage import PercentagePositionSizer
from app.entry_manager.position_sizing.volatility import VolatilityPositionSizer
from app.entry_manager.position_sizing.factory import create_position_sizer
from app.entry_manager.core.exceptions import ValidationError, CalculationError, UnsupportedConfigurationError
from app.strategy_builder.core.domain.models import PositionSizing
from app.strategy_builder.core.domain.enums import PositionSizingTypeEnum


class TestFixedPositionSizer:
    """Test cases for FixedPositionSizer."""
    
    def test_creation_valid(self):
        """Test creating a valid fixed position sizer."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.FIXED,
            value=1000.0
        )
        sizer = FixedPositionSizer(config)
        
        assert sizer.config.value == 1000.0
        assert sizer.config.type == PositionSizingTypeEnum.FIXED
    
    def test_creation_invalid_type(self):
        """Test creation with wrong type raises error."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.PERCENTAGE,
            value=1000.0
        )
        
        with pytest.raises(ValidationError) as exc_info:
            FixedPositionSizer(config)
        assert "Expected FIXED position sizing type, got PositionSizingTypeEnum.PERCENTAGE" in str(exc_info.value)
    
    def test_creation_negative_value(self):
        """Test creation with negative value raises Pydantic error."""
        with pytest.raises(PydanticValidationError):
            PositionSizing(
                type=PositionSizingTypeEnum.FIXED,
                value=-100.0
            )
    
    def test_calculate_position_size(self):
        """Test calculating fixed position size."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.FIXED,
            value=1500.0
        )
        sizer = FixedPositionSizer(config)
        
        # Fixed sizer ignores entry price and other parameters
        size = sizer.calculate_position_size(entry_price=1.1000)
        assert size == 1500.0
        
        size = sizer.calculate_position_size(
            entry_price=2.0000,
            account_balance=10000.0,
            volatility=0.001
        )
        assert size == 1500.0
    
    def test_calculate_with_invalid_entry_price(self):
        """Test calculation with invalid entry price."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.FIXED,
            value=1000.0
        )
        sizer = FixedPositionSizer(config)
        
        with pytest.raises(ValidationError) as exc_info:
            sizer.calculate_position_size(entry_price=0)
        assert "Entry price must be positive" in str(exc_info.value)
        
        with pytest.raises(ValidationError):
            sizer.calculate_position_size(entry_price=-1.0)
    
    def test_with_logger(self):
        """Test fixed sizer with custom logger."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.FIXED,
            value=1000.0
        )
        logger = Mock()
        sizer = FixedPositionSizer(config, logger=logger)
        
        size = sizer.calculate_position_size(entry_price=1.1000)
        assert size == 1000.0
        logger.debug.assert_called()


class TestPercentagePositionSizer:
    """Test cases for PercentagePositionSizer."""
    
    def test_creation_valid(self):
        """Test creating a valid percentage position sizer."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.PERCENTAGE,
            value=2.5
        )
        sizer = PercentagePositionSizer(config)
        
        assert sizer.config.value == 2.5
        assert sizer.config.type == PositionSizingTypeEnum.PERCENTAGE
    
    def test_creation_invalid_type(self):
        """Test creation with wrong type raises error."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.FIXED,
            value=2.5
        )
        
        with pytest.raises(ValidationError) as exc_info:
            PercentagePositionSizer(config)
        assert "Expected PERCENTAGE position sizing type, got PositionSizingTypeEnum.FIXED" in str(exc_info.value)
    
    def test_creation_invalid_percentage(self):
        """Test creation with invalid percentage raises error."""
        # Negative percentage should fail
        with pytest.raises(PydanticValidationError):
            PositionSizing(
                type=PositionSizingTypeEnum.PERCENTAGE,
                value=-5.0
            )
    
    def test_calculate_with_account_balance(self):
        """Test calculating percentage position size with account balance."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.PERCENTAGE,
            value=2.5
        )
        sizer = PercentagePositionSizer(config)
        
        size = sizer.calculate_position_size(
            entry_price=1.1000,
            account_balance=10000.0
        )
        assert size == 250.0  # 2.5% of 10000
        
        size = sizer.calculate_position_size(
            entry_price=1.1000,
            account_balance=50000.0
        )
        assert size == 1250.0  # 2.5% of 50000
    
    def test_calculate_without_account_balance(self):
        """Test calculating percentage position size without account balance."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.PERCENTAGE,
            value=2.5
        )
        sizer = PercentagePositionSizer(config)
        
        with pytest.raises(CalculationError) as exc_info:
            sizer.calculate_position_size(entry_price=1.1000)
        assert "Account balance is required for percentage-based position sizing" in str(exc_info.value)
        
        with pytest.raises(CalculationError):
            sizer.calculate_position_size(
                entry_price=1.1000,
                account_balance=None
            )
    
    def test_calculate_with_zero_balance(self):
        """Test calculating with zero account balance."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.PERCENTAGE,
            value=2.5
        )
        sizer = PercentagePositionSizer(config)
        
        with pytest.raises(ValidationError) as exc_info:
            sizer.calculate_position_size(
                entry_price=1.1000,
                account_balance=0
            )
        assert "Account balance must be positive" in str(exc_info.value)
    
    def test_calculate_with_negative_balance(self):
        """Test calculating with negative account balance."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.PERCENTAGE,
            value=2.5
        )
        sizer = PercentagePositionSizer(config)
        
        with pytest.raises(ValidationError):
            sizer.calculate_position_size(
                entry_price=1.1000,
                account_balance=-1000.0
            )


class TestVolatilityPositionSizer:
    """Test cases for VolatilityPositionSizer."""
    
    def test_creation_valid(self):
        """Test creating a valid volatility position sizer."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.VOLATILITY,
            value=2.0  # percentage of account balance to risk
        )
        sizer = VolatilityPositionSizer(config)
        
        assert sizer.config.value == 2.0
        assert sizer.config.type == PositionSizingTypeEnum.VOLATILITY
    
    def test_creation_without_multiplier(self):
        """Test creation uses default volatility multiplier via kwargs."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.VOLATILITY,
            value=2.0  # risk percentage
        )
        sizer = VolatilityPositionSizer(config)
        
        # Should create successfully (multiplier passed as kwargs in calculate method)
        assert sizer.config.value == 2.0
        assert sizer.config.type == PositionSizingTypeEnum.VOLATILITY
    
    def test_creation_invalid_type(self):
        """Test creation with wrong type raises error."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.FIXED,
            value=1000.0
        )
        
        with pytest.raises(ValidationError) as exc_info:
            VolatilityPositionSizer(config)
        assert "Expected VOLATILITY position sizing type, got PositionSizingTypeEnum.FIXED" in str(exc_info.value)
    
    def test_calculate_with_volatility(self):
        """Test calculating volatility-based position size."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.VOLATILITY,
            value=2.0  # 2% risk
        )
        sizer = VolatilityPositionSizer(config)
        
        # Low volatility = larger position
        size = sizer.calculate_position_size(
            entry_price=1.1000,
            volatility=0.001,
            account_balance=10000.0,
            volatility_multiplier=2.0
        )
        # Risk amount = 10000 * 0.02 = 200
        # Position size = 200 / (0.001 * 2.0) = 100000
        assert size == 100000.0
        
        # High volatility = smaller position
        size = sizer.calculate_position_size(
            entry_price=1.1000,
            volatility=0.01,
            account_balance=10000.0,
            volatility_multiplier=2.0
        )
        # Position size = 200 / (0.01 * 2.0) = 10000
        assert size == 10000.0
    
    def test_calculate_without_volatility(self):
        """Test calculating without volatility raises error."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.VOLATILITY,
            value=2.0
        )
        sizer = VolatilityPositionSizer(config)
        
        # Without volatility, should raise error
        with pytest.raises(CalculationError) as exc_info:
            sizer.calculate_position_size(
                entry_price=1.1000,
                account_balance=10000.0
            )
        assert "Valid volatility value is required" in str(exc_info.value)
        
        with pytest.raises(CalculationError):
            sizer.calculate_position_size(
                entry_price=1.1000,
                account_balance=10000.0,
                volatility=None
            )
    
    def test_calculate_with_zero_volatility(self):
        """Test calculating with zero volatility raises error."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.VOLATILITY,
            value=2.0
        )
        sizer = VolatilityPositionSizer(config)
        
        # Zero volatility should raise error to avoid division by zero
        with pytest.raises(CalculationError) as exc_info:
            sizer.calculate_position_size(
                entry_price=1.1000,
                account_balance=10000.0,
                volatility=0.0
            )
        assert "Valid volatility value is required" in str(exc_info.value)
    
    def test_calculate_with_negative_volatility(self):
        """Test calculating with negative volatility."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.VOLATILITY,
            value=2.0
        )
        sizer = VolatilityPositionSizer(config)
        
        with pytest.raises(ValidationError) as exc_info:
            sizer.calculate_position_size(
                entry_price=1.1000,
                account_balance=10000.0,
                volatility=-0.001
            )
        assert "Volatility cannot be negative" in str(exc_info.value)
    
    def test_volatility_scaling(self):
        """Test that volatility scaling works correctly."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.VOLATILITY,
            value=2.0  # 2% risk
        )
        sizer = VolatilityPositionSizer(config)
        
        # Formula: position_size = risk_amount / (volatility * volatility_multiplier)
        # Risk amount = 10000 * 0.02 = 200
        
        size1 = sizer.calculate_position_size(
            entry_price=1.1000,
            account_balance=10000.0,
            volatility=0.002,
            volatility_multiplier=1.0
        )
        # Should be 200 / (0.002 * 1.0) = 100000
        assert abs(size1 - 100000.0) < 0.01
        
        size2 = sizer.calculate_position_size(
            entry_price=1.1000,
            account_balance=10000.0,
            volatility=0.0005,
            volatility_multiplier=1.0
        )
        # Should be 200 / (0.0005 * 1.0) = 400000
        assert abs(size2 - 400000.0) < 0.01


class TestPositionSizerFactory:
    """Test position sizer factory function."""
    
    def test_create_fixed_sizer(self):
        """Test creating fixed position sizer via factory."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.FIXED,
            value=1000.0
        )
        sizer = create_position_sizer(config)
        
        assert isinstance(sizer, FixedPositionSizer)
        assert sizer.calculate_position_size(entry_price=1.1) == 1000.0
    
    def test_create_percentage_sizer(self):
        """Test creating percentage position sizer via factory."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.PERCENTAGE,
            value=5.0
        )
        sizer = create_position_sizer(config)
        
        assert isinstance(sizer, PercentagePositionSizer)
        size = sizer.calculate_position_size(
            entry_price=1.1,
            account_balance=10000.0
        )
        assert size == 500.0
    
    def test_create_volatility_sizer(self):
        """Test creating volatility position sizer via factory."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.VOLATILITY,
            value=2.0
        )
        sizer = create_position_sizer(config)
        
        assert isinstance(sizer, VolatilityPositionSizer)
    
    def test_create_with_logger(self):
        """Test creating sizer with custom logger."""
        config = PositionSizing(
            type=PositionSizingTypeEnum.FIXED,
            value=1000.0
        )
        logger = Mock()
        sizer = create_position_sizer(config, logger=logger)
        
        assert sizer.logger == logger
    
    def test_create_invalid_type(self):
        """Test creating sizer with invalid type."""
        # Create a mock config with invalid type
        config = Mock()
        config.type = "INVALID_TYPE"
        
        with pytest.raises(UnsupportedConfigurationError) as exc_info:
            create_position_sizer(config)
        assert "Unsupported position sizing type: INVALID_TYPE" in str(exc_info.value)