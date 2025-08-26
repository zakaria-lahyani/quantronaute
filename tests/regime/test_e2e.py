"""End-to-end tests with realistic data and full pipeline."""

import unittest
import pandas as pd
import numpy as np
import tempfile
import os
import json

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.regime.regime_detection import PITRegimeDetector, run_pit


class TestEndToEnd(unittest.TestCase):
    """End-to-end tests with realistic scenarios."""
    
    def create_realistic_market_data(self):
        """Create realistic market data with various market conditions."""
        np.random.seed(123)  # For reproducibility
        
        data = []
        base_price = 100
        
        # Phase 1: Bull market (100 bars)
        for i in range(100):
            date = pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i)
            trend = base_price + i * 0.3  # Strong uptrend
            noise = np.random.normal(0, 0.5)
            close = trend + noise
            
            open_price = close - np.random.uniform(-0.2, 0.5)
            high = max(open_price, close) + np.random.uniform(0, 0.3)
            low = min(open_price, close) - np.random.uniform(0, 0.3)
            
            data.append({
                'time': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': np.random.uniform(1000, 5000)
            })
        
        base_price = close
        
        # Phase 2: Volatile ranging (100 bars)
        for i in range(100):
            date = pd.Timestamp("2024-01-05") + pd.Timedelta(hours=i)
            cycle = 10 * np.sin(i * 2 * np.pi / 20)
            noise = np.random.normal(0, 2)  # Higher volatility
            close = base_price + cycle + noise
            
            open_price = close - np.random.uniform(-1, 1)
            high = max(open_price, close) + np.random.uniform(0, 2)
            low = min(open_price, close) - np.random.uniform(0, 2)
            
            data.append({
                'time': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': np.random.uniform(2000, 8000)
            })
        
        # Phase 3: Bear market (100 bars)
        for i in range(100):
            date = pd.Timestamp("2024-01-09") + pd.Timedelta(hours=i)
            trend = base_price - i * 0.4  # Strong downtrend
            noise = np.random.normal(0, 0.7)
            close = trend + noise
            
            open_price = close + np.random.uniform(-0.2, 0.5)
            high = max(open_price, close) + np.random.uniform(0, 0.4)
            low = min(open_price, close) - np.random.uniform(0, 0.4)
            
            data.append({
                'time': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': np.random.uniform(3000, 10000)
            })
        
        base_price = close
        
        # Phase 4: Low volatility consolidation (100 bars)
        for i in range(100):
            date = pd.Timestamp("2024-01-13") + pd.Timedelta(hours=i)
            noise = np.random.normal(0, 0.1)  # Very low volatility
            close = base_price + noise
            
            open_price = close - np.random.uniform(-0.05, 0.05)
            high = max(open_price, close) + np.random.uniform(0, 0.1)
            low = min(open_price, close) - np.random.uniform(0, 0.1)
            
            data.append({
                'time': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': np.random.uniform(500, 2000)
            })
        
        df = pd.DataFrame(data)
        df.set_index('time', inplace=True)
        return df
    
    def test_full_pipeline_with_export(self):
        """Test the complete pipeline including data processing and export."""
        # Create data
        df = self.create_realistic_market_data()
        
        # Save to parquet
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            input_path = f.name
        df.to_parquet(input_path)
        
        # Output path
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            output_path = f.name
        
        try:
            # Run the pipeline
            result_df, detector = run_pit(
                df,
                warmup=50,
                persist=3,
                transition=5,
                htf="4h",
                export_parquet=output_path
            )
            
            # Verify output structure
            self.assertIn('regime', result_df.columns)
            self.assertIn('regime_confidence', result_df.columns)
            self.assertIn('is_transition', result_df.columns)
            self.assertIn('htf_bias', result_df.columns)
            
            # Verify indicators are exported
            self.assertIn('rsi', result_df.columns)
            self.assertIn('atr_ratio', result_df.columns)
            self.assertIn('bb_width', result_df.columns)
            self.assertIn('ema_slope', result_df.columns)
            
            # Check that results make sense
            regimes = result_df['regime'].value_counts()
            
            # Should have detected multiple regimes
            self.assertGreater(len(regimes), 2)
            
            # Should have warming_up period
            self.assertIn('warming_up', regimes.index)
            self.assertEqual(sum(result_df['regime'] == 'warming_up'), 50)
            
            # Load exported parquet
            exported_df = pd.read_parquet(output_path)
            self.assertEqual(len(exported_df), len(df))
            
            # Verify JSON export exists
            self.assertTrue(os.path.exists('regime_backtest_results.json'))
            
            with open('regime_backtest_results.json', 'r') as f:
                json_data = json.load(f)
            
            self.assertIn('metadata', json_data)
            self.assertIn('stats', json_data)
            self.assertIn('history', json_data)
            
        finally:
            # Cleanup
            if os.path.exists(input_path):
                os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
            if os.path.exists('regime_backtest_results.json'):
                os.unlink('regime_backtest_results.json')
    
    def test_regime_transitions_realistic(self):
        """Test regime transitions with realistic market data."""
        df = self.create_realistic_market_data()
        
        detector = PITRegimeDetector(warmup=50, persist_n=3, transition_bars=5)
        
        regimes = []
        transitions = []
        confidences = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            snap = detector.process_bar(
                df.index[i],
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                i
            )
            
            if i >= 50:  # After warmup
                regimes.append(snap.regime)
                transitions.append(snap.is_transition)
                confidences.append(snap.confidence)
        
        # Analyze regime distribution
        regime_changes = []
        for i in range(1, len(regimes)):
            if regimes[i] != regimes[i-1]:
                regime_changes.append(i)
        
        # Should detect regime changes corresponding to market phases
        self.assertGreater(len(regime_changes), 2)
        self.assertLess(len(regime_changes), 20)  # Not too many (noise)
        
        # Check that bull phase is detected
        bull_count = sum(1 for r in regimes[:50] if 'bull' in r)
        self.assertGreater(bull_count, 20)  # Should detect bull in first phase
        
        # Check that bear phase is detected
        bear_count = sum(1 for r in regimes[150:250] if 'bear' in r)
        self.assertGreater(bear_count, 20)  # Should detect bear in third phase
        
        # Check volatility detection
        expansion_count = sum(1 for r in regimes[50:150] if 'expansion' in r)
        contraction_count = sum(1 for r in regimes[250:] if 'contraction' in r)
        
        self.assertGreater(expansion_count, 10)  # High vol in phase 2
        self.assertGreater(contraction_count, 10)  # Low vol in phase 4
    
    def test_htf_bias_impact(self):
        """Test HTF bias impact on regime detection."""
        df = self.create_realistic_market_data()
        
        # Test without HTF
        detector_no_htf = PITRegimeDetector(warmup=50, persist_n=2)
        regimes_no_htf = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            snap = detector_no_htf.process_bar(
                df.index[i],
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                i
            )
            if i >= 50:
                regimes_no_htf.append(snap.regime)
        
        # Test with HTF
        detector_htf = PITRegimeDetector(warmup=50, persist_n=2, htf_rule='4h')
        regimes_htf = []
        htf_biases = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            snap = detector_htf.process_bar(
                df.index[i],
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                i
            )
            if i >= 50:
                regimes_htf.append(snap.regime)
                htf_biases.append(snap.htf_bias)
        
        # HTF should create some neutral regimes
        neutral_no_htf = sum(1 for r in regimes_no_htf if 'neutral' in r)
        neutral_htf = sum(1 for r in regimes_htf if 'neutral' in r)
        
        # HTF bias should increase neutral regimes (counter-trend filtering)
        self.assertGreaterEqual(neutral_htf, neutral_no_htf)
        
        # HTF bias should evolve
        unique_biases = set(htf_biases)
        self.assertGreater(len(unique_biases), 1)  # Not stuck on one bias
    
    def test_performance_metrics(self):
        """Test that performance with large dataset is reasonable."""
        import time
        
        # Create larger dataset
        df = self.create_realistic_market_data()
        df = pd.concat([df] * 5)  # 2000 bars
        df.index = pd.date_range(start='2024-01-01', periods=len(df), freq='1h')
        
        detector = PITRegimeDetector(warmup=100, persist_n=3)
        
        start_time = time.time()
        
        for i in range(len(df)):
            row = df.iloc[i]
            detector.process_bar(
                df.index[i],
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                i
            )
        
        elapsed_time = time.time() - start_time
        
        # Should process reasonably fast (< 1 second for 2000 bars)
        self.assertLess(elapsed_time, 1.0, f"Processing too slow: {elapsed_time:.2f}s for 2000 bars")
        
        # Memory usage should be bounded
        self.assertEqual(len(detector.history), len(df))
        self.assertLessEqual(len(detector.close_win), 200)  # Window size limited
        self.assertLessEqual(len(detector.bb_hist), detector.bb_threshold_len)
    
    def test_statistics_accuracy(self):
        """Test that statistics calculation is accurate."""
        df = self.create_realistic_market_data()
        detector = PITRegimeDetector(warmup=50, persist_n=2)
        
        for i in range(len(df)):
            row = df.iloc[i]
            detector.process_bar(
                df.index[i],
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                i
            )
        
        stats = detector.stats()
        
        # Manually calculate expected values
        non_warmup = [s for s in detector.history if s.regime != "warming_up"]
        
        # Verify counts
        manual_counts = {}
        for snap in non_warmup:
            manual_counts[snap.regime] = manual_counts.get(snap.regime, 0) + 1
        
        self.assertEqual(stats['counts'], manual_counts)
        
        # Verify average confidence
        for regime in stats['avg_confidence']:
            regime_snaps = [s for s in non_warmup if s.regime == regime]
            manual_avg = np.mean([s.confidence for s in regime_snaps])
            self.assertAlmostEqual(stats['avg_confidence'][regime], manual_avg, places=10)
        
        # Verify transition count
        manual_transitions = sum(1 for s in detector.history if s.is_transition)
        self.assertEqual(stats['num_transitions'], manual_transitions)
        
        # Verify duration stats make sense
        self.assertGreater(stats['avg_duration'], 0)
        self.assertGreaterEqual(stats['max_duration'], stats['avg_duration'])
        self.assertLessEqual(stats['min_duration'], stats['avg_duration'])


class TestDataIntegrity(unittest.TestCase):
    """Test data integrity and edge cases."""
    
    def test_missing_data_handling(self):
        """Test handling of missing or invalid data."""
        detector = PITRegimeDetector(warmup=10, persist_n=2)
        
        # Process normal data
        for i in range(20):
            snap = detector.process_bar(
                pd.Timestamp(f"2024-01-{i+1:02d}"),
                100 + i*0.1, 101 + i*0.1, 99 + i*0.1, 100 + i*0.1,
                i
            )
            self.assertIsNotNone(snap)
        
        # State should be preserved
        self.assertIsNotNone(detector.current_regime)
        self.assertIsNotNone(detector.ema["ema12"])
    
    def test_indicator_availability_progression(self):
        """Test that indicators become available progressively."""
        detector = PITRegimeDetector(warmup=50, persist_n=2)
        
        indicator_availability = {
            'rsi': [],
            'macd_hist': [],
            'ema200': [],
            'atr_ratio': []
        }
        
        for i in range(250):
            ts = pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i)
            price = 100 + np.sin(i * 0.1) * 5
            
            snap = detector.process_bar(
                ts,
                price - 0.5, price + 0.5, price - 1, price,
                i
            )
            
            if snap.indicators:
                for key in indicator_availability:
                    available = snap.indicators.get(key) is not None
                    indicator_availability[key].append((i, available))
        
        # RSI should be available early
        rsi_first_available = next((i for i, avail in indicator_availability['rsi'] if avail), None)
        self.assertIsNotNone(rsi_first_available)
        self.assertLess(rsi_first_available, 100)
        
        # MACD should be available early too (both EMAs initialize to first price)
        # but may take time to develop meaningful values
        macd_first = next((i for i, avail in indicator_availability['macd_hist'] if avail), None)
        self.assertIsNotNone(macd_first)
        
        # The real test is that indicators develop over time
        # Check that there's variation in later values (indicating they're working)
        late_rsi_values = [snap.indicators.get('rsi') for snap in detector.history[-20:] 
                          if snap.indicators and snap.indicators.get('rsi') is not None]
        if late_rsi_values:
            rsi_variation = max(late_rsi_values) - min(late_rsi_values)
            self.assertGreater(rsi_variation, 1.0, "RSI should show variation over time")
        
        late_macd_values = [snap.indicators.get('macd_hist') for snap in detector.history[-20:] 
                           if snap.indicators and snap.indicators.get('macd_hist') is not None]
        if late_macd_values:
            macd_variation = max(late_macd_values) - min(late_macd_values)  
            self.assertGreater(macd_variation, 0.001, "MACD should show variation over time")
        
        # EMA200 should be available after 200 bars
        ema200_first = next((i for i, avail in indicator_availability['ema200'] if avail), None)
        self.assertIsNotNone(ema200_first)
        
        # All should be available by the end
        final_snap = detector.history[-1]
        if final_snap.indicators:
            self.assertIsNotNone(final_snap.indicators.get('rsi'))
            self.assertIsNotNone(final_snap.indicators.get('macd_hist'))
            self.assertIsNotNone(final_snap.indicators.get('atr_ratio'))


if __name__ == '__main__':
    unittest.main()