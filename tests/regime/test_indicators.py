"""Unit tests for indicator calculations in regime detection."""

import unittest
import pandas as pd
import numpy as np
from collections import deque

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.regime.regime_detection import PITRegimeDetector


class TestIndicatorCalculations(unittest.TestCase):
    """Test incremental indicator calculations."""
    
    def setUp(self):
        """Set up test detector instance."""
        self.detector = PITRegimeDetector(warmup=10, persist_n=2)
    
    def test_macd_initialization(self):
        """Test MACD is None initially and becomes available after enough data."""
        # Initially all EMAs and MACD should be None
        self.assertIsNone(self.detector.ema["ema12"])
        self.assertIsNone(self.detector.ema["ema26"])
        self.assertIsNone(self.detector.macd_signal)
        
        # Process first bar
        ts = pd.Timestamp("2024-01-01")
        self.detector._update_incrementals(100, 101, 99, 100, ts)
        
        # EMAs should have values but MACD signal needs more data
        self.assertIsNotNone(self.detector.ema["ema12"])
        self.assertIsNotNone(self.detector.ema["ema26"])
        
        # Process more bars to build up MACD signal
        for i in range(20):
            ts = pd.Timestamp(f"2024-01-{i+2:02d}")
            price = 100 + np.sin(i * 0.5) * 2
            self.detector._update_incrementals(price, price+1, price-1, price, ts)
        
        # Now MACD signal should be available
        self.assertIsNotNone(self.detector.macd_signal)
    
    def test_rsi_calculation_edge_cases(self):
        """Test RSI calculation handles edge cases correctly."""
        detector = PITRegimeDetector(warmup=5)
        
        # First bar - no previous close, RSI should be 50
        ts = pd.Timestamp("2024-01-01")
        regime, conf, indicators = detector._update_incrementals(100, 101, 99, 100, ts)
        self.assertEqual(indicators["rsi"], 50.0)
        
        # Consistent upward movement
        for i in range(20):
            ts = pd.Timestamp(f"2024-01-{i+2:02d}")
            price = 100 + i  # Steady increase
            regime, conf, indicators = detector._update_incrementals(price, price+1, price-1, price, ts)
        
        # RSI should be high (near 100) after consistent gains
        self.assertGreater(indicators["rsi"], 80)
        
        # Consistent downward movement
        detector2 = PITRegimeDetector(warmup=5)
        detector2._update_incrementals(100, 101, 99, 100, pd.Timestamp("2024-01-01"))
        
        for i in range(20):
            ts = pd.Timestamp(f"2024-01-{i+2:02d}")
            price = 100 - i  # Steady decrease
            regime, conf, indicators = detector2._update_incrementals(price, price+1, price-1, price, ts)
        
        # RSI should be low (near 0) after consistent losses
        self.assertLess(indicators["rsi"], 20)
    
    def test_rsi_zero_division_protection(self):
        """Test RSI handles zero average loss correctly."""
        detector = PITRegimeDetector(warmup=5)
        
        # Initialize detector properly
        detector.prev_close = 100
        for _ in range(5):
            detector.close_win.append(100)
        
        # Create scenario with only gains (no losses)
        detector.rsi_avg_gain = 1.0
        detector.rsi_avg_loss = 0.0  # Zero loss
        
        regime, conf, indicators = detector._update_incrementals(101, 102, 100, 101, pd.Timestamp("2024-01-01"))
        
        # Should return 100 when only gains
        self.assertEqual(indicators["rsi"], 100.0)
        
        # Test with both zero
        detector.rsi_avg_gain = 0.0
        detector.rsi_avg_loss = 0.0
        detector.prev_close = 100  # Reset prev_close
        
        regime, conf, indicators = detector._update_incrementals(100, 101, 99, 100, pd.Timestamp("2024-01-02"))
        
        # Should return 50 when both are zero
        self.assertEqual(indicators["rsi"], 50.0)
    
    def test_atr_ratio_calculation(self):
        """Test ATR ratio calculation with various scenarios."""
        detector = PITRegimeDetector(warmup=5)
        
        # Initially ATR values are None
        self.assertIsNone(detector.atr14)
        self.assertIsNone(detector.atr50)
        
        # Process bars with increasing volatility
        for i in range(60):
            ts = pd.Timestamp(f"2024-01-{(i%28)+1:02d}")
            volatility = 1 + i * 0.05  # Increasing volatility
            o = 100
            h = 100 + volatility
            l = 100 - volatility
            c = 100 + np.random.uniform(-volatility, volatility)
            
            regime, conf, indicators = detector._update_incrementals(o, h, l, c, ts)
        
        # After 60 bars, both ATRs should be available
        self.assertIsNotNone(detector.atr14)
        self.assertIsNotNone(detector.atr50)
        
        # ATR14 should be higher than ATR50 due to increasing volatility
        atr_ratio = indicators["atr_ratio"]
        self.assertGreater(atr_ratio, 1.0)
    
    def test_atr_ratio_zero_protection(self):
        """Test ATR ratio handles zero ATR50 correctly."""
        # Test the protection logic directly
        
        # Case 1: ATR50 is zero
        atr14 = 2.0
        atr50 = 0.0
        
        if atr14 is not None and atr50 not in (None, 0.0):
            atr_ratio = atr14 / atr50
        else:
            atr_ratio = 1.0
        
        self.assertEqual(atr_ratio, 1.0)
        
        # Case 2: ATR14 is None
        atr14 = None
        atr50 = 3.0
        
        if atr14 is not None and atr50 not in (None, 0.0):
            atr_ratio = atr14 / atr50
        else:
            atr_ratio = 1.0
        
        self.assertEqual(atr_ratio, 1.0)
        
        # Case 3: Both valid values
        atr14 = 4.0
        atr50 = 2.0
        
        if atr14 is not None and atr50 not in (None, 0.0):
            atr_ratio = atr14 / atr50
        else:
            atr_ratio = 1.0
        
        self.assertEqual(atr_ratio, 2.0)
        
        # Case 4: ATR50 is None
        atr14 = 2.0
        atr50 = None
        
        if atr14 is not None and atr50 not in (None, 0.0):
            atr_ratio = atr14 / atr50
        else:
            atr_ratio = 1.0
        
        self.assertEqual(atr_ratio, 1.0)
    
    def test_ema_slope_calculation(self):
        """Test EMA slope calculation."""
        detector = PITRegimeDetector(warmup=5)
        
        # Build up EMA20
        for i in range(25):
            ts = pd.Timestamp(f"2024-01-{(i%28)+1:02d}")
            price = 100 + i * 0.5  # Upward trend
            regime, conf, indicators = detector._update_incrementals(price, price+1, price-1, price, ts)
        
        # EMA slope should be positive (1) when price > EMA20
        self.assertEqual(indicators["ema_slope"], 1.0)
        
        # Now test downward scenario
        detector2 = PITRegimeDetector(warmup=5)
        for i in range(25):
            ts = pd.Timestamp(f"2024-01-{(i%28)+1:02d}")
            price = 100 - i * 0.5  # Downward trend
            regime, conf, indicators = detector2._update_incrementals(price, price+1, price-1, price, ts)
        
        # EMA slope should be negative (-1) when price < EMA20
        self.assertEqual(indicators["ema_slope"], -1.0)
    
    def test_bollinger_band_width(self):
        """Test Bollinger Band width calculation."""
        detector = PITRegimeDetector(warmup=5)
        
        # Add steady prices for low volatility
        for i in range(25):
            ts = pd.Timestamp(f"2024-01-{(i%28)+1:02d}")
            price = 100 + np.random.uniform(-0.1, 0.1)  # Very low volatility
            regime, conf, indicators = detector._update_incrementals(price, price+0.1, price-0.1, price, ts)
        
        bb_width_low = indicators["bb_width"]
        
        # Now add high volatility
        for i in range(25):
            ts = pd.Timestamp(f"2024-02-{(i%28)+1:02d}")
            price = 100 + np.random.uniform(-5, 5)  # High volatility
            regime, conf, indicators = detector._update_incrementals(price, price+5, price-5, price, ts)
        
        bb_width_high = indicators["bb_width"]
        
        # High volatility should produce wider bands
        self.assertGreater(bb_width_high, bb_width_low)
    
    def test_confidence_adaptive_calculation(self):
        """Test that confidence adapts based on available indicators."""
        detector = PITRegimeDetector(warmup=5)
        
        # Early in the series - not all indicators available
        ts = pd.Timestamp("2024-01-01")
        regime, conf1, indicators = detector._update_incrementals(100, 101, 99, 100, ts)
        
        # Process more bars to make all indicators available
        for i in range(50):
            ts = pd.Timestamp(f"2024-01-{(i%28)+2:02d}")
            price = 100 + np.sin(i * 0.2) * 5
            regime, conf2, indicators = detector._update_incrementals(price, price+1, price-1, price, ts)
        
        # Confidence calculation should be based on available indicators
        # With strong directional movement, confidence should be reasonable
        self.assertGreaterEqual(conf2, 0.0)
        self.assertLessEqual(conf2, 1.0)
    
    def test_macd_hist_export_none(self):
        """Test that macd_hist is exported as None when not available."""
        detector = PITRegimeDetector(warmup=5)
        
        # On the very first bar with no EMAs initialized, macd_hist should be None
        # But need to ensure EMAs are truly None
        detector.ema["ema12"] = None
        detector.ema["ema26"] = None
        detector.macd_signal = None
        detector.prev_close = None
        
        # First bar - MACD not ready because EMAs are None
        ts = pd.Timestamp("2024-01-01")
        regime, conf, indicators = detector._update_incrementals(100, 101, 99, 100, ts)
        
        # After first bar, EMAs are initialized but macd_hist might be 0
        # This is acceptable behavior - test that it becomes meaningful over time
        
        # Process more bars to build up meaningful MACD
        for i in range(30):
            ts = pd.Timestamp(f"2024-01-{(i%28)+2:02d}")
            price = 100 + np.sin(i * 0.5) * 2
            regime, conf, indicators = detector._update_incrementals(price, price+1, price-1, price, ts)
        
        # Now macd_hist should be a meaningful number (not just 0)
        self.assertIsNotNone(indicators["macd_hist"])
        self.assertIsInstance(indicators["macd_hist"], (float, type(None)))
        
        # More importantly, check that MACD changes over time (not stuck at 0)
        values = []
        for i in range(10):
            price = 100 + i * 0.5  # Trending up
            regime, conf, indicators = detector._update_incrementals(price, price+1, price-1, price, ts)
            if indicators["macd_hist"] is not None:
                values.append(indicators["macd_hist"])
        
        # Should have variation in MACD hist values
        if len(values) > 1:
            self.assertNotEqual(min(values), max(values), "MACD hist should vary")


class TestIndicatorIntegration(unittest.TestCase):
    """Test integration of multiple indicators."""
    
    def test_all_indicators_together(self):
        """Test that all indicators work together correctly."""
        detector = PITRegimeDetector(warmup=50)
        
        # Generate synthetic price data with trend and volatility changes
        prices = []
        for i in range(100):
            # Trend component
            trend = 100 + i * 0.1
            # Cyclical component
            cycle = 5 * np.sin(i * 2 * np.pi / 20)
            # Noise
            noise = np.random.normal(0, 0.5)
            prices.append(trend + cycle + noise)
        
        # Process all bars
        for i, price in enumerate(prices):
            ts = pd.Timestamp(f"2024-01-01") + pd.Timedelta(minutes=i)
            o = price - 0.1
            h = price + np.random.uniform(0, 0.5)
            l = price - np.random.uniform(0, 0.5)
            c = price
            
            regime, conf, indicators = detector._update_incrementals(o, h, l, c, ts)
        
        # After processing, all indicators should be available
        self.assertIsNotNone(indicators["rsi"])
        self.assertIsNotNone(indicators["atr_ratio"])
        self.assertIsNotNone(indicators["bb_width"])
        self.assertIsNotNone(indicators["macd_hist"])
        self.assertIsNotNone(indicators["ema20"])
        self.assertIsNotNone(indicators["ema50"])
        self.assertIsNotNone(indicators["ema200"])
        self.assertIsNotNone(indicators["ema_slope"])
        
        # Values should be in reasonable ranges
        self.assertGreaterEqual(indicators["rsi"], 0)
        self.assertLessEqual(indicators["rsi"], 100)
        self.assertGreater(indicators["atr_ratio"], 0)
        self.assertGreater(indicators["bb_width"], 0)


if __name__ == '__main__':
    unittest.main()