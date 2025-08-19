"""
Unit tests for trader models.
"""

import pytest
from datetime import datetime
from app.trader.risk_manager.models import (
    ScalingConfig, ScaledPosition, PositionGroup, 
    TradeState, PositionType
)
from app.strategy_builder.data.dtos import EntryDecision, StopLossResult


class TestScalingConfig:
    """Test suite for ScalingConfig model."""
    
    def test_default_initialization(self):
        """Test default ScalingConfig initialization."""
        config = ScalingConfig()
        assert config.num_entries == 4
        assert config.scaling_type == "equal"
        assert config.entry_spacing == 0.5
        assert config.max_risk_per_group == 500.0
        assert config.immediate_first_entry is True
        assert config.entry_delay_seconds == 0
    
    def test_equal_scaling_ratios(self):
        """Test equal scaling ratio calculation."""
        config = ScalingConfig(num_entries=4, scaling_type="equal")
        ratios = config.get_size_ratios()
        
        assert len(ratios) == 4
        assert all(r == 0.25 for r in ratios)
        assert sum(ratios) == pytest.approx(1.0)
    
    def test_pyramid_up_scaling_ratios(self):
        """Test pyramid up scaling (increasing sizes)."""
        config = ScalingConfig(num_entries=4, scaling_type="pyramid_up")
        ratios = config.get_size_ratios()
        
        # Should be [0.1, 0.2, 0.3, 0.4]
        expected = [0.1, 0.2, 0.3, 0.4]
        assert len(ratios) == 4
        assert ratios == expected
        assert sum(ratios) == pytest.approx(1.0)
    
    def test_pyramid_down_scaling_ratios(self):
        """Test pyramid down scaling (decreasing sizes)."""
        config = ScalingConfig(num_entries=4, scaling_type="pyramid_down")
        ratios = config.get_size_ratios()
        
        # Should be [0.4, 0.3, 0.2, 0.1]
        expected = [0.4, 0.3, 0.2, 0.1]
        assert len(ratios) == 4
        assert ratios == expected
        assert sum(ratios) == pytest.approx(1.0)
    
    def test_custom_scaling_ratios(self):
        """Test custom scaling ratios."""
        custom = [0.5, 0.3, 0.2]
        config = ScalingConfig(
            num_entries=3,
            scaling_type="custom",
            custom_ratios=custom
        )
        ratios = config.get_size_ratios()
        
        assert ratios == custom
        assert sum(ratios) == pytest.approx(1.0)
    
    def test_validation_valid_config(self):
        """Test validation with valid configuration."""
        config = ScalingConfig(num_entries=3)
        assert config.validate() is True
    
    def test_validation_invalid_entries(self):
        """Test validation with invalid number of entries."""
        config = ScalingConfig(num_entries=0)
        assert config.validate() is False
    
    def test_validation_custom_ratios_mismatch(self):
        """Test validation with mismatched custom ratios."""
        config = ScalingConfig(
            num_entries=3,
            scaling_type="custom",
            custom_ratios=[0.5, 0.5]  # Only 2 ratios for 3 entries
        )
        assert config.validate() is False
    
    def test_validation_custom_ratios_wrong_sum(self):
        """Test validation with custom ratios not summing to 1."""
        config = ScalingConfig(
            num_entries=3,
            scaling_type="custom",
            custom_ratios=[0.3, 0.3, 0.3]  # Sum = 0.9
        )
        assert config.validate() is False


class TestScaledPosition:
    """Test suite for ScaledPosition model."""
    
    def test_initialization(self):
        """Test ScaledPosition initialization."""
        pos = ScaledPosition(
            position_id="pos_1",
            group_id="group_1",
            symbol="XAUUSD",
            direction="long",
            entry_price=3000.0,
            position_size=0.5
        )
        
        assert pos.position_id == "pos_1"
        assert pos.group_id == "group_1"
        assert pos.symbol == "XAUUSD"
        assert pos.direction == "long"
        assert pos.entry_price == 3000.0
        assert pos.position_size == 0.5
        assert pos.state == TradeState.PENDING
        assert pos.position_type == PositionType.INITIAL
        assert pos.filled_size == 0.0
        assert pos.filled_price is None
    
    def test_is_filled_property(self):
        """Test is_filled property."""
        pos = ScaledPosition(
            position_id="pos_1",
            group_id="group_1",
            symbol="XAUUSD",
            direction="long",
            entry_price=3000.0,
            position_size=1.0
        )
        
        assert pos.is_filled is False
        
        # Update with full fill
        pos.update_fill(1.0, 3000.0)
        assert pos.is_filled is True
    
    def test_fill_percentage(self):
        """Test fill percentage calculation."""
        pos = ScaledPosition(
            position_id="pos_1",
            group_id="group_1",
            symbol="XAUUSD",
            direction="long",
            entry_price=3000.0,
            position_size=1.0
        )
        
        assert pos.fill_percentage == 0.0
        
        pos.update_fill(0.5, 3000.0)
        assert pos.fill_percentage == 50.0
        
        pos.update_fill(0.5, 3000.0)
        assert pos.fill_percentage == 100.0
    
    def test_update_fill(self):
        """Test updating position with fill information."""
        pos = ScaledPosition(
            position_id="pos_1",
            group_id="group_1",
            symbol="XAUUSD",
            direction="long",
            entry_price=3000.0,
            position_size=1.0
        )
        
        # Partial fill
        pos.update_fill(0.3, 2999.5)
        assert pos.filled_size == 0.3
        assert pos.filled_price == 2999.5
        assert pos.state == TradeState.PARTIAL_FILLED
        assert pos.filled_at is not None
        
        # Additional fill
        pos.update_fill(0.7, 3000.5)
        assert pos.filled_size == 1.0
        assert pos.filled_price == 3000.5  # Last fill price
        assert pos.state == TradeState.ACTIVE


class TestPositionGroup:
    """Test suite for PositionGroup model."""
    
    @pytest.fixture
    def entry_decision(self):
        """Create a sample entry decision."""
        return EntryDecision(
            symbol='XAUUSD',
            strategy_name='test-strategy',
            magic=12345,
            direction='long',
            entry_signals='BUY',
            entry_price=3000.0,
            position_size=1.0,
            stop_loss=StopLossResult(type='fixed', level=2995.0, trailing=False),
            take_profit=None,
            decision_time=datetime.now()
        )
    
    def test_initialization(self, entry_decision):
        """Test PositionGroup initialization."""
        group = PositionGroup(
            group_id="group_1",
            symbol="XAUUSD",
            strategy_name="test-strategy",
            direction="long",
            original_decision=entry_decision,
            total_target_size=1.0,
            num_entries=4,
            scaling_strategy="equal",
            total_risk_amount=500.0
        )
        
        assert group.group_id == "group_1"
        assert group.symbol == "XAUUSD"
        assert group.strategy_name == "test-strategy"
        assert group.direction == "long"
        assert group.total_target_size == 1.0
        assert group.num_entries == 4
        assert group.total_risk_amount == 500.0
        assert len(group.positions) == 0
    
    def test_add_position(self, entry_decision):
        """Test adding positions to group."""
        group = PositionGroup(
            group_id="group_1",
            symbol="XAUUSD",
            strategy_name="test",
            direction="long",
            original_decision=entry_decision,
            total_target_size=1.0,
            num_entries=2
        )
        
        pos1 = ScaledPosition(
            position_id="pos_1",
            group_id="different_group",
            symbol="XAUUSD",
            direction="long",
            entry_price=3000.0,
            position_size=0.5
        )
        
        group.add_position(pos1)
        
        assert len(group.positions) == 1
        assert pos1.group_id == "group_1"  # Should be updated
    
    def test_active_positions_property(self, entry_decision):
        """Test active_positions property."""
        group = PositionGroup(
            group_id="group_1",
            symbol="XAUUSD",
            strategy_name="test",
            direction="long",
            original_decision=entry_decision,
            total_target_size=1.0,
            num_entries=2
        )
        
        # Add positions with different states
        pos1 = ScaledPosition("pos_1", "group_1", "XAUUSD", "long", 3000.0, 0.5)
        pos1.state = TradeState.ACTIVE
        
        pos2 = ScaledPosition("pos_2", "group_1", "XAUUSD", "long", 2995.0, 0.5)
        pos2.state = TradeState.PENDING
        
        group.positions = [pos1, pos2]
        
        assert len(group.active_positions) == 1
        assert group.active_positions[0] == pos1
    
    def test_pending_positions_property(self, entry_decision):
        """Test pending_positions property."""
        group = PositionGroup(
            group_id="group_1",
            symbol="XAUUSD",
            strategy_name="test",
            direction="long",
            original_decision=entry_decision,
            total_target_size=1.0,
            num_entries=2
        )
        
        pos1 = ScaledPosition("pos_1", "group_1", "XAUUSD", "long", 3000.0, 0.5)
        pos1.state = TradeState.PENDING
        
        pos2 = ScaledPosition("pos_2", "group_1", "XAUUSD", "long", 2995.0, 0.5)
        pos2.state = TradeState.PENDING
        
        group.positions = [pos1, pos2]
        
        assert len(group.pending_positions) == 2
    
    def test_is_fully_filled(self, entry_decision):
        """Test is_fully_filled property."""
        group = PositionGroup(
            group_id="group_1",
            symbol="XAUUSD",
            strategy_name="test",
            direction="long",
            original_decision=entry_decision,
            total_target_size=1.0,
            num_entries=2
        )
        
        pos1 = ScaledPosition("pos_1", "group_1", "XAUUSD", "long", 3000.0, 0.5)
        pos2 = ScaledPosition("pos_2", "group_1", "XAUUSD", "long", 2995.0, 0.5)
        
        group.positions = [pos1, pos2]
        
        # Not filled initially
        assert group.is_fully_filled is False
        
        # Fill both positions
        pos1.update_fill(0.5, 3000.0)
        pos2.update_fill(0.5, 2995.0)
        
        assert group.is_fully_filled is True
    
    def test_update_group_metrics(self, entry_decision):
        """Test updating group metrics."""
        group = PositionGroup(
            group_id="group_1",
            symbol="XAUUSD",
            strategy_name="test",
            direction="long",
            original_decision=entry_decision,
            total_target_size=1.0,
            num_entries=2
        )
        
        pos1 = ScaledPosition("pos_1", "group_1", "XAUUSD", "long", 3000.0, 0.5)
        pos1.state = TradeState.ACTIVE
        pos1.filled_size = 0.5
        pos1.filled_price = 3000.0
        
        pos2 = ScaledPosition("pos_2", "group_1", "XAUUSD", "long", 2996.0, 0.5)
        pos2.state = TradeState.ACTIVE
        pos2.filled_size = 0.5
        pos2.filled_price = 2996.0
        
        group.positions = [pos1, pos2]
        group.update_group_metrics()
        
        # Average: (3000*0.5 + 2996*0.5) / 1.0 = 2998
        assert group.average_entry_price == 2998.0
        assert group.total_filled_size == 1.0
    
    def test_calculate_unrealized_pnl_long(self, entry_decision):
        """Test PnL calculation for long positions."""
        group = PositionGroup(
            group_id="group_1",
            symbol="XAUUSD",
            strategy_name="test",
            direction="long",
            original_decision=entry_decision,
            total_target_size=1.0,
            num_entries=1
        )
        
        pos = ScaledPosition("pos_1", "group_1", "XAUUSD", "long", 3000.0, 1.0)
        pos.state = TradeState.ACTIVE
        pos.filled_size = 1.0
        pos.filled_price = 3000.0
        
        group.positions = [pos]
        
        # Current price 3005, gain of 5 points
        pnl = group.calculate_unrealized_pnl(3005.0)
        assert pnl == 5.0
        
        # Current price 2995, loss of 5 points
        pnl = group.calculate_unrealized_pnl(2995.0)
        assert pnl == -5.0
    
    def test_calculate_unrealized_pnl_short(self, entry_decision):
        """Test PnL calculation for short positions."""
        group = PositionGroup(
            group_id="group_1",
            symbol="BTCUSD",
            strategy_name="test",
            direction="short",
            original_decision=entry_decision,
            total_target_size=1.0,
            num_entries=1
        )
        
        pos = ScaledPosition("pos_1", "group_1", "BTCUSD", "short", 117400.0, 1.0)
        pos.state = TradeState.ACTIVE
        pos.filled_size = 1.0
        pos.filled_price = 117400.0
        
        group.positions = [pos]
        
        # Current price 117300, gain of 100 points for short
        pnl = group.calculate_unrealized_pnl(117300.0)
        assert pnl == 100.0
        
        # Current price 117500, loss of 100 points for short
        pnl = group.calculate_unrealized_pnl(117500.0)
        assert pnl == -100.0
    
    def test_get_position_summary(self, entry_decision):
        """Test getting position summary."""
        group = PositionGroup(
            group_id="group_123",
            symbol="XAUUSD",
            strategy_name="test-strategy",
            direction="long",
            original_decision=entry_decision,
            total_target_size=2.0,
            num_entries=2
        )
        
        pos1 = ScaledPosition("pos_1", "group_123", "XAUUSD", "long", 3000.0, 1.0)
        pos1.state = TradeState.ACTIVE
        
        pos2 = ScaledPosition("pos_2", "group_123", "XAUUSD", "long", 2995.0, 1.0)
        pos2.state = TradeState.PENDING
        
        group.positions = [pos1, pos2]
        
        summary = group.get_position_summary()
        
        assert summary['group_id'] == "group_123"
        assert summary['symbol'] == "XAUUSD"
        assert summary['strategy'] == "test-strategy"
        assert summary['direction'] == "long"
        assert summary['total_positions'] == 2
        assert summary['active_positions'] == 1
        assert summary['pending_positions'] == 1
        assert summary['total_target_size'] == 2.0