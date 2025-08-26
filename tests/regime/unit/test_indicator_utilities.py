"""Unit tests for regime indicator utility functions."""

import unittest
import numpy as np
from collections import deque

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app.regime.indicator_utilities import (
    ema_update, wilder_update, true_range, bb_width_normalized, safe_clip
)


class TestEMAUpdate(unittest.TestCase):
    """Test EMA update function."""
    
    def test_initial_ema_update(self):
        """Test EMA update with no previous value."""
        result = ema_update(None, 100.0, 12)
        self.assertEqual(result, 100.0)
    
    def test_ema_update_with_previous(self):
        """Test EMA update with previous value."""
        # EMA(12) alpha = 2/13 = 0.153846...
        prev_ema = 100.0
        new_price = 105.0
        period = 12
        
        result = ema_update(prev_ema, new_price, period)
        
        # Manual calculation: alpha * new_price + (1-alpha) * prev_ema
        alpha = 2.0 / (period + 1.0)
        expected = alpha * new_price + (1 - alpha) * prev_ema
        
        self.assertAlmostEqual(result, expected, places=10)
        
        # For EMA(12): alpha = 2/13 ≈ 0.1538
        # result ≈ 0.1538 * 105 + 0.8462 * 100 ≈ 16.15 + 84.62 ≈ 100.77
        self.assertAlmostEqual(result, 100.769, places=2)
    
    def test_ema_update_different_periods(self):
        """Test EMA update with different periods."""
        prev_ema = 100.0
        new_price = 110.0
        
        # Short period (more responsive)
        result_short = ema_update(prev_ema, new_price, 5)
        # Long period (less responsive)
        result_long = ema_update(prev_ema, new_price, 50)
        
        # Short period should be more responsive to new price
        self.assertGreater(result_short, result_long)
        self.assertGreater(result_short, prev_ema)
        self.assertGreater(result_long, prev_ema)
    
    def test_ema_update_extreme_values(self):
        """Test EMA update with extreme values."""
        # Very large values
        result_large = ema_update(1e6, 1.1e6, 20)
        self.assertIsNotNone(result_large)
        self.assertTrue(np.isfinite(result_large))
        
        # Very small values
        result_small = ema_update(1e-6, 1.1e-6, 20)
        self.assertIsNotNone(result_small)
        self.assertTrue(np.isfinite(result_small))
        
        # Zero values
        result_zero = ema_update(0.0, 0.0, 20)
        self.assertEqual(result_zero, 0.0)
    
    def test_ema_convergence_property(self):
        """Test that EMA converges to constant input."""
        # If we feed constant price, EMA should converge to that price
        price = 150.0
        period = 10
        ema = None
        
        # Run many iterations
        for _ in range(100):  # Enough iterations for convergence
            ema = ema_update(ema, price, period)
        
        # Should converge very close to the input price
        self.assertAlmostEqual(ema, price, places=6)


class TestWilderUpdate(unittest.TestCase):
    """Test Wilder smoothing update function."""
    
    def test_initial_wilder_update(self):
        """Test Wilder update with no previous value."""
        result = wilder_update(None, 5.0, 14)
        self.assertEqual(result, 5.0)
    
    def test_wilder_update_with_previous(self):
        """Test Wilder update with previous value."""
        prev_value = 10.0
        new_value = 15.0
        period = 14
        
        result = wilder_update(prev_value, new_value, period)
        
        # Manual calculation: prev + (new - prev) / period
        expected = prev_value + (new_value - prev_value) / period
        
        self.assertAlmostEqual(result, expected, places=10)
        
        # 10 + (15 - 10) / 14 = 10 + 5/14 ≈ 10.357
        self.assertAlmostEqual(result, 10.357, places=3)
    
    def test_wilder_vs_ema_behavior(self):
        """Test that Wilder smoothing behaves differently from EMA."""
        prev = 100.0
        new_val = 110.0
        period = 14
        
        wilder_result = wilder_update(prev, new_val, period)
        ema_result = ema_update(prev, new_val, period)
        
        # Both should be between prev and new_val, but different values
        self.assertGreater(wilder_result, prev)
        self.assertLess(wilder_result, new_val)
        self.assertGreater(ema_result, prev)
        self.assertLess(ema_result, new_val)
        self.assertNotEqual(wilder_result, ema_result)
    
    def test_wilder_update_zero_period(self):
        """Test Wilder update behavior with different periods."""
        prev = 50.0
        new_val = 60.0
        
        # Period 1 should return new value
        result_1 = wilder_update(prev, new_val, 1)
        self.assertEqual(result_1, new_val)
        
        # Larger periods should be less responsive
        result_10 = wilder_update(prev, new_val, 10)
        result_50 = wilder_update(prev, new_val, 50)
        
        self.assertGreater(result_10, result_50)
    
    def test_wilder_convergence(self):
        """Test Wilder smoothing convergence."""
        value = 75.0
        period = 14
        result = None
        
        # Run many iterations
        for _ in range(200):
            result = wilder_update(result, value, period)
        
        # Should converge to the input value
        self.assertAlmostEqual(result, value, places=6)


class TestTrueRange(unittest.TestCase):
    """Test True Range calculation function."""
    
    def test_true_range_no_previous_close(self):
        """Test True Range when previous close is None."""
        high = 105.0
        low = 98.0
        prev_close = None
        
        result = true_range(high, low, prev_close)
        
        # Should be high - low
        self.assertEqual(result, high - low)
        self.assertEqual(result, 7.0)
    
    def test_true_range_with_previous_close(self):
        """Test True Range with previous close."""
        high = 105.0
        low = 98.0
        prev_close = 102.0
        
        result = true_range(high, low, prev_close)
        
        # Should be max of: high-low, |high-prev_close|, |low-prev_close|
        # max(7.0, 3.0, 4.0) = 7.0
        expected = max(high - low, abs(high - prev_close), abs(low - prev_close))
        self.assertEqual(result, expected)
        self.assertEqual(result, 7.0)
    
    def test_true_range_gap_up(self):
        """Test True Range with gap up scenario."""
        high = 115.0
        low = 110.0  # Gap up from previous close
        prev_close = 105.0
        
        result = true_range(high, low, prev_close)
        
        # max(5.0, 10.0, 5.0) = 10.0 (high - prev_close)
        self.assertEqual(result, 10.0)
    
    def test_true_range_gap_down(self):
        """Test True Range with gap down scenario."""
        high = 95.0  # Gap down from previous close
        low = 90.0
        prev_close = 105.0
        
        result = true_range(high, low, prev_close)
        
        # max(5.0, 10.0, 15.0) = 15.0 (prev_close - low)
        self.assertEqual(result, 15.0)
    
    def test_true_range_inside_day(self):
        """Test True Range for inside day (within previous close range)."""
        high = 102.0
        low = 98.0
        prev_close = 100.0
        
        result = true_range(high, low, prev_close)
        
        # max(4.0, 2.0, 2.0) = 4.0 (high - low)
        self.assertEqual(result, 4.0)
    
    def test_true_range_zero_range(self):
        """Test True Range with zero high-low range."""
        high = 100.0
        low = 100.0
        prev_close = 98.0
        
        result = true_range(high, low, prev_close)
        
        # max(0.0, 2.0, 2.0) = 2.0
        self.assertEqual(result, 2.0)
    
    def test_true_range_negative_values(self):
        """Test True Range with negative price values."""
        high = -10.0
        low = -15.0
        prev_close = -12.0
        
        result = true_range(high, low, prev_close)
        
        # max(5.0, 2.0, 3.0) = 5.0
        self.assertEqual(result, 5.0)


class TestBBWidthNormalized(unittest.TestCase):
    """Test Bollinger Band width normalized calculation."""
    
    def test_bb_width_empty_window(self):
        """Test BB width with empty price window."""
        prices = deque()
        result = bb_width_normalized(prices)
        self.assertEqual(result, 0.0)
    
    def test_bb_width_single_price(self):
        """Test BB width with single price (zero std)."""
        prices = deque([100.0])
        result = bb_width_normalized(prices, period=20, k=2.0)
        
        # Standard deviation is 0, so width should be 0
        self.assertEqual(result, 0.0)
    
    def test_bb_width_constant_prices(self):
        """Test BB width with constant prices."""
        prices = deque([100.0] * 10)
        result = bb_width_normalized(prices, period=20, k=2.0)
        
        # Standard deviation is 0, so width should be 0
        self.assertEqual(result, 0.0)
    
    def test_bb_width_normal_case(self):
        """Test BB width with normal price variation."""
        # Create prices with known std
        prices = deque([95.0, 100.0, 105.0, 100.0, 98.0])
        result = bb_width_normalized(prices, period=5, k=2.0)
        
        # Manual calculation
        mean = 99.6
        std = np.std([95.0, 100.0, 105.0, 100.0, 98.0], ddof=0)
        upper = mean + 2.0 * std
        lower = mean - 2.0 * std
        expected_width = (upper - lower) / mean
        
        self.assertAlmostEqual(result, expected_width, places=10)
        self.assertGreater(result, 0)
    
    def test_bb_width_different_k_values(self):
        """Test BB width with different k (standard deviation multiplier) values."""
        prices = deque([90.0, 95.0, 100.0, 105.0, 110.0])
        
        result_k1 = bb_width_normalized(prices, period=5, k=1.0)
        result_k2 = bb_width_normalized(prices, period=5, k=2.0)
        result_k3 = bb_width_normalized(prices, period=5, k=3.0)
        
        # Larger k should give larger width
        self.assertGreater(result_k2, result_k1)
        self.assertGreater(result_k3, result_k2)
    
    def test_bb_width_period_limiting(self):
        """Test that period is properly limited by window size."""
        prices = deque([100.0, 101.0, 99.0])  # Only 3 prices
        
        result = bb_width_normalized(prices, period=20, k=2.0)  # Period > window size
        
        # Should use only the 3 available prices
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result, 0.0)
    
    def test_bb_width_zero_mean(self):
        """Test BB width when mean is zero."""
        prices = deque([-1.0, 0.0, 1.0])
        result = bb_width_normalized(prices, period=3, k=2.0)
        
        # Mean is 0, so normalized width should be 0 (division by zero protection)
        self.assertEqual(result, 0.0)
    
    def test_bb_width_high_volatility(self):
        """Test BB width with high volatility prices."""
        # High volatility scenario
        high_vol_prices = deque([50.0, 100.0, 150.0, 75.0, 125.0])
        high_vol_result = bb_width_normalized(high_vol_prices, period=5, k=2.0)
        
        # Low volatility scenario
        low_vol_prices = deque([98.0, 100.0, 102.0, 99.0, 101.0])
        low_vol_result = bb_width_normalized(low_vol_prices, period=5, k=2.0)
        
        # High volatility should give wider bands
        self.assertGreater(high_vol_result, low_vol_result)


class TestSafeClip(unittest.TestCase):
    """Test safe clipping function."""
    
    def test_value_within_range(self):
        """Test clipping value within range."""
        result = safe_clip(1.5, 0.5, 3.0)
        self.assertEqual(result, 1.5)
        self.assertIsInstance(result, float)
    
    def test_value_below_min(self):
        """Test clipping value below minimum."""
        result = safe_clip(0.2, 0.5, 3.0)
        self.assertEqual(result, 0.5)
    
    def test_value_above_max(self):
        """Test clipping value above maximum."""
        result = safe_clip(5.0, 0.5, 3.0)
        self.assertEqual(result, 3.0)
    
    def test_value_equals_bounds(self):
        """Test clipping with values equal to bounds."""
        # Equal to min
        result_min = safe_clip(0.5, 0.5, 3.0)
        self.assertEqual(result_min, 0.5)
        
        # Equal to max
        result_max = safe_clip(3.0, 0.5, 3.0)
        self.assertEqual(result_max, 3.0)
    
    def test_negative_values(self):
        """Test clipping with negative values."""
        result = safe_clip(-5.0, -10.0, -1.0)
        self.assertEqual(result, -5.0)
        
        result_clipped = safe_clip(-15.0, -10.0, -1.0)
        self.assertEqual(result_clipped, -10.0)
    
    def test_numpy_input(self):
        """Test clipping with numpy inputs."""
        result = safe_clip(np.float64(2.5), np.float32(1.0), np.int64(4))
        self.assertEqual(result, 2.5)
        self.assertIsInstance(result, float)
    
    def test_inf_and_nan_handling(self):
        """Test clipping with infinity and NaN values."""
        # Positive infinity
        result_pos_inf = safe_clip(np.inf, 0.5, 3.0)
        self.assertEqual(result_pos_inf, 3.0)
        
        # Negative infinity
        result_neg_inf = safe_clip(-np.inf, 0.5, 3.0)
        self.assertEqual(result_neg_inf, 0.5)
        
        # NaN should remain NaN (numpy.clip behavior)
        result_nan = safe_clip(np.nan, 0.5, 3.0)
        self.assertTrue(np.isnan(result_nan))
    
    def test_type_preservation(self):
        """Test that result is always float type."""
        # Integer input
        result_int = safe_clip(2, 1, 3)
        self.assertIsInstance(result_int, float)
        self.assertEqual(result_int, 2.0)
        
        # Numpy types
        result_np = safe_clip(np.int32(2), np.float32(1.0), np.int64(3))
        self.assertIsInstance(result_np, float)


class TestUtilityFunctionIntegration(unittest.TestCase):
    """Test integration between utility functions."""
    
    def test_ema_wilder_relationship(self):
        """Test relationship between EMA and Wilder smoothing."""
        prev = 100.0
        new_val = 110.0
        period = 14
        
        ema_result = ema_update(prev, new_val, period)
        wilder_result = wilder_update(prev, new_val, period)
        
        # Both should move towards new value, but at different rates
        self.assertGreater(ema_result, prev)
        self.assertGreater(wilder_result, prev)
        self.assertLess(ema_result, new_val)
        self.assertLess(wilder_result, new_val)
    
    def test_true_range_bb_width_scenarios(self):
        """Test True Range and BB width in various market scenarios."""
        # Trending market
        trending_prices = deque([100.0, 102.0, 104.0, 106.0, 108.0])
        trending_bb_width = bb_width_normalized(trending_prices, 5, 2.0)
        
        # Ranging market
        ranging_prices = deque([100.0, 102.0, 100.0, 102.0, 100.0])
        ranging_bb_width = bb_width_normalized(ranging_prices, 5, 2.0)
        
        # Both should be positive
        self.assertGreater(trending_bb_width, 0)
        self.assertGreater(ranging_bb_width, 0)
        
        # Compare True Ranges
        trending_tr = true_range(108.5, 107.5, 108.0)
        ranging_tr = true_range(102.5, 99.5, 100.0)
        
        self.assertGreater(trending_tr, 0)
        self.assertGreater(ranging_tr, 0)
    
    def test_function_purity(self):
        """Test that utility functions are pure (no side effects)."""
        # Prepare inputs
        initial_deque = deque([100.0, 101.0, 99.0])
        original_deque_contents = list(initial_deque)
        
        # Call functions
        ema_result1 = ema_update(100.0, 105.0, 12)
        ema_result2 = ema_update(100.0, 105.0, 12)
        
        wilder_result1 = wilder_update(10.0, 15.0, 14)
        wilder_result2 = wilder_update(10.0, 15.0, 14)
        
        bb_width1 = bb_width_normalized(initial_deque, 3, 2.0)
        bb_width2 = bb_width_normalized(initial_deque, 3, 2.0)
        
        # Results should be identical (deterministic)
        self.assertEqual(ema_result1, ema_result2)
        self.assertEqual(wilder_result1, wilder_result2)
        self.assertEqual(bb_width1, bb_width2)
        
        # Input deque should be unchanged (though bb_width_normalized doesn't modify it)
        self.assertEqual(list(initial_deque), original_deque_contents)


if __name__ == '__main__':
    unittest.main()