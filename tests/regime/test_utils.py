"""Unit tests for regime detection utility functions."""

import unittest
import numpy as np
from collections import deque

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.regime.regime_detection import (
    ema_update,
    wilder_update,
    true_range,
    bb_width_from_window
)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions used in regime detection."""
    
    def test_ema_update_initial(self):
        """Test EMA update with no previous value."""
        result = ema_update(None, 100.0, 12)
        self.assertEqual(result, 100.0)
    
    def test_ema_update_with_previous(self):
        """Test EMA update with previous value."""
        # Alpha for period 12 = 2/(12+1) = 0.1538...
        alpha = 2.0 / (12 + 1.0)
        prev = 100.0
        price = 110.0
        expected = alpha * price + (1 - alpha) * prev
        result = ema_update(prev, price, 12)
        self.assertAlmostEqual(result, expected, places=10)
    
    def test_wilder_update_initial(self):
        """Test Wilder's smoothing with no previous value."""
        result = wilder_update(None, 5.0, 14)
        self.assertEqual(result, 5.0)
    
    def test_wilder_update_with_previous(self):
        """Test Wilder's smoothing with previous value."""
        prev = 10.0
        value = 12.0
        period = 14
        expected = prev + (value - prev) / period
        result = wilder_update(prev, value, period)
        self.assertAlmostEqual(result, expected, places=10)
    
    def test_true_range_no_previous(self):
        """Test true range calculation without previous close."""
        high = 110.0
        low = 100.0
        result = true_range(high, low, None)
        self.assertEqual(result, 10.0)
    
    def test_true_range_with_previous(self):
        """Test true range calculation with previous close."""
        high = 110.0
        low = 100.0
        prev_close = 95.0  # Creates gap up
        # TR = max(110-100, abs(110-95), abs(100-95)) = max(10, 15, 5) = 15
        result = true_range(high, low, prev_close)
        self.assertEqual(result, 15.0)
        
        # Test gap down
        prev_close = 115.0
        # TR = max(110-100, abs(110-115), abs(100-115)) = max(10, 5, 15) = 15
        result = true_range(high, low, prev_close)
        self.assertEqual(result, 15.0)
    
    def test_bb_width_empty_window(self):
        """Test Bollinger Band width with empty window."""
        window = deque(maxlen=20)
        result = bb_width_from_window(window)
        self.assertEqual(result, 0.0)
    
    def test_bb_width_single_value(self):
        """Test BB width with single value (no variance)."""
        window = deque([100.0], maxlen=20)
        result = bb_width_from_window(window, period=20, k=2.0)
        # With single value, std=0, so width=0
        self.assertEqual(result, 0.0)
    
    def test_bb_width_normal_case(self):
        """Test BB width with normal price data."""
        prices = [100, 102, 98, 103, 99, 101, 97, 104, 100, 102]
        window = deque(prices, maxlen=20)
        result = bb_width_from_window(window, period=10, k=2.0)
        
        # Calculate expected
        arr = np.array(prices)
        mean = arr.mean()
        std = arr.std(ddof=0)
        upper = mean + 2 * std
        lower = mean - 2 * std
        expected = (upper - lower) / mean
        
        self.assertAlmostEqual(result, expected, places=10)
    
    def test_bb_width_zero_mean(self):
        """Test BB width when mean is zero (edge case)."""
        window = deque([0.0, 0.0], maxlen=20)
        result = bb_width_from_window(window)
        self.assertEqual(result, 0.0)


class TestEMAConvergence(unittest.TestCase):
    """Test EMA convergence properties."""
    
    def test_ema_convergence(self):
        """Test that EMA converges to price after sufficient updates."""
        price = 100.0
        ema = None
        period = 12
        
        # After many updates with same price, EMA should converge
        for _ in range(100):
            ema = ema_update(ema, price, period)
        
        self.assertAlmostEqual(ema, price, places=5)
    
    def test_ema_responsiveness(self):
        """Test EMA responsiveness to price changes."""
        ema12 = 100.0
        ema26 = 100.0
        
        # Sudden price jump
        new_price = 110.0
        
        new_ema12 = ema_update(ema12, new_price, 12)
        new_ema26 = ema_update(ema26, new_price, 26)
        
        # EMA12 should respond more than EMA26
        diff_12 = new_ema12 - ema12
        diff_26 = new_ema26 - ema26
        
        self.assertGreater(diff_12, diff_26)


if __name__ == '__main__':
    unittest.main()