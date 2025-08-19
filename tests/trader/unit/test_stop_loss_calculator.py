"""
Unit tests for MonetaryStopLossCalculator.
"""

import pytest
from app.trader.risk_manager.stop_loss_calculator import MonetaryStopLossCalculator, PositionEntry


class TestMonetaryStopLossCalculator:
    """Test suite for MonetaryStopLossCalculator."""
    
    def test_initialization(self):
        """Test calculator initialization with different symbols."""
        calc_gold = MonetaryStopLossCalculator('XAUUSD')
        assert calc_gold.symbol == 'XAUUSD'
        assert calc_gold.get_point_value() == 100.0
        
        calc_btc = MonetaryStopLossCalculator('BTCUSD')
        assert calc_btc.symbol == 'BTCUSD'
        assert calc_btc.get_point_value() == 1.0
        
        calc_unknown = MonetaryStopLossCalculator('UNKNOWN')
        assert calc_unknown.get_point_value() == 1.0  # Default value
    
    def test_calculate_group_stop_loss_long(self):
        """Test stop loss calculation for long positions with monetary risk."""
        calculator = MonetaryStopLossCalculator('XAUUSD')
        
        # Two equal positions
        entries = [
            PositionEntry(entry_price=3000.0, position_size=0.5),
            PositionEntry(entry_price=2995.0, position_size=0.5)
        ]
        
        stop_loss, details = calculator.calculate_group_stop_loss(
            entries=entries,
            target_risk=500.0,
            direction='long'
        )
        
        # Average entry is 2997.5, for $500 risk with 1 lot total:
        # Points = 500 / (1 * 100) = 5
        # Stop = 2997.5 - 5 = 2992.5
        assert stop_loss == pytest.approx(2992.5, rel=1e-6)
        assert details['weighted_avg_price'] == pytest.approx(2997.5)
        assert details['calculated_total_risk'] == pytest.approx(500.0, rel=1e-6)
        assert details['total_size'] == 1.0
    
    def test_calculate_group_stop_loss_short(self):
        """Test stop loss calculation for short positions with monetary risk."""
        calculator = MonetaryStopLossCalculator('BTCUSD')
        
        entries = [
            PositionEntry(entry_price=117400.0, position_size=0.25),
            PositionEntry(entry_price=117600.0, position_size=0.25),
            PositionEntry(entry_price=117800.0, position_size=0.25),
            PositionEntry(entry_price=118000.0, position_size=0.25)
        ]
        
        stop_loss, details = calculator.calculate_group_stop_loss(
            entries=entries,
            target_risk=1000.0,
            direction='short'
        )
        
        # Average entry is 117700, for $1000 risk with 1 lot total:
        # Points = 1000 / (1 * 1) = 1000
        # Stop = 117700 + 1000 = 118700 (above for short)
        assert stop_loss == pytest.approx(118700.0)
        assert details['weighted_avg_price'] == pytest.approx(117700.0)
        assert details['calculated_total_risk'] == pytest.approx(1000.0, rel=1e-6)
    
    def test_calculate_group_stop_loss_pyramid_scaling(self):
        """Test with pyramid scaling (unequal position sizes)."""
        calculator = MonetaryStopLossCalculator('XAUUSD')
        
        # Pyramid: smaller first, larger later
        entries = [
            PositionEntry(entry_price=3000.0, position_size=0.1),
            PositionEntry(entry_price=2997.0, position_size=0.2),
            PositionEntry(entry_price=2994.0, position_size=0.3),
            PositionEntry(entry_price=2991.0, position_size=0.4)
        ]
        
        stop_loss, details = calculator.calculate_group_stop_loss(
            entries=entries,
            target_risk=500.0,
            direction='long'
        )
        
        # Calculate weighted average: (3000*0.1 + 2997*0.2 + 2994*0.3 + 2991*0.4) / 1.0
        weighted_avg = (300 + 599.4 + 898.2 + 1196.4) / 1.0
        assert details['weighted_avg_price'] == pytest.approx(weighted_avg, rel=1e-6)
        assert details['total_size'] == 1.0
        assert details['calculated_total_risk'] == pytest.approx(500.0, rel=1e-6)
    
    def test_calculate_group_stop_loss_from_price_level_long(self):
        """Test stop loss calculation from price levels for long position."""
        calculator = MonetaryStopLossCalculator('XAUUSD')
        
        # Original: 1 lot at 3000 with stop at 2995 = $500 risk
        entries = [
            PositionEntry(entry_price=3000.0, position_size=0.5),
            PositionEntry(entry_price=2995.0, position_size=0.5)
        ]
        
        stop_loss, details = calculator.calculate_group_stop_loss_from_price_level(
            entries=entries,
            original_entry_price=3000.0,
            original_stop_price=2995.0,
            original_position_size=1.0,
            direction='long'
        )
        
        # Should maintain same $500 risk
        # Average entry: 2997.5, stop should be at 2992.5
        assert stop_loss == pytest.approx(2992.5, rel=1e-6)
        assert details['calculated_total_risk'] == pytest.approx(500.0, rel=1e-6)
    
    def test_calculate_group_stop_loss_from_price_level_short_below(self):
        """Test stop loss calculation from price levels for short with stop below."""
        calculator = MonetaryStopLossCalculator('BTCUSD')
        
        entries = [
            PositionEntry(entry_price=117400.0, position_size=0.5),
            PositionEntry(entry_price=117600.0, position_size=0.5)
        ]
        
        # Short with stop below (unusual but supported)
        stop_loss, details = calculator.calculate_group_stop_loss_from_price_level(
            entries=entries,
            original_entry_price=117400.0,
            original_stop_price=116900.0,  # 500 points below
            original_position_size=1.0,
            direction='short'
        )
        
        # Average entry: 117500
        # Original risk: 500 points * 1 lot * $1 = $500
        # With stop below, it should be 117500 - 500 = 117000
        assert stop_loss == pytest.approx(117000.0, rel=1e-6)
        assert details['stop_side'] == 'below'
    
    def test_calculate_risk_for_stop(self):
        """Test risk calculation for a given stop loss level."""
        calculator = MonetaryStopLossCalculator('XAUUSD')
        
        entries = [
            PositionEntry(entry_price=3000.0, position_size=0.5),
            PositionEntry(entry_price=2995.0, position_size=0.5)
        ]
        
        risk_details = calculator.calculate_risk_for_stop(
            entries=entries,
            stop_loss=2990.0,
            direction='long'
        )
        
        # Position 1: (3000 - 2990) * 0.5 * 100 = $500
        # Position 2: (2995 - 2990) * 0.5 * 100 = $250
        # Total: $750
        assert risk_details['total_risk'] == pytest.approx(750.0)
        assert len(risk_details['individual_risks']) == 2
        assert risk_details['individual_risks'][0]['risk'] == pytest.approx(500.0)
        assert risk_details['individual_risks'][1]['risk'] == pytest.approx(250.0)
    
    def test_empty_entries_raises_error(self):
        """Test that empty entries list raises an error."""
        calculator = MonetaryStopLossCalculator('XAUUSD')
        
        with pytest.raises(ValueError, match="No entries provided"):
            calculator.calculate_group_stop_loss(
                entries=[],
                target_risk=500.0,
                direction='long'
            )
    
    def test_zero_position_size_raises_error(self):
        """Test that zero total position size raises an error."""
        calculator = MonetaryStopLossCalculator('XAUUSD')
        
        entries = [
            PositionEntry(entry_price=3000.0, position_size=0.0),
            PositionEntry(entry_price=2995.0, position_size=0.0)
        ]
        
        with pytest.raises(ValueError, match="Total position size is zero"):
            calculator.calculate_group_stop_loss(
                entries=entries,
                target_risk=500.0,
                direction='long'
            )
    
    def test_calculate_group_stop_loss_with_side(self):
        """Test stop loss calculation with explicit side control."""
        calculator = MonetaryStopLossCalculator('XAUUSD')
        
        entries = [
            PositionEntry(entry_price=3000.0, position_size=0.5),
            PositionEntry(entry_price=2995.0, position_size=0.5)
        ]
        
        # Force stop below (normal for long)
        stop_below, details_below = calculator.calculate_group_stop_loss_with_side(
            entries=entries,
            target_risk=500.0,
            direction='long',
            stop_below_entry=True
        )
        
        assert stop_below == pytest.approx(2992.5)
        assert details_below['stop_side'] == 'below'
        
        # Force stop above (unusual for long)
        stop_above, details_above = calculator.calculate_group_stop_loss_with_side(
            entries=entries,
            target_risk=500.0,
            direction='long',
            stop_below_entry=False
        )
        
        assert stop_above == pytest.approx(3002.5)
        assert details_above['stop_side'] == 'above'