"""Final verification test for incremental computation consistency."""

import unittest
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.regime.regime_detection import PITRegimeDetector


class TestFinalVerification(unittest.TestCase):
    """Final verification that incremental computation is consistent."""
    
    def test_incremental_computation_deterministic(self):
        """Verify that processing the same data multiple times gives identical results."""
        np.random.seed(42)
        
        # Generate test data
        n_bars = 500
        dates = pd.date_range(start='2024-01-01', periods=n_bars, freq='1h')
        prices = []
        
        for i in range(n_bars):
            # Deterministic price generation
            trend = 100 + i * 0.05
            cycle = 5 * np.sin(i * 2 * np.pi / 50)
            noise = np.random.normal(0, 1)
            prices.append(trend + cycle + noise)
        
        # Create OHLC data
        data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            open_price = close - np.random.uniform(-0.5, 0.5)
            high = max(open_price, close) + np.random.uniform(0, 1)
            low = min(open_price, close) - np.random.uniform(0, 1)
            
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close
            })
        
        df = pd.DataFrame(data)
        
        # Process data three times
        results = []
        for run in range(3):
            detector = PITRegimeDetector(warmup=100, persist_n=3)
            run_results = []
            
            for i, row in df.iterrows():
                snap = detector.process_bar(
                    row['timestamp'],
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    i
                )
                
                # Store key values
                run_results.append({
                    'regime': snap.regime,
                    'confidence': snap.confidence,
                    'is_transition': snap.is_transition,
                    'rsi': snap.indicators.get('rsi') if snap.indicators else None,
                    'bb_width': snap.indicators.get('bb_width') if snap.indicators else None,
                    'atr_ratio': snap.indicators.get('atr_ratio') if snap.indicators else None
                })
            
            results.append(run_results)
        
        # All three runs should be identical
        for bar_idx in range(n_bars):
            # Compare run 1 with run 0
            self.assertEqual(
                results[0][bar_idx]['regime'],
                results[1][bar_idx]['regime'],
                f"Regime mismatch at bar {bar_idx} between run 0 and 1"
            )
            
            # Compare run 2 with run 0
            self.assertEqual(
                results[0][bar_idx]['regime'],
                results[2][bar_idx]['regime'],
                f"Regime mismatch at bar {bar_idx} between run 0 and 2"
            )
            
            # Check confidence
            if results[0][bar_idx]['confidence'] is not None:
                self.assertAlmostEqual(
                    results[0][bar_idx]['confidence'],
                    results[1][bar_idx]['confidence'],
                    places=10,
                    msg=f"Confidence mismatch at bar {bar_idx}"
                )
                self.assertAlmostEqual(
                    results[0][bar_idx]['confidence'],
                    results[2][bar_idx]['confidence'],
                    places=10,
                    msg=f"Confidence mismatch at bar {bar_idx}"
                )
            
            # Check transitions
            self.assertEqual(
                results[0][bar_idx]['is_transition'],
                results[1][bar_idx]['is_transition'],
                f"Transition mismatch at bar {bar_idx}"
            )
    
    def test_no_future_leakage(self):
        """Verify that future data doesn't affect past results."""
        np.random.seed(123)
        
        # Generate test data
        n_bars = 200
        dates = pd.date_range(start='2024-01-01', periods=n_bars, freq='1h')
        prices = [100 + i * 0.1 + np.random.normal(0, 1) for i in range(n_bars)]
        
        data = []
        for date, close in zip(dates, prices):
            open_price = close - 0.5
            high = close + 1
            low = close - 1
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close
            })
        
        df = pd.DataFrame(data)
        
        # Process first 100 bars
        detector1 = PITRegimeDetector(warmup=50, persist_n=2)
        results_100 = []
        
        for i in range(100):
            row = df.iloc[i]
            snap = detector1.process_bar(
                row['timestamp'],
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                i
            )
            results_100.append({
                'regime': snap.regime,
                'rsi': snap.indicators.get('rsi') if snap.indicators else None
            })
        
        # Process all 200 bars with new detector
        detector2 = PITRegimeDetector(warmup=50, persist_n=2)
        results_200 = []
        
        for i in range(200):
            row = df.iloc[i]
            snap = detector2.process_bar(
                row['timestamp'],
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                i
            )
            results_200.append({
                'regime': snap.regime,
                'rsi': snap.indicators.get('rsi') if snap.indicators else None
            })
        
        # First 100 bars should be identical
        for i in range(100):
            self.assertEqual(
                results_100[i]['regime'],
                results_200[i]['regime'],
                f"Future data affected bar {i} regime"
            )
            
            if results_100[i]['rsi'] is not None and results_200[i]['rsi'] is not None:
                self.assertAlmostEqual(
                    results_100[i]['rsi'],
                    results_200[i]['rsi'],
                    places=10,
                    msg=f"Future data affected bar {i} RSI"
                )
    
    def test_regime_detection_consistency(self):
        """Test that regime detection is consistent with market conditions."""
        # Create clear market scenarios
        detector = PITRegimeDetector(warmup=30, persist_n=2)
        
        # Bull market scenario
        for i in range(50):
            ts = pd.Timestamp('2024-01-01') + pd.Timedelta(hours=i)
            price = 100 + i * 0.5  # Clear uptrend
            snap = detector.process_bar(
                ts,
                price - 0.2,  # open
                price + 0.3,  # high
                price - 0.3,  # low
                price,        # close
                i
            )
        
        # After warmup and persistence, should detect bull
        if snap.regime != "warming_up":
            self.assertIn("bull", snap.regime)
        
        # Bear market scenario
        detector2 = PITRegimeDetector(warmup=30, persist_n=2)
        
        for i in range(50):
            ts = pd.Timestamp('2024-01-01') + pd.Timedelta(hours=i)
            price = 100 - i * 0.5  # Clear downtrend
            snap = detector2.process_bar(
                ts,
                price + 0.2,  # open
                price + 0.3,  # high
                price - 0.3,  # low
                price,        # close
                i
            )
        
        # After warmup and persistence, should detect bear
        if snap.regime != "warming_up":
            self.assertIn("bear", snap.regime)
    
    def test_indicator_values_reasonable(self):
        """Test that all indicator values are within reasonable ranges."""
        detector = PITRegimeDetector(warmup=50, persist_n=2)
        
        # Process enough bars to get all indicators
        for i in range(250):
            ts = pd.Timestamp('2024-01-01') + pd.Timedelta(hours=i)
            price = 100 + np.sin(i * 0.1) * 5
            
            snap = detector.process_bar(
                ts,
                price - 0.5,
                price + 0.5,
                price - 1,
                price,
                i
            )
            
            if snap.indicators:
                # RSI should be between 0 and 100
                if 'rsi' in snap.indicators and snap.indicators['rsi'] is not None:
                    self.assertGreaterEqual(snap.indicators['rsi'], 0)
                    self.assertLessEqual(snap.indicators['rsi'], 100)
                
                # ATR ratio should be positive
                if 'atr_ratio' in snap.indicators and snap.indicators['atr_ratio'] is not None:
                    self.assertGreater(snap.indicators['atr_ratio'], 0)
                
                # BB width should be non-negative
                if 'bb_width' in snap.indicators and snap.indicators['bb_width'] is not None:
                    self.assertGreaterEqual(snap.indicators['bb_width'], 0)
                
                # Confidence should be between 0 and 1
                if snap.confidence is not None:
                    self.assertGreaterEqual(snap.confidence, 0)
                    self.assertLessEqual(snap.confidence, 1)


if __name__ == '__main__':
    unittest.main()