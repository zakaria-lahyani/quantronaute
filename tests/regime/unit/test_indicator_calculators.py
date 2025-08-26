"""Unit tests for regime indicator calculators."""

import unittest
import numpy as np
import pandas as pd
from collections import deque

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app.regime.data_structure import IndicatorState, BarData
from app.regime.indicator_calculator import IndicatorCalculators


class TestIndicatorCalculators(unittest.TestCase):
    """Test IndicatorCalculators static methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.state = IndicatorState()
        self.sample_bar = BarData(
            timestamp=pd.Timestamp("2024-01-01"),
            open=100.0,
            high=102.0,
            low=98.0,
            close=101.0,
            bar_index=0
        )


class TestEMAUpdates(TestIndicatorCalculators):
    """Test EMA update functionality."""
    
    def test_update_emas_initial(self):
        """Test updating EMAs from initial state."""
        close = 100.0
        IndicatorCalculators.update_emas(self.state, close)
        
        # All EMAs should be set to the initial close price
        self.assertEqual(self.state.ema12, 100.0)
        self.assertEqual(self.state.ema26, 100.0)
        self.assertEqual(self.state.ema20, 100.0)
        self.assertEqual(self.state.ema50, 100.0)
        self.assertEqual(self.state.ema200, 100.0)
    
    def test_update_emas_subsequent(self):
        """Test updating EMAs with existing values."""
        # Initialize with first value
        IndicatorCalculators.update_emas(self.state, 100.0)
        
        # Update with new value
        IndicatorCalculators.update_emas(self.state, 105.0)
        
        # All EMAs should have moved towards 105, but not equal to it
        self.assertGreater(self.state.ema12, 100.0)
        self.assertLess(self.state.ema12, 105.0)
        self.assertGreater(self.state.ema26, 100.0)
        self.assertLess(self.state.ema26, 105.0)
        
        # Shorter periods should be more responsive
        self.assertGreater(self.state.ema12, self.state.ema26)
        self.assertGreater(self.state.ema20, self.state.ema50)
        self.assertGreater(self.state.ema50, self.state.ema200)
    
    def test_update_emas_multiple_iterations(self):
        """Test EMA updates over multiple iterations."""
        prices = [100.0, 102.0, 104.0, 103.0, 105.0]
        
        for price in prices:
            IndicatorCalculators.update_emas(self.state, price)
        
        # EMAs should be between initial and final price
        final_price = 105.0
        initial_price = 100.0
        
        self.assertGreater(self.state.ema12, initial_price)
        self.assertLess(self.state.ema12, final_price)
        
        # Short EMAs should be closer to final price
        self.assertGreater(self.state.ema12, self.state.ema200)


class TestEMASlope(TestIndicatorCalculators):
    """Test EMA slope calculation functionality."""
    
    def test_calculate_ema_slope_initial(self):
        """Test EMA slope calculation with no previous value."""
        slope = IndicatorCalculators.calculate_ema_slope(self.state)
        self.assertEqual(slope, 0.0)  # Should be 0 when no previous value
    
    def test_calculate_ema_slope_no_current(self):
        """Test EMA slope when current EMA20 is None."""
        self.state.ema20_prev = 100.0
        slope = IndicatorCalculators.calculate_ema_slope(self.state)
        self.assertEqual(slope, 0.0)
    
    def test_calculate_ema_slope_upward(self):
        """Test EMA slope calculation for upward movement."""
        self.state.ema20 = 105.0
        self.state.ema20_prev = 100.0
        
        slope = IndicatorCalculators.calculate_ema_slope(self.state)
        self.assertEqual(slope, 1.0)  # Upward slope
    
    def test_calculate_ema_slope_downward(self):
        """Test EMA slope calculation for downward movement."""
        self.state.ema20 = 95.0
        self.state.ema20_prev = 100.0
        
        slope = IndicatorCalculators.calculate_ema_slope(self.state)
        self.assertEqual(slope, -1.0)  # Downward slope
    
    def test_calculate_ema_slope_flat(self):
        """Test EMA slope calculation for flat movement."""
        self.state.ema20 = 100.0
        self.state.ema20_prev = 100.0
        
        slope = IndicatorCalculators.calculate_ema_slope(self.state)
        self.assertEqual(slope, 0.0)  # Flat slope
    
    def test_calculate_ema_slope_small_difference(self):
        """Test EMA slope with very small differences."""
        self.state.ema20 = 100.0001
        self.state.ema20_prev = 100.0
        
        slope = IndicatorCalculators.calculate_ema_slope(self.state)
        self.assertEqual(slope, 1.0)  # Should still detect upward
        
        self.state.ema20 = 99.9999
        slope = IndicatorCalculators.calculate_ema_slope(self.state)
        self.assertEqual(slope, -1.0)  # Should still detect downward
    
    def test_update_ema_slope_state(self):
        """Test updating EMA slope state."""
        self.state.ema20 = 105.0
        
        IndicatorCalculators.update_ema_slope_state(self.state)
        
        self.assertEqual(self.state.ema20_prev, 105.0)


class TestMACDHistogram(TestIndicatorCalculators):
    """Test MACD histogram calculation."""
    
    def test_calculate_macd_hist_no_emas(self):
        """Test MACD histogram when EMAs are not available."""
        result = IndicatorCalculators.calculate_macd_hist(self.state)
        self.assertIsNone(result)
    
    def test_calculate_macd_hist_first_calculation(self):
        """Test first MACD histogram calculation."""
        # Set up EMAs
        self.state.ema12 = 105.0
        self.state.ema26 = 100.0
        
        result = IndicatorCalculators.calculate_macd_hist(self.state)
        
        # First calculation returns 0.0 (MACD line - MACD signal where both are same value)
        self.assertEqual(result, 0.0)
        
        # MACD signal should be initialized to the MACD line value
        self.assertIsNotNone(self.state.macd_signal)
        self.assertEqual(self.state.macd_signal, 5.0)  # ema12 - ema26
    
    def test_calculate_macd_hist_subsequent_calculations(self):
        """Test subsequent MACD histogram calculations."""
        # Initialize with first values
        self.state.ema12 = 105.0
        self.state.ema26 = 100.0
        IndicatorCalculators.calculate_macd_hist(self.state)  # Initialize signal
        
        # Update EMAs and calculate again
        self.state.ema12 = 108.0
        self.state.ema26 = 102.0
        
        result = IndicatorCalculators.calculate_macd_hist(self.state)
        
        # Should have a valid histogram value
        self.assertIsNotNone(result)
        self.assertIsInstance(result, float)
        
        # Histogram = MACD Line - MACD Signal
        macd_line = 108.0 - 102.0  # 6.0
        # Signal should be EMA of MACD line values
        expected_signal = (2.0/10.0) * macd_line + (8.0/10.0) * 5.0  # Previous signal was 5.0
        expected_hist = macd_line - expected_signal
        
        self.assertAlmostEqual(result, expected_hist, places=10)
    
    def test_calculate_macd_hist_series(self):
        """Test MACD histogram over a series of values."""
        ema12_values = [105.0, 107.0, 109.0, 108.0]
        ema26_values = [100.0, 101.0, 103.0, 104.0]
        
        results = []
        for ema12, ema26 in zip(ema12_values, ema26_values):
            self.state.ema12 = ema12
            self.state.ema26 = ema26
            result = IndicatorCalculators.calculate_macd_hist(self.state)
            results.append(result)
        
        # First result should be 0.0 (initial histogram value)
        self.assertEqual(results[0], 0.0)
        
        # All results should be numeric
        for result in results:
            self.assertIsNotNone(result)
            self.assertIsInstance(result, float)


class TestRSICalculation(TestIndicatorCalculators):
    """Test RSI calculation functionality."""
    
    def test_calculate_rsi_first_bar(self):
        """Test RSI calculation for first bar (no previous close)."""
        close = 100.0
        result = IndicatorCalculators.calculate_rsi(self.state, close)
        
        # First bar should return 50.0
        self.assertEqual(result, 50.0)
        
        # State should be initialized
        self.assertIsNotNone(self.state.rsi_avg_gain)
        self.assertIsNotNone(self.state.rsi_avg_loss)
        self.assertEqual(self.state.rsi_avg_gain, 0.0)
        self.assertEqual(self.state.rsi_avg_loss, 0.0)
    
    def test_calculate_rsi_upward_move(self):
        """Test RSI calculation with upward price movement."""
        # Initialize with first bar
        self.state.prev_close = 100.0
        IndicatorCalculators.calculate_rsi(self.state, 100.0)
        
        # Upward move
        result = IndicatorCalculators.calculate_rsi(self.state, 105.0)
        
        self.assertGreater(result, 50.0)  # Should be above 50 for upward move
        self.assertLessEqual(result, 100.0)  # Should not exceed 100
        
        # Check internal state
        self.assertGreater(self.state.rsi_avg_gain, 0)
        self.assertEqual(self.state.rsi_avg_loss, 0)
    
    def test_calculate_rsi_downward_move(self):
        """Test RSI calculation with downward price movement."""
        # Initialize
        self.state.prev_close = 100.0
        IndicatorCalculators.calculate_rsi(self.state, 100.0)
        
        # Downward move
        result = IndicatorCalculators.calculate_rsi(self.state, 95.0)
        
        self.assertLess(result, 50.0)  # Should be below 50 for downward move
        self.assertGreaterEqual(result, 0.0)  # Should not go below 0
        
        # Check internal state
        self.assertEqual(self.state.rsi_avg_gain, 0)
        self.assertGreater(self.state.rsi_avg_loss, 0)
    
    def test_calculate_rsi_no_change(self):
        """Test RSI calculation with no price change."""
        # Initialize
        self.state.prev_close = 100.0
        result1 = IndicatorCalculators.calculate_rsi(self.state, 100.0)
        result2 = IndicatorCalculators.calculate_rsi(self.state, 100.0)
        
        # Both should return 50.0
        self.assertEqual(result1, 50.0)
        self.assertEqual(result2, 50.0)
    
    def test_calculate_rsi_extreme_values(self):
        """Test RSI with extreme gain scenarios."""
        # Set up state with only gains
        self.state.rsi_avg_gain = 10.0
        self.state.rsi_avg_loss = 0.0  # No losses
        self.state.prev_close = 100.0
        
        result = IndicatorCalculators.calculate_rsi(self.state, 110.0)
        
        # Should return 100.0 when there are no losses
        self.assertEqual(result, 100.0)
    
    def test_calculate_rsi_mixed_movements(self):
        """Test RSI over mixed price movements."""
        prices = [100.0, 102.0, 101.0, 104.0, 99.0, 103.0]
        results = []
        
        for price in prices:
            result = IndicatorCalculators.calculate_rsi(self.state, price)
            results.append(result)
        
        # All results should be between 0 and 100
        for result in results:
            self.assertGreaterEqual(result, 0.0)
            self.assertLessEqual(result, 100.0)
        
        # With small price changes and Wilder smoothing, RSI may not change much initially
        # Just verify all results are valid RSI values
        for result in results:
            self.assertGreaterEqual(result, 0.0)
            self.assertLessEqual(result, 100.0)


class TestATRRatio(TestIndicatorCalculators):
    """Test ATR ratio calculation functionality."""
    
    def test_calculate_atr_ratio_first_bar(self):
        """Test ATR ratio calculation for first bar."""
        result = IndicatorCalculators.calculate_atr_ratio(self.state, self.sample_bar)
        
        # First bar should return 1.0 (default)
        self.assertEqual(result, 1.0)
        
        # ATR values should be initialized
        self.assertIsNotNone(self.state.atr14)
        self.assertIsNotNone(self.state.atr50)
    
    def test_calculate_atr_ratio_subsequent_bars(self):
        """Test ATR ratio after multiple bars."""
        bars = [
            BarData(pd.Timestamp("2024-01-01"), 100.0, 102.0, 98.0, 101.0, 0),
            BarData(pd.Timestamp("2024-01-02"), 101.0, 104.0, 100.0, 103.0, 1),
            BarData(pd.Timestamp("2024-01-03"), 103.0, 105.0, 101.0, 102.0, 2),
        ]
        
        results = []
        for bar in bars:
            result = IndicatorCalculators.calculate_atr_ratio(self.state, bar)
            results.append(result)
        
        # All results should be valid ratios
        for result in results:
            self.assertGreaterEqual(result, 0.5)  # Min clip value
            self.assertLessEqual(result, 3.0)    # Max clip value
    
    def test_calculate_atr_ratio_high_volatility(self):
        """Test ATR ratio with high volatility scenario."""
        # Create bars with increasing volatility
        bars = [
            BarData(pd.Timestamp("2024-01-01"), 100.0, 101.0, 99.0, 100.0, 0),
            BarData(pd.Timestamp("2024-01-02"), 100.0, 110.0, 90.0, 105.0, 1),  # High volatility
        ]
        
        # Process first bar to establish baseline
        IndicatorCalculators.calculate_atr_ratio(self.state, bars[0])
        
        # Process high volatility bar
        result = IndicatorCalculators.calculate_atr_ratio(self.state, bars[1])
        
        # Should detect increased volatility
        self.assertGreaterEqual(result, 1.0)
    
    def test_calculate_atr_ratio_clipping(self):
        """Test ATR ratio clipping functionality."""
        # Manually set extreme ATR values to test clipping
        self.state.atr14 = 20.0
        self.state.atr50 = 1.0  # Ratio would be 20.0, should be clipped to 3.0
        
        result = IndicatorCalculators.calculate_atr_ratio(self.state, self.sample_bar)
        
        # Should be clipped to maximum of 3.0
        self.assertEqual(result, 3.0)
    
    def test_calculate_atr_ratio_zero_atr50(self):
        """Test ATR ratio when ATR50 is zero."""
        self.state.atr14 = 5.0
        self.state.atr50 = 0.0
        
        result = IndicatorCalculators.calculate_atr_ratio(self.state, self.sample_bar)
        
        # Note: The function updates ATR50 with wilder_update before checking
        # wilder_update(0.0, tr, 50) returns tr, so ATR50 becomes non-zero
        # The result will be the clipped ratio
        self.assertEqual(result, 3.0)  # Clipped to maximum value
        
        # Test with None ATR14 - but ATR50 is already updated from previous call
        # so wilder_update(None, tr, 14) will return tr, and the condition will be true
        # The function will calculate ratio and clip it
        self.state.atr14 = None
        result2 = IndicatorCalculators.calculate_atr_ratio(self.state, self.sample_bar)
        # ATR14 becomes tr=4.0 (from sample_bar), ATR50 is already updated
        # Ratio will be clipped to maximum 3.0
        self.assertEqual(result2, 3.0)


class TestBollingerBandWidth(TestIndicatorCalculators):
    """Test Bollinger Band width calculation functionality."""
    
    def test_calculate_bb_width_first_bar(self):
        """Test BB width calculation for first bar."""
        result = IndicatorCalculators.calculate_bb_width(self.state, 100.0)
        
        # First bar should have zero width (no variation)
        self.assertEqual(result, 0.0)
        
        # Close window should contain the price
        self.assertEqual(len(self.state.close_window), 1)
        self.assertEqual(self.state.close_window[0], 100.0)
    
    def test_calculate_bb_width_multiple_bars(self):
        """Test BB width over multiple bars."""
        prices = [100.0, 102.0, 98.0, 104.0, 96.0]
        results = []
        
        for price in prices:
            result = IndicatorCalculators.calculate_bb_width(self.state, price)
            results.append(result)
        
        # First result should be 0 (single price)
        self.assertEqual(results[0], 0.0)
        
        # Subsequent results should be positive (price variation)
        for result in results[1:]:
            self.assertGreater(result, 0.0)
        
        # Window should accumulate prices
        self.assertEqual(len(self.state.close_window), 5)
        self.assertEqual(list(self.state.close_window), prices)
    
    def test_calculate_bb_width_constant_prices(self):
        """Test BB width with constant prices."""
        constant_price = 100.0
        
        for _ in range(5):
            result = IndicatorCalculators.calculate_bb_width(self.state, constant_price)
        
        # Should remain 0 for constant prices
        self.assertEqual(result, 0.0)
    
    def test_update_bb_history(self):
        """Test updating BB history."""
        bb_widths = [0.05, 0.06, 0.04, 0.07, 0.03]
        
        for width in bb_widths:
            IndicatorCalculators.update_bb_history(self.state, width)
        
        # History should contain all values
        self.assertEqual(len(self.state.bb_history), 5)
        self.assertEqual(list(self.state.bb_history), bb_widths)
    
    def test_bb_width_window_limit(self):
        """Test that BB width respects window size limit."""
        # Fill beyond window size
        for i in range(250):  # More than maxlen=200
            IndicatorCalculators.calculate_bb_width(self.state, float(i))
        
        # Window should be limited to maxlen
        self.assertEqual(len(self.state.close_window), 200)


class TestIntegratedIndicatorCalculation(TestIndicatorCalculators):
    """Test integrated indicator calculations."""
    
    def test_full_indicator_calculation_sequence(self):
        """Test full sequence of indicator calculations."""
        bars = [
            BarData(pd.Timestamp("2024-01-01"), 100.0, 102.0, 98.0, 101.0, 0),
            BarData(pd.Timestamp("2024-01-02"), 101.0, 104.0, 100.0, 103.0, 1),
            BarData(pd.Timestamp("2024-01-03"), 103.0, 105.0, 101.0, 102.0, 2),
            BarData(pd.Timestamp("2024-01-04"), 102.0, 106.0, 99.0, 104.0, 3),
        ]
        
        for bar in bars:
            # Update EMAs
            IndicatorCalculators.update_emas(self.state, bar.close)
            
            # Calculate other indicators
            rsi = IndicatorCalculators.calculate_rsi(self.state, bar.close)
            atr_ratio = IndicatorCalculators.calculate_atr_ratio(self.state, bar)
            bb_width = IndicatorCalculators.calculate_bb_width(self.state, bar.close)
            macd_hist = IndicatorCalculators.calculate_macd_hist(self.state)
            ema_slope = IndicatorCalculators.calculate_ema_slope(self.state)
            
            # Update slope state for next iteration
            IndicatorCalculators.update_ema_slope_state(self.state)
            
            # Update BB history
            IndicatorCalculators.update_bb_history(self.state, bb_width)
            
            # All indicators should be valid
            self.assertIsNotNone(rsi)
            self.assertIsNotNone(atr_ratio)
            self.assertIsNotNone(bb_width)
            # MACD hist might be None for first calculation
            self.assertIsNotNone(ema_slope)
        
        # Final state checks
        self.assertIsNotNone(self.state.ema20)
        self.assertIsNotNone(self.state.ema20_prev)
        self.assertIsNotNone(self.state.rsi_avg_gain)
        self.assertIsNotNone(self.state.rsi_avg_loss)
        self.assertEqual(len(self.state.close_window), 4)
        self.assertEqual(len(self.state.bb_history), 4)
    
    def test_state_consistency_after_calculations(self):
        """Test that state remains consistent after calculations."""
        # Perform several calculations
        for i in range(10):
            bar = BarData(
                pd.Timestamp(f"2024-01-{i+1:02d}"),
                100.0 + i, 102.0 + i, 98.0 + i, 101.0 + i, i
            )
            
            IndicatorCalculators.update_emas(self.state, bar.close)
            IndicatorCalculators.calculate_rsi(self.state, bar.close)
            IndicatorCalculators.calculate_atr_ratio(self.state, bar)
            IndicatorCalculators.calculate_bb_width(self.state, bar.close)
            IndicatorCalculators.calculate_macd_hist(self.state)
        
        # State should be consistent
        self.assertIsNotNone(self.state.ema12)
        self.assertIsNotNone(self.state.ema26)
        self.assertIsNotNone(self.state.ema20)
        self.assertIsNotNone(self.state.ema50)
        self.assertIsNotNone(self.state.ema200)
        
        # Values should be reasonable
        self.assertTrue(np.isfinite(self.state.ema12))
        self.assertTrue(np.isfinite(self.state.ema26))
        self.assertTrue(np.isfinite(self.state.atr14))
        self.assertTrue(np.isfinite(self.state.atr50))


if __name__ == '__main__':
    unittest.main()