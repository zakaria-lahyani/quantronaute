"""
Unit tests for RiskManager.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from app.trader.risk_manager import RiskManager
from app.trader.models import ScalingConfig
from app.strategy_builder.data.dtos import EntryDecision, StopLossResult, TakeProfitResult, TPLevel


class TestRiskManager:
    """Test suite for RiskManager."""
    
    @pytest.fixture
    def scaling_config(self):
        """Create a test scaling configuration."""
        return ScalingConfig(
            num_entries=4,
            scaling_type="equal",
            entry_spacing=0.5,
            max_risk_per_group=1000.0
        )
    
    @pytest.fixture
    def risk_manager(self, scaling_config):
        """Create a RiskManager instance for testing."""
        return RiskManager(scaling_config)
    
    @pytest.fixture
    def entry_decision_long(self):
        """Create a sample long entry decision."""
        return EntryDecision(
            symbol='XAUUSD',
            strategy_name='test-strategy',
            magic=12345,
            direction='long',
            entry_signals='BUY',
            entry_price=3000.0,
            position_size=1.0,
            stop_loss=StopLossResult(
                type='fixed',
                level=2995.0,
                trailing=False
            ),
            take_profit=TakeProfitResult(
                type='multi_target',
                targets=[
                    TPLevel(level=3005.0, value=1.0, percent=60.0, move_stop=True),
                    TPLevel(level=3010.0, value=2.0, percent=40.0, move_stop=False)
                ]
            ),
            decision_time=datetime.now()
        )
    
    @pytest.fixture
    def entry_decision_short(self):
        """Create a sample short entry decision."""
        return EntryDecision(
            symbol='BTCUSD',
            strategy_name='btc-strategy',
            magic=67890,
            direction='short',
            entry_signals='SELL',
            entry_price=117400.0,
            position_size=1.0,
            stop_loss=StopLossResult(
                type='fixed',
                level=117900.0,
                trailing=False
            ),
            take_profit=None,
            decision_time=datetime.now()
        )
    
    def test_initialization(self, scaling_config):
        """Test RiskManager initialization."""
        rm = RiskManager(scaling_config)
        assert rm.scaling_config == scaling_config
        assert rm.group_stop_loss is True
        assert rm.position_groups == {}
        assert rm.active_tickets == {}
    
    def test_calculate_scaled_entry_prices_long(self, risk_manager):
        """Test entry price calculation for long positions."""
        current_price = 3000.0
        entry_prices = risk_manager._calculate_scaled_entry_prices(current_price, 'long')
        
        # For long, prices should decrease (buying dips)
        assert len(entry_prices) == 4
        assert entry_prices[0] == 3000.0
        assert entry_prices[1] == pytest.approx(2985.0)  # 0.5% below
        assert entry_prices[2] == pytest.approx(2970.0)  # 1% below
        assert entry_prices[3] == pytest.approx(2955.0)  # 1.5% below
    
    def test_calculate_scaled_entry_prices_short(self, risk_manager):
        """Test entry price calculation for short positions."""
        current_price = 117400.0
        entry_prices = risk_manager._calculate_scaled_entry_prices(current_price, 'short')
        
        # For short, prices should increase (selling rallies)
        assert len(entry_prices) == 4
        assert entry_prices[0] == 117400.0
        assert entry_prices[1] == pytest.approx(117987.0)  # 0.5% above
        assert entry_prices[2] == pytest.approx(118574.0)  # 1% above
        assert entry_prices[3] == pytest.approx(119161.0)  # 1.5% above
    
    def test_process_entry_signal_long_with_price_stop(self, risk_manager, entry_decision_long):
        """Test processing long entry with price-based stop loss."""
        current_price = 3001.0
        
        result = risk_manager.process_entry_signal(entry_decision_long, current_price)
        
        # Verify result structure
        assert 'group_id' in result
        assert 'limit_orders' in result
        assert result['total_orders'] == 4
        assert result['total_size'] == 1.0
        assert len(result['scaled_sizes']) == 4
        assert all(size == 0.25 for size in result['scaled_sizes'])
        
        # Verify limit orders
        orders = result['limit_orders']
        assert len(orders) == 4
        
        # Check first order
        first_order = orders[0]
        assert first_order['symbol'] == 'XAUUSD'
        assert first_order['order_type'] == 'BUY_LIMIT'
        assert first_order['volume'] == 0.25
        assert first_order['price'] == 3001.0
        assert first_order['magic'] == 12345
        assert 'group_stop_loss' in first_order
        
        # Verify stop calculation method
        assert result['stop_calculation_method'] == 'price_level'
    
    def test_process_entry_signal_short_with_monetary_stop(self, risk_manager, entry_decision_short):
        """Test processing short entry with monetary stop loss."""
        # Change to monetary type
        entry_decision_short.stop_loss.type = 'monetary'
        current_price = 117401.0
        
        result = risk_manager.process_entry_signal(entry_decision_short, current_price)
        
        # Verify result
        assert result['total_orders'] == 4
        assert result['stop_calculation_method'] == 'monetary'
        
        # Check orders are SELL_LIMIT for short
        for order in result['limit_orders']:
            assert order['order_type'] == 'SELL_LIMIT'
    
    def test_process_entry_signal_no_group_stop(self, scaling_config, entry_decision_long):
        """Test processing with individual stop losses."""
        rm = RiskManager(scaling_config, group_stop_loss=False)
        current_price = 3001.0
        
        result = rm.process_entry_signal(entry_decision_long, current_price)
        
        # Should have individual stops, no group stop
        assert result['stop_loss_mode'] == 'individual'
        assert result['group_stop_loss'] is None
        
        # Each order should have individual stop
        for order in result['limit_orders']:
            assert order['stop_loss'] == 2995.0  # Original stop level
            assert order['group_stop_loss'] is None
    
    def test_create_position_group(self, risk_manager, entry_decision_long):
        """Test position group creation."""
        group_id = "test-group-123"
        group = risk_manager._create_position_group(entry_decision_long, group_id)
        
        assert group.group_id == group_id
        assert group.symbol == 'XAUUSD'
        assert group.strategy_name == 'test-strategy'
        assert group.direction == 'long'
        assert group.original_decision == entry_decision_long
        assert group.total_target_size == 1.0
        assert group.num_entries == 4
        assert group.scaling_strategy == 'equal'
        assert group.total_risk_amount == 1000.0
    
    def test_pyramid_scaling_configuration(self, entry_decision_long):
        """Test pyramid scaling type."""
        config = ScalingConfig(
            num_entries=4,
            scaling_type="pyramid_up",
            entry_spacing=0.5,
            max_risk_per_group=1000.0
        )
        rm = RiskManager(config)
        
        result = rm.process_entry_signal(entry_decision_long, 3000.0)
        
        # Pyramid up: [0.1, 0.2, 0.3, 0.4]
        expected_sizes = [0.1, 0.2, 0.3, 0.4]
        assert result['scaled_sizes'] == expected_sizes
    
    def test_custom_scaling_ratios(self, entry_decision_long):
        """Test custom scaling ratios."""
        config = ScalingConfig(
            num_entries=3,
            scaling_type="custom",
            custom_ratios=[0.5, 0.3, 0.2],
            entry_spacing=1.0,
            max_risk_per_group=1000.0
        )
        rm = RiskManager(config)
        
        result = rm.process_entry_signal(entry_decision_long, 3000.0)
        
        assert result['scaled_sizes'] == [0.5, 0.3, 0.2]
        assert len(result['limit_orders']) == 3
    
    def test_position_tracking(self, risk_manager, entry_decision_long):
        """Test that positions are properly tracked."""
        result = risk_manager.process_entry_signal(entry_decision_long, 3000.0)
        
        group_id = result['group_id']
        
        # Check position group is stored
        assert group_id in risk_manager.position_groups
        group = risk_manager.position_groups[group_id]
        assert len(group.positions) == 4
        
        # Check ticket tracking
        for order in result['limit_orders']:
            ticket_id = order['ticket_id']
            assert ticket_id in risk_manager.active_tickets
            assert risk_manager.active_tickets[ticket_id] == group_id
    
    def test_no_stop_loss_handling(self, risk_manager):
        """Test handling of entry without stop loss."""
        entry = EntryDecision(
            symbol='XAUUSD',
            strategy_name='test',
            magic=12345,
            direction='long',
            entry_signals='BUY',
            entry_price=3000.0,
            position_size=1.0,
            stop_loss=None,  # No stop loss
            take_profit=None,
            decision_time=datetime.now()
        )
        
        result = risk_manager.process_entry_signal(entry, 3000.0)
        
        # Should still process but with monetary risk fallback
        assert result['group_stop_loss'] is not None
        assert result['stop_calculation_method'] == 'monetary'