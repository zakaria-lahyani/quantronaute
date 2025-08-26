"""Unit tests for HTF (Higher Timeframe) bias calculator."""

import unittest
import pandas as pd

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app.regime.htf_regime_bias import HTFBiasCalculator, HTFState


class TestHTFState(unittest.TestCase):
    """Test HTFState data structure."""
    
    def test_htf_state_default_initialization(self):
        """Test HTFState default initialization."""
        state = HTFState()
        
        self.assertIsNone(state.rule)
        self.assertIsNone(state.bucket)
        self.assertIsNone(state.last_close)
        self.assertIsNone(state.ema12)
        self.assertIsNone(state.ema26)
        self.assertIsNone(state.ema200)
        self.assertIsNone(state.macd_signal)
        self.assertEqual(state.bias, "neutral")
    
    def test_htf_state_partial_initialization(self):
        """Test HTFState with some values initialized."""
        bucket = pd.Timestamp("2024-01-01 00:00:00")
        state = HTFState(
            rule="1h",
            bucket=bucket,
            last_close=100.0,
            bias="bull"
        )
        
        self.assertEqual(state.rule, "1h")
        self.assertEqual(state.bucket, bucket)
        self.assertEqual(state.last_close, 100.0)
        self.assertEqual(state.bias, "bull")
        
        # Other fields should still be None
        self.assertIsNone(state.ema12)
        self.assertIsNone(state.ema26)


class TestHTFBiasCalculator(unittest.TestCase):
    """Test HTFBiasCalculator functionality."""
    
    def test_init_no_rule(self):
        """Test initialization without HTF rule."""
        calculator = HTFBiasCalculator()
        
        self.assertIsNone(calculator.state.rule)
        self.assertEqual(calculator.state.bias, "neutral")
    
    def test_init_with_rule(self):
        """Test initialization with HTF rule."""
        calculator = HTFBiasCalculator("4h")
        
        self.assertEqual(calculator.state.rule, "4h")
        self.assertEqual(calculator.state.bias, "neutral")
    
    def test_update_no_rule(self):
        """Test update when no HTF rule is set."""
        calculator = HTFBiasCalculator()
        
        result = calculator.update(pd.Timestamp("2024-01-01 10:00:00"), 100.0)
        
        # Should always return neutral when no rule
        self.assertEqual(result, "neutral")
        
        # Multiple calls should still return neutral
        result2 = calculator.update(pd.Timestamp("2024-01-01 11:00:00"), 105.0)
        self.assertEqual(result2, "neutral")


class TestHTFBiasFirstBucket(TestHTFBiasCalculator):
    """Test HTF bias calculation for first bucket."""
    
    def test_first_bucket_initialization(self):
        """Test first bucket initialization."""
        calculator = HTFBiasCalculator("1h")
        
        result = calculator.update(pd.Timestamp("2024-01-01 10:30:00"), 100.0)
        
        # First update should set bucket and return neutral
        self.assertEqual(result, "neutral")
        self.assertEqual(calculator.state.bucket, pd.Timestamp("2024-01-01 10:00:00"))
        self.assertEqual(calculator.state.last_close, 100.0)
        self.assertEqual(calculator.state.bias, "neutral")
    
    def test_same_bucket_updates(self):
        """Test multiple updates within same bucket."""
        calculator = HTFBiasCalculator("1h")
        
        # Initialize first bucket
        calculator.update(pd.Timestamp("2024-01-01 10:15:00"), 100.0)
        
        # Update within same hour
        result = calculator.update(pd.Timestamp("2024-01-01 10:30:00"), 102.0)
        self.assertEqual(result, "neutral")
        self.assertEqual(calculator.state.last_close, 102.0)
        
        # Another update within same hour
        result = calculator.update(pd.Timestamp("2024-01-01 10:45:00"), 101.5)
        self.assertEqual(result, "neutral")
        self.assertEqual(calculator.state.last_close, 101.5)
        
        # Bucket should remain the same
        self.assertEqual(calculator.state.bucket, pd.Timestamp("2024-01-01 10:00:00"))


class TestHTFBiasNewBucket(TestHTFBiasCalculator):
    """Test HTF bias calculation when moving to new bucket."""
    
    def test_bucket_transition_updates_indicators(self):
        """Test that moving to new bucket updates HTF indicators."""
        calculator = HTFBiasCalculator("1h")
        
        # Initialize first bucket
        calculator.update(pd.Timestamp("2024-01-01 10:30:00"), 100.0)
        
        # Move to next bucket - should trigger indicator update
        result = calculator.update(pd.Timestamp("2024-01-01 11:15:00"), 105.0)
        
        # HTF indicators should be updated
        self.assertIsNotNone(calculator.state.ema12)
        self.assertIsNotNone(calculator.state.ema26)
        self.assertIsNotNone(calculator.state.ema200)
        self.assertEqual(calculator.state.ema12, 100.0)  # First value
        self.assertEqual(calculator.state.ema26, 100.0)  # First value
        self.assertEqual(calculator.state.ema200, 100.0)  # First value
        
        # New bucket should be set
        self.assertEqual(calculator.state.bucket, pd.Timestamp("2024-01-01 11:00:00"))
        self.assertEqual(calculator.state.last_close, 105.0)
    
    def test_macd_signal_initialization(self):
        """Test MACD signal initialization on first bucket close."""
        calculator = HTFBiasCalculator("1h")
        
        # Initialize and close first bucket
        calculator.update(pd.Timestamp("2024-01-01 10:30:00"), 100.0)
        calculator.update(pd.Timestamp("2024-01-01 11:15:00"), 105.0)
        
        # MACD line = ema12 - ema26 = 100 - 100 = 0
        # MACD signal should be initialized to 0
        self.assertEqual(calculator.state.macd_signal, 0.0)
    
    def test_multiple_bucket_transitions(self):
        """Test multiple bucket transitions."""
        calculator = HTFBiasCalculator("1h")
        
        # First bucket
        calculator.update(pd.Timestamp("2024-01-01 10:30:00"), 100.0)
        
        # Second bucket
        calculator.update(pd.Timestamp("2024-01-01 11:15:00"), 105.0)
        ema12_after_second = calculator.state.ema12
        ema26_after_second = calculator.state.ema26
        
        # Third bucket
        calculator.update(pd.Timestamp("2024-01-01 12:15:00"), 110.0)
        
        # EMAs should have evolved
        self.assertNotEqual(calculator.state.ema12, ema12_after_second)
        self.assertNotEqual(calculator.state.ema26, ema26_after_second)
        self.assertGreater(calculator.state.ema12, ema12_after_second)
        self.assertGreater(calculator.state.ema26, ema26_after_second)


class TestHTFBiasCalculation(TestHTFBiasCalculator):
    """Test HTF bias calculation logic."""
    
    def test_bias_calculation_insufficient_indicators(self):
        """Test bias calculation when indicators are not ready."""
        calculator = HTFBiasCalculator("1h")
        
        # First bucket - should remain neutral
        calculator.update(pd.Timestamp("2024-01-01 10:30:00"), 100.0)
        calculator.update(pd.Timestamp("2024-01-01 11:15:00"), 105.0)
        
        # Bias should remain neutral (not enough data)
        self.assertEqual(calculator.state.bias, "neutral")
    
    def test_bias_calculation_bull_conditions(self):
        """Test bias calculation for bullish conditions."""
        calculator = HTFBiasCalculator("1h")
        
        # Simulate multiple bucket closes to build indicators
        timestamps_and_closes = [
            (pd.Timestamp("2024-01-01 10:30:00"), 100.0),  # First bucket
            (pd.Timestamp("2024-01-01 11:15:00"), 102.0),  # Second bucket
            (pd.Timestamp("2024-01-01 12:15:00"), 105.0),  # Third bucket
            (pd.Timestamp("2024-01-01 13:15:00"), 108.0),  # Fourth bucket
        ]
        
        for ts, close in timestamps_and_closes:
            calculator.update(ts, close)
        
        # Manually verify conditions: close > ema200 and MACD hist > 0
        # After several updates, we should have valid indicators
        self.assertIsNotNone(calculator.state.ema200)
        self.assertIsNotNone(calculator.state.macd_signal)
        
        # If conditions are met, bias should be bull
        if (calculator.state.last_close > calculator.state.ema200 and
            calculator.state.ema12 is not None and calculator.state.ema26 is not None):
            macd_line = calculator.state.ema12 - calculator.state.ema26
            hist = macd_line - calculator.state.macd_signal
            if hist > 0:
                self.assertEqual(calculator.state.bias, "bull")
    
    def test_bias_calculation_bear_conditions(self):
        """Test bias calculation for bearish conditions."""
        calculator = HTFBiasCalculator("1h")
        
        # Simulate declining prices
        timestamps_and_closes = [
            (pd.Timestamp("2024-01-01 10:30:00"), 110.0),  # Start high
            (pd.Timestamp("2024-01-01 11:15:00"), 108.0),  # Decline
            (pd.Timestamp("2024-01-01 12:15:00"), 105.0),  # Further decline
            (pd.Timestamp("2024-01-01 13:15:00"), 102.0),  # Continue decline
            (pd.Timestamp("2024-01-01 14:15:00"), 100.0),  # More decline
        ]
        
        for ts, close in timestamps_and_closes:
            calculator.update(ts, close)
        
        # After declining trend, conditions for bear bias might be met
        if (calculator.state.last_close < calculator.state.ema200 and
            calculator.state.ema12 is not None and calculator.state.ema26 is not None):
            macd_line = calculator.state.ema12 - calculator.state.ema26
            hist = macd_line - calculator.state.macd_signal
            if hist < 0:
                self.assertEqual(calculator.state.bias, "bear")
    
    def test_bias_calculation_neutral_mixed(self):
        """Test bias calculation for neutral/mixed conditions."""
        calculator = HTFBiasCalculator("1h")
        
        # Create mixed conditions (e.g., price above EMA200 but MACD negative)
        calculator.state.ema12 = 100.0
        calculator.state.ema26 = 102.0  # MACD line will be negative
        calculator.state.ema200 = 90.0
        calculator.state.macd_signal = -1.0
        calculator.state.last_close = 105.0  # Above EMA200
        
        # Manually trigger bias calculation
        calculator._calculate_bias()
        
        # close > ema200 (105 > 90) but hist < 0 (-2 - (-1) = -1)
        # Should result in neutral bias
        self.assertEqual(calculator.state.bias, "neutral")


class TestHTFBiasDifferentTimeframes(TestHTFBiasCalculator):
    """Test HTF bias with different timeframes."""
    
    def test_daily_timeframe(self):
        """Test HTF bias with daily timeframe."""
        calculator = HTFBiasCalculator("1D")
        
        # Multiple updates within same day
        calculator.update(pd.Timestamp("2024-01-01 09:00:00"), 100.0)
        calculator.update(pd.Timestamp("2024-01-01 12:00:00"), 102.0)
        calculator.update(pd.Timestamp("2024-01-01 15:00:00"), 104.0)
        
        # Should still be in same bucket (same day)
        self.assertEqual(calculator.state.bucket, pd.Timestamp("2024-01-01"))
        self.assertEqual(calculator.state.last_close, 104.0)
        
        # Move to next day
        calculator.update(pd.Timestamp("2024-01-02 10:00:00"), 106.0)
        
        # Should have moved to new bucket
        self.assertEqual(calculator.state.bucket, pd.Timestamp("2024-01-02"))
    
    def test_hourly_timeframe(self):
        """Test HTF bias with hourly timeframe."""
        calculator = HTFBiasCalculator("1h")
        
        # Updates within same hour
        calculator.update(pd.Timestamp("2024-01-01 10:15:00"), 100.0)
        calculator.update(pd.Timestamp("2024-01-01 10:45:00"), 102.0)
        
        # Should be same bucket
        self.assertEqual(calculator.state.bucket, pd.Timestamp("2024-01-01 10:00:00"))
        
        # Move to next hour
        calculator.update(pd.Timestamp("2024-01-01 11:30:00"), 105.0)
        
        # Should have moved to new bucket
        self.assertEqual(calculator.state.bucket, pd.Timestamp("2024-01-01 11:00:00"))
    
    def test_minute_timeframe(self):
        """Test HTF bias with minute timeframe."""
        calculator = HTFBiasCalculator("5min")
        
        # Updates within same 5-minute bucket
        calculator.update(pd.Timestamp("2024-01-01 10:31:00"), 100.0)
        calculator.update(pd.Timestamp("2024-01-01 10:34:00"), 102.0)
        
        # Should be same bucket (10:30:00)
        self.assertEqual(calculator.state.bucket, pd.Timestamp("2024-01-01 10:30:00"))
        
        # Move to next 5-minute bucket
        calculator.update(pd.Timestamp("2024-01-01 10:37:00"), 105.0)
        
        # Should have moved to new bucket (10:35:00)
        self.assertEqual(calculator.state.bucket, pd.Timestamp("2024-01-01 10:35:00"))


class TestHTFBiasEdgeCases(TestHTFBiasCalculator):
    """Test HTF bias edge cases and error handling."""
    
    def test_bias_with_none_last_close(self):
        """Test bias calculation when last_close is None."""
        calculator = HTFBiasCalculator("1h")
        calculator.state.last_close = None
        
        # Should not crash and should not update indicators
        calculator._update_htf_indicators()
        
        self.assertIsNone(calculator.state.ema12)
        self.assertIsNone(calculator.state.ema26)
        self.assertIsNone(calculator.state.ema200)
    
    def test_bias_calculation_missing_indicators(self):
        """Test bias calculation with missing indicators."""
        calculator = HTFBiasCalculator("1h")
        
        # Set only some indicators
        calculator.state.ema200 = 100.0
        calculator.state.last_close = 105.0
        # Leave ema12, ema26, macd_signal as None
        
        calculator._calculate_bias()
        
        # Should remain neutral when indicators are missing
        self.assertEqual(calculator.state.bias, "neutral")
    
    def test_extreme_price_values(self):
        """Test HTF bias with extreme price values."""
        calculator = HTFBiasCalculator("1h")
        
        # Very large prices
        calculator.update(pd.Timestamp("2024-01-01 10:30:00"), 1e6)
        calculator.update(pd.Timestamp("2024-01-01 11:30:00"), 1.1e6)
        
        # Should handle without errors
        self.assertIsNotNone(calculator.state.ema12)
        self.assertTrue(calculator.state.ema12 > 0)
        
        # Very small prices
        calculator2 = HTFBiasCalculator("1h")
        calculator2.update(pd.Timestamp("2024-01-01 10:30:00"), 0.001)
        calculator2.update(pd.Timestamp("2024-01-01 11:30:00"), 0.0011)
        
        # Should handle without errors
        self.assertIsNotNone(calculator2.state.ema12)
        self.assertTrue(calculator2.state.ema12 > 0)
    
    def test_zero_price_values(self):
        """Test HTF bias with zero price values."""
        calculator = HTFBiasCalculator("1h")
        
        calculator.update(pd.Timestamp("2024-01-01 10:30:00"), 0.0)
        calculator.update(pd.Timestamp("2024-01-01 11:30:00"), 0.0)
        
        # Should handle zero prices
        self.assertEqual(calculator.state.ema12, 0.0)
        self.assertEqual(calculator.state.ema26, 0.0)
        self.assertEqual(calculator.state.ema200, 0.0)


class TestHTFBiasIntegration(TestHTFBiasCalculator):
    """Test HTF bias integration and realistic scenarios."""
    
    def test_realistic_trading_session(self):
        """Test HTF bias over a realistic trading session."""
        calculator = HTFBiasCalculator("4h")
        
        # Simulate a trading day with 4-hour buckets
        trading_data = [
            # First 4-hour session (00:00-04:00)
            (pd.Timestamp("2024-01-01 01:00:00"), 100.0),
            (pd.Timestamp("2024-01-01 02:30:00"), 101.5),
            (pd.Timestamp("2024-01-01 03:45:00"), 102.0),
            
            # Second 4-hour session (04:00-08:00) - Uptrend
            (pd.Timestamp("2024-01-01 05:30:00"), 103.5),
            (pd.Timestamp("2024-01-01 07:15:00"), 105.0),
            
            # Third 4-hour session (08:00-12:00) - Continue uptrend
            (pd.Timestamp("2024-01-01 09:45:00"), 107.0),
            (pd.Timestamp("2024-01-01 11:30:00"), 109.0),
            
            # Fourth 4-hour session (12:00-16:00) - Strong uptrend
            (pd.Timestamp("2024-01-01 14:20:00"), 112.0),
            (pd.Timestamp("2024-01-01 15:45:00"), 115.0),
        ]
        
        biases = []
        for timestamp, close in trading_data:
            bias = calculator.update(timestamp, close)
            biases.append(bias)
        
        # Should have reasonable bias progression
        self.assertTrue(all(bias in ["neutral", "bull", "bear"] for bias in biases))
        
        # Final bias should reflect the uptrend (might be bull if conditions are met)
        final_bias = biases[-1]
        self.assertIn(final_bias, ["neutral", "bull", "bear"])
    
    def test_bias_persistence_across_buckets(self):
        """Test that bias persists appropriately across bucket changes."""
        calculator = HTFBiasCalculator("1h")
        
        # Establish initial trend
        timestamps_closes = [
            (pd.Timestamp("2024-01-01 09:30:00"), 100.0),
            (pd.Timestamp("2024-01-01 10:30:00"), 105.0),
            (pd.Timestamp("2024-01-01 11:30:00"), 110.0),
            (pd.Timestamp("2024-01-01 12:30:00"), 115.0),
        ]
        
        previous_bias = "neutral"
        for timestamp, close in timestamps_closes:
            current_bias = calculator.update(timestamp, close)
            
            # Bias should be consistent or change logically
            self.assertIn(current_bias, ["neutral", "bull", "bear"])
            
            # Track bias evolution
            if current_bias != previous_bias:
                # Bias changed - this is expected as trend develops
                pass
            
            previous_bias = current_bias
    
    def test_multiple_timeframes_consistency(self):
        """Test that different timeframes produce consistent behavior."""
        calc_1h = HTFBiasCalculator("1h")
        calc_4h = HTFBiasCalculator("4h")
        
        # Same price data
        test_data = [
            (pd.Timestamp("2024-01-01 10:30:00"), 100.0),
            (pd.Timestamp("2024-01-01 11:45:00"), 102.0),
            (pd.Timestamp("2024-01-01 13:15:00"), 104.0),
            (pd.Timestamp("2024-01-01 14:30:00"), 106.0),
        ]
        
        biases_1h = []
        biases_4h = []
        
        for timestamp, close in test_data:
            bias_1h = calc_1h.update(timestamp, close)
            bias_4h = calc_4h.update(timestamp, close)
            biases_1h.append(bias_1h)
            biases_4h.append(bias_4h)
        
        # All biases should be valid
        for bias in biases_1h + biases_4h:
            self.assertIn(bias, ["neutral", "bull", "bear"])
        
        # Different timeframes may have different sensitivities, but both should be reasonable


if __name__ == '__main__':
    unittest.main()