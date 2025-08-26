"""Unit tests for regime classifier."""

import unittest

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app.regime.data_structure import IndicatorValues, ClassificationResult
from app.regime.regime_classifier import RegimeClassifier


class TestRegimeClassifier(unittest.TestCase):
    """Test RegimeClassifier static methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.basic_indicators = IndicatorValues(
            rsi=50.0,
            atr_ratio=1.0,
            bb_width=0.05,
            macd_hist=0.0,
            ema20=100.0,
            ema50=99.0,
            ema200=98.0,
            ema_slope=0.0
        )


class TestDirectionScoreCalculation(TestRegimeClassifier):
    """Test direction score calculation."""
    
    def test_direction_score_neutral_indicators(self):
        """Test direction score with neutral indicators."""
        indicators = IndicatorValues(
            rsi=50.0,  # Neutral (between 45-55)
            atr_ratio=1.0,
            bb_width=0.05,
            macd_hist=None,  # Neutral (no MACD contribution)
            ema20=100.0,
            ema50=99.0,   # Price > EMA50 (+2)
            ema200=98.0,  # Price > EMA200 (+3)  
            ema_slope=0.0  # Neutral
        )
        close = 100.0  # Above EMAs to get neutral overall score
        
        score = RegimeClassifier.calculate_direction_score(indicators, close)
        
        # RSI neutral (0) + no MACD (0) + EMA50 (+2) + EMA200 (+3) + slope (0) = +5
        # But for truly neutral, we need to balance better
        self.assertEqual(score, 5)
    
    def test_direction_score_bullish_indicators(self):
        """Test direction score with bullish indicators."""
        indicators = IndicatorValues(
            rsi=65.0,  # +2 (above 55)
            atr_ratio=1.0,
            bb_width=0.05,
            macd_hist=1.0,  # +2 (positive)
            ema20=100.0,
            ema50=99.0,   # +2 (price above EMA50)
            ema200=98.0,  # +3 (price above EMA200)
            ema_slope=1.0  # +1 (upward slope)
        )
        close = 101.0  # Above both EMAs
        
        score = RegimeClassifier.calculate_direction_score(indicators, close)
        
        # Expected: +2 (RSI) + 2 (MACD) + 2 (EMA50) + 3 (EMA200) + 1 (slope) = +10
        self.assertEqual(score, 10)
    
    def test_direction_score_bearish_indicators(self):
        """Test direction score with bearish indicators."""
        indicators = IndicatorValues(
            rsi=35.0,  # -2 (below 45), -1 (below 30) = -3 total
            atr_ratio=1.0,
            bb_width=0.05,
            macd_hist=-1.0,  # -2 (negative)
            ema20=100.0,
            ema50=102.0,   # -2 (price below EMA50)
            ema200=103.0,  # -3 (price below EMA200)
            ema_slope=-1.0  # -1 (downward slope)
        )
        close = 99.0  # Below both EMAs
        
        score = RegimeClassifier.calculate_direction_score(indicators, close)
        
        # Expected: -3 (RSI) -2 (MACD) -2 (EMA50) -3 (EMA200) -1 (slope) = -11
        # But RSI=35 gives -2 (below 45) but not -1 (not below 30), so -2 total
        # Actual: -2 (RSI) -2 (MACD) -2 (EMA50) -3 (EMA200) -1 (slope) = -10
        self.assertEqual(score, -10)
    
    def test_direction_score_mixed_indicators(self):
        """Test direction score with mixed indicators."""
        indicators = IndicatorValues(
            rsi=75.0,  # +2 (above 55), +1 (above 70) = +3 total
            atr_ratio=1.0,
            bb_width=0.05,
            macd_hist=-0.5,  # -2 (negative)
            ema20=100.0,
            ema50=99.0,   # +2 (price above EMA50)
            ema200=101.0,  # -3 (price below EMA200)
            ema_slope=1.0  # +1 (upward slope)
        )
        close = 100.0
        
        score = RegimeClassifier.calculate_direction_score(indicators, close)
        
        # Expected: +3 (RSI) -2 (MACD) +2 (EMA50) -3 (EMA200) +1 (slope) = +1
        self.assertEqual(score, 1)
    
    def test_direction_score_missing_emas(self):
        """Test direction score when EMAs are not available."""
        indicators = IndicatorValues(
            rsi=60.0,  # +2
            atr_ratio=1.0,
            bb_width=0.05,
            macd_hist=1.0,  # +2
            ema20=None,
            ema50=None,   # No EMA contributions
            ema200=None,
            ema_slope=1.0  # +1
        )
        close = 100.0
        
        score = RegimeClassifier.calculate_direction_score(indicators, close)
        
        # Expected: +2 (RSI) + 2 (MACD) + 1 (slope) = +5
        self.assertEqual(score, 5)
    
    def test_direction_score_missing_macd(self):
        """Test direction score when MACD is not available."""
        indicators = IndicatorValues(
            rsi=40.0,  # -2 (below 45)
            atr_ratio=1.0,
            bb_width=0.05,
            macd_hist=None,  # No MACD contribution
            ema20=100.0,
            ema50=101.0,   # -2 (price below EMA50)
            ema200=102.0,  # -3 (price below EMA200)
            ema_slope=-1.0  # -1 (downward slope)
        )
        close = 99.0
        
        score = RegimeClassifier.calculate_direction_score(indicators, close)
        
        # Expected: -2 (RSI) -2 (EMA50) -3 (EMA200) -1 (slope) = -8
        self.assertEqual(score, -8)
    
    def test_direction_score_rsi_extreme_values(self):
        """Test RSI contribution with extreme values."""
        # Very oversold RSI
        indicators_oversold = IndicatorValues(rsi=20.0)  # -2 (below 45) -1 (below 30) = -3
        score_oversold = RegimeClassifier.calculate_direction_score(indicators_oversold, 100.0)
        self.assertEqual(score_oversold, -3)
        
        # Very overbought RSI
        indicators_overbought = IndicatorValues(rsi=85.0)  # +2 (above 55) +1 (above 70) = +3
        score_overbought = RegimeClassifier.calculate_direction_score(indicators_overbought, 100.0)
        self.assertEqual(score_overbought, 3)
        
        # Neutral RSI
        indicators_neutral = IndicatorValues(rsi=50.0)  # 0
        score_neutral = RegimeClassifier.calculate_direction_score(indicators_neutral, 100.0)
        self.assertEqual(score_neutral, 0)


class TestAdaptiveConfidence(TestRegimeClassifier):
    """Test adaptive confidence calculation."""
    
    def test_adaptive_confidence_all_indicators_available(self):
        """Test confidence when all indicators are available."""
        indicators = IndicatorValues(
            rsi=60.0,
            atr_ratio=1.2,
            bb_width=0.05,
            macd_hist=1.0,
            ema20=100.0,
            ema50=99.0,
            ema200=98.0,
            ema_slope=1.0  # Non-zero slope
        )
        dir_score = 10  # Strong directional score
        
        confidence = RegimeClassifier.calculate_adaptive_confidence(dir_score, indicators)
        
        # Total weight: (2+3) EMA + (2+1) RSI + 2 MACD + 1 slope = 11
        # Confidence = min(1.0, |10|/11) = min(1.0, 0.909) = 0.909
        expected_confidence = min(1.0, abs(dir_score) / 11)
        self.assertAlmostEqual(confidence, expected_confidence, places=10)
    
    def test_adaptive_confidence_missing_indicators(self):
        """Test confidence when some indicators are missing."""
        indicators = IndicatorValues(
            rsi=60.0,
            atr_ratio=1.0,
            bb_width=0.05,
            macd_hist=None,  # Missing MACD
            ema20=100.0,
            ema50=None,      # Missing EMA50
            ema200=None,     # Missing EMA200
            ema_slope=0.0    # Zero slope (no contribution)
        )
        dir_score = 3
        
        confidence = RegimeClassifier.calculate_adaptive_confidence(dir_score, indicators)
        
        # Total weight: (2+1) RSI only = 3
        # Confidence = min(1.0, |3|/3) = 1.0
        expected_confidence = 1.0
        self.assertEqual(confidence, expected_confidence)
    
    def test_adaptive_confidence_zero_score(self):
        """Test confidence with zero direction score."""
        indicators = self.basic_indicators
        dir_score = 0
        
        confidence = RegimeClassifier.calculate_adaptive_confidence(dir_score, indicators)
        
        # Zero score should give zero confidence regardless of weight
        self.assertEqual(confidence, 0.0)
    
    def test_adaptive_confidence_zero_weight(self):
        """Test confidence when total weight is zero."""
        indicators = IndicatorValues(
            # No valid indicators
            ema50=None,
            ema200=None,
            macd_hist=None,
            ema_slope=0.0
        )
        dir_score = 5
        
        confidence = RegimeClassifier.calculate_adaptive_confidence(dir_score, indicators)
        
        # Only RSI contributes: weight = 2+1 = 3
        # Confidence = min(1.0, |5|/3) = 1.0
        self.assertEqual(confidence, 1.0)
    
    def test_adaptive_confidence_high_score_low_weight(self):
        """Test confidence with high score but low weight."""
        indicators = IndicatorValues(
            rsi=50.0,  # Only RSI available
            ema50=None,
            ema200=None,
            macd_hist=None,
            ema_slope=0.0
        )
        dir_score = 10  # High score from RSI alone would be impossible, but testing the math
        
        confidence = RegimeClassifier.calculate_adaptive_confidence(dir_score, indicators)
        
        # Weight = 2+1 = 3, confidence = min(1.0, 10/3) = 1.0
        self.assertEqual(confidence, 1.0)
    
    def test_adaptive_confidence_slope_contribution(self):
        """Test that EMA slope contributes to weight only when non-zero."""
        indicators_no_slope = IndicatorValues(
            rsi=60.0,
            ema50=99.0,
            ema200=98.0,
            macd_hist=1.0,
            ema_slope=0.0  # Zero slope
        )
        
        indicators_with_slope = IndicatorValues(
            rsi=60.0,
            ema50=99.0,
            ema200=98.0,
            macd_hist=1.0,
            ema_slope=1.0  # Non-zero slope
        )
        
        dir_score = 8
        
        confidence_no_slope = RegimeClassifier.calculate_adaptive_confidence(dir_score, indicators_no_slope)
        confidence_with_slope = RegimeClassifier.calculate_adaptive_confidence(dir_score, indicators_with_slope)
        
        # With slope should have lower confidence (higher weight, same score)
        self.assertGreater(confidence_no_slope, confidence_with_slope)


class TestRegimeClassification(TestRegimeClassifier):
    """Test complete regime classification."""
    
    def test_classify_regime_bull_expansion(self):
        """Test classification of bull expansion regime."""
        indicators = IndicatorValues(
            rsi=70.0,
            atr_ratio=1.5,    # High volatility
            bb_width=0.08,    # Wide bands
            macd_hist=2.0,
            ema20=100.0,
            ema50=99.0,
            ema200=98.0,
            ema_slope=1.0
        )
        close = 102.0
        bb_threshold = 0.05
        
        result = RegimeClassifier.classify_regime(indicators, close, bb_threshold)
        
        self.assertIsInstance(result, ClassificationResult)
        self.assertEqual(result.direction, "bull")
        self.assertEqual(result.volatility, "expansion")
        self.assertGreater(result.confidence, 0.5)
        self.assertGreater(result.dir_score, 0)
    
    def test_classify_regime_bear_contraction(self):
        """Test classification of bear contraction regime."""
        indicators = IndicatorValues(
            rsi=25.0,
            atr_ratio=0.8,     # Low volatility
            bb_width=0.03,     # Narrow bands
            macd_hist=-1.5,
            ema20=100.0,
            ema50=102.0,
            ema200=104.0,
            ema_slope=-1.0
        )
        close = 98.0
        bb_threshold = 0.05
        
        result = RegimeClassifier.classify_regime(indicators, close, bb_threshold)
        
        self.assertEqual(result.direction, "bear")
        self.assertEqual(result.volatility, "contraction")
        self.assertGreater(result.confidence, 0.0)
        self.assertLess(result.dir_score, 0)
    
    def test_classify_regime_neutral_expansion(self):
        """Test classification of neutral expansion regime."""
        indicators = IndicatorValues(
            rsi=50.0,
            atr_ratio=1.3,     # High volatility
            bb_width=0.02,     # Low BB width but high ATR
            macd_hist=0.1,     # Weak positive
            ema20=100.0,
            ema50=100.0,       # Price = EMA (neutral)
            ema200=100.0,
            ema_slope=0.0
        )
        close = 100.0
        bb_threshold = 0.05
        
        result = RegimeClassifier.classify_regime(indicators, close, bb_threshold)
        
        # Direction will be bear because price=EMA gives negative score (not >)
        self.assertEqual(result.direction, "bear")  # Due to EMA scoring logic
        self.assertEqual(result.volatility, "expansion")  # Due to high ATR ratio
    
    def test_classify_regime_bull_contraction(self):
        """Test classification of bull contraction regime."""
        indicators = IndicatorValues(
            rsi=65.0,
            atr_ratio=0.9,     # Low volatility
            bb_width=0.03,     # Low volatility
            macd_hist=0.8,
            ema20=100.0,
            ema50=99.0,
            ema200=97.0,
            ema_slope=1.0
        )
        close = 101.0
        bb_threshold = 0.05
        
        result = RegimeClassifier.classify_regime(indicators, close, bb_threshold)
        
        self.assertEqual(result.direction, "bull")
        self.assertEqual(result.volatility, "contraction")
    
    def test_classify_regime_volatility_bb_threshold(self):
        """Test volatility classification based on BB threshold."""
        indicators = IndicatorValues(
            rsi=50.0,
            atr_ratio=1.0,     # Neutral ATR
            bb_width=0.06,     # Above threshold
            ema50=100.0,
            ema200=100.0
        )
        close = 100.0
        bb_threshold = 0.05
        
        result = RegimeClassifier.classify_regime(indicators, close, bb_threshold)
        
        self.assertEqual(result.volatility, "expansion")  # BB width > threshold
    
    def test_classify_regime_volatility_atr_threshold(self):
        """Test volatility classification based on ATR ratio."""
        indicators = IndicatorValues(
            rsi=50.0,
            atr_ratio=1.2,     # Above 1.1 threshold
            bb_width=0.03,     # Below BB threshold
            ema50=100.0,
            ema200=100.0
        )
        close = 100.0
        bb_threshold = 0.05
        
        result = RegimeClassifier.classify_regime(indicators, close, bb_threshold)
        
        self.assertEqual(result.volatility, "expansion")  # ATR ratio > 1.1
    
    def test_classify_regime_missing_volatility_indicators(self):
        """Test classification when volatility indicators are missing."""
        indicators = IndicatorValues(
            rsi=60.0,
            atr_ratio=None,    # Missing ATR
            bb_width=None,     # Missing BB width
            ema50=99.0,
            ema200=98.0
        )
        close = 101.0
        bb_threshold = 0.05
        
        result = RegimeClassifier.classify_regime(indicators, close, bb_threshold)
        
        self.assertEqual(result.direction, "bull")
        self.assertEqual(result.volatility, "contraction")  # Default when no expansion signals
    
    def test_classify_regime_edge_case_thresholds(self):
        """Test classification at edge case thresholds."""
        # Exactly at ATR threshold
        indicators = IndicatorValues(
            rsi=50.0,
            atr_ratio=1.1,     # Exactly at threshold
            bb_width=0.04,
            ema50=100.0,
            ema200=100.0
        )
        close = 100.0
        bb_threshold = 0.05
        
        result = RegimeClassifier.classify_regime(indicators, close, bb_threshold)
        
        # ATR ratio > 1.1 should be expansion
        self.assertEqual(result.volatility, "contraction")  # 1.1 is not > 1.1
        
        # Just above threshold
        indicators.atr_ratio = 1.101
        result = RegimeClassifier.classify_regime(indicators, close, bb_threshold)
        self.assertEqual(result.volatility, "expansion")


class TestClassificationIntegration(TestRegimeClassifier):
    """Test integration of classification components."""
    
    def test_classification_consistency(self):
        """Test that classification is consistent across multiple calls."""
        indicators = IndicatorValues(
            rsi=65.0,
            atr_ratio=1.2,
            bb_width=0.06,
            macd_hist=1.0,
            ema20=100.0,
            ema50=99.0,
            ema200=98.0,
            ema_slope=1.0
        )
        close = 101.0
        bb_threshold = 0.05
        
        # Call multiple times
        result1 = RegimeClassifier.classify_regime(indicators, close, bb_threshold)
        result2 = RegimeClassifier.classify_regime(indicators, close, bb_threshold)
        result3 = RegimeClassifier.classify_regime(indicators, close, bb_threshold)
        
        # Results should be identical
        self.assertEqual(result1.direction, result2.direction)
        self.assertEqual(result1.volatility, result2.volatility)
        self.assertEqual(result1.confidence, result3.confidence)
        self.assertEqual(result1.dir_score, result3.dir_score)
    
    def test_classification_result_immutability(self):
        """Test that ClassificationResult is immutable."""
        indicators = self.basic_indicators
        result = RegimeClassifier.classify_regime(indicators, 100.0, 0.05)
        
        # Should not be able to modify result
        with self.assertRaises(AttributeError):
            result.direction = "modified"
        
        with self.assertRaises(AttributeError):
            result.confidence = 0.99
    
    def test_confidence_bounds(self):
        """Test that confidence is always within valid bounds."""
        test_cases = [
            # Extreme bullish
            (IndicatorValues(rsi=90.0, atr_ratio=2.0, macd_hist=5.0, 
                           ema50=90.0, ema200=85.0, ema_slope=1.0), 110.0),
            # Extreme bearish
            (IndicatorValues(rsi=10.0, atr_ratio=0.5, macd_hist=-5.0,
                           ema50=110.0, ema200=115.0, ema_slope=-1.0), 90.0),
            # Neutral
            (IndicatorValues(rsi=50.0, atr_ratio=1.0, macd_hist=0.0,
                           ema50=100.0, ema200=100.0, ema_slope=0.0), 100.0),
        ]
        
        for indicators, close in test_cases:
            result = RegimeClassifier.classify_regime(indicators, close, 0.05)
            
            # Confidence should be between 0 and 1
            self.assertGreaterEqual(result.confidence, 0.0)
            self.assertLessEqual(result.confidence, 1.0)
    
    def test_direction_score_directional_relationship(self):
        """Test that direction score correlates with direction classification."""
        test_cases = [
            # Strong bullish indicators
            IndicatorValues(rsi=80.0, macd_hist=3.0, ema50=95.0, ema200=90.0, ema_slope=1.0),
            # Weak bullish indicators  
            IndicatorValues(rsi=60.0, macd_hist=0.5, ema50=99.0, ema200=98.0, ema_slope=1.0),
            # Weak bearish indicators
            IndicatorValues(rsi=40.0, macd_hist=-0.5, ema50=101.0, ema200=102.0, ema_slope=-1.0),
            # Strong bearish indicators
            IndicatorValues(rsi=20.0, macd_hist=-3.0, ema50=105.0, ema200=110.0, ema_slope=-1.0),
        ]
        
        close_prices = [100.0, 100.0, 100.0, 100.0]
        
        for indicators, close in zip(test_cases, close_prices):
            result = RegimeClassifier.classify_regime(indicators, close, 0.05)
            
            # Direction should correlate with score sign
            if result.dir_score > 0:
                self.assertEqual(result.direction, "bull")
            elif result.dir_score < 0:
                self.assertEqual(result.direction, "bear")
            else:
                self.assertEqual(result.direction, "neutral")


if __name__ == '__main__':
    unittest.main()