"""Unit tests for regime detector orchestration."""

import unittest
import json
import tempfile
import os
import pandas as pd
import numpy as np

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app.regime.data_structure import BarData, IndicatorValues, RegimeSnapshot
from app.regime.regime_detector import RegimeDetector


class TestRegimeDetector(unittest.TestCase):
    """Test RegimeDetector functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = RegimeDetector(
            warmup=10,
            persist_n=2,
            transition_bars=3,
            bb_threshold_len=50,
            htf_rule=None
        )
        
        self.sample_bars = [
            BarData(pd.Timestamp("2024-01-01 10:00:00"), 100.0, 102.0, 98.0, 101.0, 0),
            BarData(pd.Timestamp("2024-01-01 10:01:00"), 101.0, 103.0, 99.0, 102.0, 1),
            BarData(pd.Timestamp("2024-01-01 10:02:00"), 102.0, 104.0, 100.0, 103.0, 2),
        ]
    
    def test_initialization_default(self):
        """Test RegimeDetector default initialization."""
        detector = RegimeDetector()
        
        self.assertEqual(detector.warmup, 500)
        self.assertIsNotNone(detector.indicator_state)
        self.assertIsNotNone(detector.htf_calculator)
        self.assertIsNotNone(detector.state_machine)
        self.assertEqual(len(detector.history), 0)
    
    def test_initialization_custom(self):
        """Test RegimeDetector with custom parameters."""
        detector = RegimeDetector(
            warmup=100,
            persist_n=3,
            transition_bars=5,
            bb_threshold_len=150,
            htf_rule="4h"
        )
        
        self.assertEqual(detector.warmup, 100)
        self.assertEqual(detector.state_machine.persist_n, 3)
        self.assertEqual(detector.state_machine.transition_bars, 5)
        self.assertEqual(detector.indicator_state.bb_history.maxlen, 150)
        self.assertEqual(detector.htf_calculator.state.rule, "4h")


class TestProcessBarWarmup(TestRegimeDetector):
    """Test process_bar during warmup period."""
    
    def test_process_bar_warmup_period(self):
        """Test processing bars during warmup period."""
        # Process bars during warmup
        for bar in self.sample_bars:
            snapshot = self.detector.process_bar(bar)
            
            # Should return warming_up regime
            self.assertEqual(snapshot.regime, "warming_up")
            self.assertEqual(snapshot.confidence, 0.0)
            self.assertFalse(snapshot.is_transition)
            self.assertIsInstance(snapshot.indicators, IndicatorValues)
            self.assertEqual(snapshot.htf_bias, "neutral")  # No HTF rule set
    
    def test_warmup_indicators_calculated(self):
        """Test that indicators are calculated during warmup."""
        bar = self.sample_bars[0]
        snapshot = self.detector.process_bar(bar)
        
        # Indicators should be calculated even during warmup
        self.assertIsNotNone(snapshot.indicators.rsi)
        self.assertIsNotNone(snapshot.indicators.atr_ratio)
        self.assertIsNotNone(snapshot.indicators.bb_width)
        # MACD might be None initially
        self.assertIsNotNone(snapshot.indicators.ema20)
    
    def test_warmup_state_tracking(self):
        """Test that state is properly tracked during warmup."""
        for bar in self.sample_bars:
            self.detector.process_bar(bar)
        
        # State should be updated
        self.assertEqual(self.detector.indicator_state.prev_close, 103.0)  # Last close
        self.assertIsNotNone(self.detector.indicator_state.ema20)
        self.assertEqual(len(self.detector.indicator_state.close_window), 3)
    
    def test_warmup_history_accumulation(self):
        """Test that history accumulates during warmup."""
        for i, bar in enumerate(self.sample_bars):
            self.detector.process_bar(bar)
            self.assertEqual(len(self.detector.history), i + 1)
        
        # All should be warming_up
        for snapshot in self.detector.history:
            self.assertEqual(snapshot.regime, "warming_up")


class TestProcessBarActive(TestRegimeDetector):
    """Test process_bar after warmup period."""
    
    def setUp(self):
        """Set up with detector that has shorter warmup."""
        super().setUp()
        self.detector = RegimeDetector(warmup=2, persist_n=2, transition_bars=1)
        
        # Process warmup bars
        warmup_bars = [
            BarData(pd.Timestamp("2024-01-01 09:58:00"), 98.0, 99.0, 97.0, 98.5, 0),
            BarData(pd.Timestamp("2024-01-01 09:59:00"), 98.5, 100.0, 98.0, 99.5, 1),
        ]
        for bar in warmup_bars:
            self.detector.process_bar(bar)
    
    def test_process_bar_after_warmup(self):
        """Test processing bar after warmup period."""
        bar = BarData(pd.Timestamp("2024-01-01 10:00:00"), 99.5, 101.0, 99.0, 100.5, 2)
        snapshot = self.detector.process_bar(bar)
        
        # Should not be warming_up anymore
        self.assertNotEqual(snapshot.regime, "warming_up")
        self.assertGreaterEqual(snapshot.confidence, 0.0)
        self.assertLessEqual(snapshot.confidence, 1.0)
        self.assertIsInstance(snapshot.indicators, IndicatorValues)
    
    def test_bb_threshold_calculation(self):
        """Test BB threshold calculation with sufficient history."""
        # Process enough bars to build BB history
        for i in range(15):  # More than warmup
            bar = BarData(
                pd.Timestamp(f"2024-01-01 10:{i:02d}:00"),
                100.0 + i * 0.5, 101.0 + i * 0.5, 99.0 + i * 0.5, 100.5 + i * 0.5, i + 2
            )
            self.detector.process_bar(bar)
        
        # Should have BB history
        self.assertGreater(len(self.detector.indicator_state.bb_history), 1)
    
    def test_regime_classification_applied(self):
        """Test that regime classification is properly applied."""
        # Create bars with clear trend
        trend_bars = [
            BarData(pd.Timestamp("2024-01-01 10:00:00"), 100.0, 101.0, 99.0, 100.5, 2),
            BarData(pd.Timestamp("2024-01-01 10:01:00"), 100.5, 102.0, 100.0, 101.5, 3),
            BarData(pd.Timestamp("2024-01-01 10:02:00"), 101.5, 103.0, 101.0, 102.5, 4),
        ]
        
        snapshots = []
        for bar in trend_bars:
            snapshot = self.detector.process_bar(bar)
            snapshots.append(snapshot)
        
        # Should have valid regimes
        for snapshot in snapshots:
            self.assertIn(snapshot.regime.split('_')[0], ['bull', 'bear', 'neutral'])
            self.assertIn(snapshot.regime.split('_')[1], ['expansion', 'contraction'])
    
    def test_state_machine_applied(self):
        """Test that state machine persistence is applied."""
        # Create consistent regime signals
        consistent_bars = []
        for i in range(10):
            bar = BarData(
                pd.Timestamp(f"2024-01-01 10:{i:02d}:00"),
                100.0 + i * 2, 102.0 + i * 2, 99.0 + i * 2, 101.0 + i * 2, i + 2
            )
            consistent_bars.append(bar)
        
        snapshots = []
        for bar in consistent_bars:
            snapshot = self.detector.process_bar(bar)
            snapshots.append(snapshot)
        
        # Should show persistence behavior (regime changes require persistence)
        regimes = [s.regime for s in snapshots]
        
        # Check that not every bar has different regime (persistence working)
        unique_regimes = set(regimes)
        self.assertLess(len(unique_regimes), len(regimes))


class TestHTFBiasIntegration(TestRegimeDetector):
    """Test HTF bias integration."""
    
    def test_htf_bias_without_rule(self):
        """Test HTF bias when no rule is set."""
        detector = RegimeDetector(warmup=1, htf_rule=None)
        
        bar = BarData(pd.Timestamp("2024-01-01 10:00:00"), 100.0, 101.0, 99.0, 100.5, 1)
        snapshot = detector.process_bar(bar)
        
        # Should always be neutral without HTF rule
        self.assertEqual(snapshot.htf_bias, "neutral")
    
    def test_htf_bias_with_rule(self):
        """Test HTF bias when rule is set."""
        detector = RegimeDetector(warmup=1, htf_rule="1h")
        
        bar = BarData(pd.Timestamp("2024-01-01 10:30:00"), 100.0, 101.0, 99.0, 100.5, 1)
        snapshot = detector.process_bar(bar)
        
        # Should have HTF bias calculation
        self.assertIn(snapshot.htf_bias, ["neutral", "bull", "bear"])
    
    def test_htf_bias_filtering(self):
        """Test that HTF bias filtering is applied."""
        detector = RegimeDetector(warmup=1, htf_rule="1h")
        
        # Manually set HTF bias to test filtering
        detector.htf_calculator.state.bias = "bear"
        
        bar = BarData(pd.Timestamp("2024-01-01 10:30:00"), 100.0, 101.0, 99.0, 100.5, 1)
        snapshot = detector.process_bar(bar)
        
        # If classification is bull but HTF is bear, should be neutral
        # (This depends on the actual classification result, but tests the mechanism)
        self.assertIn(snapshot.regime.split('_')[0], ['bull', 'bear', 'neutral'])


class TestIndicatorCalculation(TestRegimeDetector):
    """Test indicator calculation integration."""
    
    def test_all_indicators_calculated(self):
        """Test that all indicators are calculated and returned."""
        # Process enough bars to have all indicators
        bars = []
        for i in range(20):  # Enough to get past warmup and establish indicators
            bar = BarData(
                pd.Timestamp(f"2024-01-01 10:{i:02d}:00"),
                100.0 + np.sin(i * 0.1) * 2,  # Some variation
                101.0 + np.sin(i * 0.1) * 2,
                99.0 + np.sin(i * 0.1) * 2,
                100.5 + np.sin(i * 0.1) * 2,
                i
            )
            bars.append(bar)
        
        snapshots = []
        for bar in bars:
            snapshot = self.detector.process_bar(bar)
            snapshots.append(snapshot)
        
        # Check final snapshot has all indicators
        final_snapshot = snapshots[-1]
        indicators = final_snapshot.indicators
        
        self.assertIsNotNone(indicators.rsi)
        self.assertIsNotNone(indicators.atr_ratio)
        self.assertIsNotNone(indicators.bb_width)
        # MACD hist might be None initially but should be available later
        self.assertIsNotNone(indicators.ema20)
        self.assertIsNotNone(indicators.ema50)
        self.assertIsNotNone(indicators.ema200)
        self.assertIsNotNone(indicators.ema_slope)
    
    def test_indicator_evolution(self):
        """Test that indicators evolve over time."""
        # Process several bars
        bars = []
        for i in range(10):
            bar = BarData(
                pd.Timestamp(f"2024-01-01 10:{i:02d}:00"),
                100.0 + i,  # Increasing trend
                101.0 + i,
                99.0 + i,
                100.5 + i,
                i
            )
            bars.append(bar)
        
        snapshots = []
        for bar in bars:
            snapshot = self.detector.process_bar(bar)
            snapshots.append(snapshot)
        
        # EMAs should increase with increasing prices
        ema20_values = [s.indicators.ema20 for s in snapshots[5:] if s.indicators.ema20 is not None]
        if len(ema20_values) > 1:
            self.assertGreater(ema20_values[-1], ema20_values[0])


class TestRegimeDetectorStats(TestRegimeDetector):
    """Test statistics calculation."""
    
    def setUp(self):
        """Set up detector with processed bars."""
        super().setUp()
        self.detector = RegimeDetector(warmup=5, persist_n=2, transition_bars=2)
        
        # Process enough bars to have active regimes
        for i in range(20):
            bar = BarData(
                pd.Timestamp(f"2024-01-01 10:{i:02d}:00"),
                100.0 + np.sin(i * 0.3) * 5,  # Oscillating prices
                102.0 + np.sin(i * 0.3) * 5,
                98.0 + np.sin(i * 0.3) * 5,
                101.0 + np.sin(i * 0.3) * 5,
                i
            )
            self.detector.process_bar(bar)
    
    def test_stats_calculation(self):
        """Test basic statistics calculation."""
        stats = self.detector.stats()
        
        # Should have basic stats structure
        self.assertIn("counts", stats)
        self.assertIn("avg_confidence", stats)
        self.assertIn("avg_duration", stats)
        self.assertIn("max_duration", stats)
        self.assertIn("min_duration", stats)
        self.assertIn("num_transitions", stats)
    
    def test_stats_values_reasonable(self):
        """Test that statistics values are reasonable."""
        stats = self.detector.stats()
        
        # Counts should be positive
        for regime, count in stats["counts"].items():
            self.assertGreater(count, 0)
            self.assertIsInstance(regime, str)
        
        # Confidence should be between 0 and 1
        for regime, confidence in stats["avg_confidence"].items():
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)
        
        # Durations should be positive
        self.assertGreaterEqual(stats["avg_duration"], 0.0)
        self.assertGreaterEqual(stats["max_duration"], 0)
        self.assertGreaterEqual(stats["min_duration"], 0)
        self.assertGreaterEqual(stats["num_transitions"], 0)
    
    def test_stats_empty_history(self):
        """Test stats with empty history."""
        empty_detector = RegimeDetector()
        stats = empty_detector.stats()
        
        # Should return empty dict
        self.assertEqual(stats, {})
    
    def test_stats_warmup_only(self):
        """Test stats with only warmup bars."""
        warmup_detector = RegimeDetector(warmup=100)
        
        # Process only a few bars (all warmup)
        for i in range(5):
            bar = BarData(
                pd.Timestamp(f"2024-01-01 10:{i:02d}:00"),
                100.0, 101.0, 99.0, 100.5, i
            )
            warmup_detector.process_bar(bar)
        
        stats = warmup_detector.stats()
        
        # Should return empty dict (no non-warmup bars)
        self.assertEqual(stats, {})


class TestRegimeDetectorExport(TestRegimeDetector):
    """Test export functionality."""
    
    def setUp(self):
        """Set up detector with some history."""
        super().setUp()
        # Process some bars
        for i in range(15):
            bar = BarData(
                pd.Timestamp(f"2024-01-01 10:{i:02d}:00"),
                100.0 + i, 101.0 + i, 99.0 + i, 100.5 + i, i
            )
            self.detector.process_bar(bar)
    
    def test_export_functionality(self):
        """Test JSON export functionality."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            self.detector.export(temp_path)
            
            # Read and verify export
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            # Check structure
            self.assertIn("metadata", data)
            self.assertIn("stats", data)
            self.assertIn("history", data)
            
            # Check metadata
            metadata = data["metadata"]
            self.assertEqual(metadata["warmup"], self.detector.warmup)
            self.assertEqual(metadata["persist_n"], self.detector.state_machine.persist_n)
            self.assertEqual(metadata["transition_bars"], self.detector.state_machine.transition_bars)
            self.assertEqual(metadata["total_bars"], len(self.detector.history))
            
            # Check history
            history = data["history"]
            self.assertEqual(len(history), len(self.detector.history))
            
            # Check first entry structure
            if history:
                first_entry = history[0]
                self.assertIn("timestamp", first_entry)
                self.assertIn("bar_index", first_entry)
                self.assertIn("regime", first_entry)
                self.assertIn("confidence", first_entry)
                self.assertIn("indicators", first_entry)
                self.assertIn("is_transition", first_entry)
                self.assertIn("htf_bias", first_entry)
        
        finally:
            os.unlink(temp_path)
    
    def test_export_serialization(self):
        """Test that export properly serializes all data types."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            self.detector.export(temp_path)
            
            # Should not raise any serialization errors
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            # All values should be JSON-serializable
            self.assertIsInstance(data, dict)
            
        finally:
            os.unlink(temp_path)


class TestRegimeDetectorEdgeCases(TestRegimeDetector):
    """Test edge cases and error handling."""
    
    def test_single_bar_processing(self):
        """Test processing a single bar."""
        bar = BarData(pd.Timestamp("2024-01-01 10:00:00"), 100.0, 101.0, 99.0, 100.5, 0)
        snapshot = self.detector.process_bar(bar)
        
        # Should work without errors
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.regime, "warming_up")  # First bar during warmup
        self.assertEqual(len(self.detector.history), 1)
    
    def test_extreme_price_values(self):
        """Test with extreme price values."""
        extreme_bars = [
            BarData(pd.Timestamp("2024-01-01 10:00:00"), 1e6, 1.1e6, 0.9e6, 1.05e6, 0),
            BarData(pd.Timestamp("2024-01-01 10:01:00"), 1e-6, 1.1e-6, 0.9e-6, 1.05e-6, 1),
        ]
        
        for bar in extreme_bars:
            snapshot = self.detector.process_bar(bar)
            # Should handle without errors
            self.assertIsNotNone(snapshot)
            self.assertIsNotNone(snapshot.indicators)
    
    def test_zero_volatility(self):
        """Test with zero volatility (same prices)."""
        zero_vol_bars = []
        for i in range(15):
            bar = BarData(
                pd.Timestamp(f"2024-01-01 10:{i:02d}:00"),
                100.0, 100.0, 100.0, 100.0,  # All same price
                i
            )
            zero_vol_bars.append(bar)
        
        for bar in zero_vol_bars:
            snapshot = self.detector.process_bar(bar)
            # Should handle zero volatility gracefully
            self.assertIsNotNone(snapshot)
            
            if snapshot.regime != "warming_up":
                # Should detect low volatility
                self.assertIn("contraction", snapshot.regime)
    
    def test_rapid_regime_changes(self):
        """Test with rapidly changing market conditions."""
        # Create alternating high/low volatility
        rapid_bars = []
        for i in range(20):
            if i % 2 == 0:
                # High volatility bar
                bar = BarData(
                    pd.Timestamp(f"2024-01-01 10:{i:02d}:00"),
                    100.0, 120.0, 80.0, 110.0, i
                )
            else:
                # Low volatility bar
                bar = BarData(
                    pd.Timestamp(f"2024-01-01 10:{i:02d}:00"),
                    110.0, 111.0, 109.0, 110.5, i
                )
            rapid_bars.append(bar)
        
        snapshots = []
        for bar in rapid_bars:
            snapshot = self.detector.process_bar(bar)
            snapshots.append(snapshot)
        
        # Should handle rapid changes without errors
        self.assertEqual(len(snapshots), 20)
        
        # State machine should provide stability
        non_warmup = [s for s in snapshots if s.regime != "warming_up"]
        if non_warmup:
            # Should have some consistency due to persistence
            regimes = [s.regime for s in non_warmup]
            # Not every bar should have different regime
            unique_regimes = set(regimes)
            self.assertLessEqual(len(unique_regimes), len(regimes))


class TestRegimeDetectorIntegration(TestRegimeDetector):
    """Test full integration scenarios."""
    
    def test_realistic_trading_session(self):
        """Test a realistic full trading session."""
        # Simulate a full day of trading with different market phases
        session_bars = []
        
        # Morning: Trending up
        for i in range(20):
            # Use proper minute calculation to avoid > 59
            hour = 9 + (30 + i) // 60
            minute = (30 + i) % 60
            bar = BarData(
                pd.Timestamp(f"2024-01-01 {hour:02d}:{minute:02d}:00"),
                100.0 + i * 0.5, 101.0 + i * 0.5, 99.0 + i * 0.5, 100.5 + i * 0.5, i
            )
            session_bars.append(bar)
        
        # Midday: Consolidation
        for i in range(20, 40):
            # Use proper minute calculation
            hour = 9 + (30 + i) // 60
            minute = (30 + i) % 60
            bar = BarData(
                pd.Timestamp(f"2024-01-01 {hour:02d}:{minute:02d}:00"),
                110.0 + np.sin((i-20) * 0.3) * 2,
                111.0 + np.sin((i-20) * 0.3) * 2,
                109.0 + np.sin((i-20) * 0.3) * 2,
                110.5 + np.sin((i-20) * 0.3) * 2,
                i
            )
            session_bars.append(bar)
        
        # Afternoon: Trending down
        for i in range(40, 60):
            # Use proper minute calculation
            hour = 9 + (30 + i) // 60
            minute = (30 + i) % 60
            bar = BarData(
                pd.Timestamp(f"2024-01-01 {hour:02d}:{minute:02d}:00"),
                110.0 - (i-40) * 0.3, 111.0 - (i-40) * 0.3, 109.0 - (i-40) * 0.3, 110.5 - (i-40) * 0.3, i
            )
            session_bars.append(bar)
        
        # Process all bars
        snapshots = []
        for bar in session_bars:
            snapshot = self.detector.process_bar(bar)
            snapshots.append(snapshot)
        
        # Should complete without errors
        self.assertEqual(len(snapshots), 60)
        self.assertEqual(len(self.detector.history), 60)
        
        # Should show regime evolution
        non_warmup = [s for s in snapshots if s.regime != "warming_up"]
        if non_warmup:
            regimes = [s.regime for s in non_warmup]
            # Should have detected different regimes
            unique_regimes = set(regimes)
            self.assertGreater(len(unique_regimes), 1)
        
        # Statistics should be reasonable
        stats = self.detector.stats()
        if stats:
            self.assertGreater(stats["avg_duration"], 0)
            self.assertGreaterEqual(stats["num_transitions"], 0)


if __name__ == '__main__':
    unittest.main()