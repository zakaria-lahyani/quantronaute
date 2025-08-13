import pytest
import numpy as np
import pandas as pd
from tests.indicators.reader import load_test_data

# Import batch indicators - only the ones that exist as standalone functions
from app.indicators.batch.sma import sma_batch
from app.indicators.batch.ema import ema_numba
from app.indicators.batch.rsi import rsi_batch
from app.indicators.batch.macd import macd_batch_update
from app.indicators.batch.bollinger_bands import bollinger_bands_batch
from app.indicators.batch.atr import compute_true_range, compute_atr
from app.indicators.batch.sar import sar_batch
from app.indicators.batch.ultimate_rsi import ultimate_rsi_batch
from app.indicators.batch.keltner_channel import keltner_channel_batch

FILENAME = "history.csv"


@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)


class TestBatchIndicators:
    
    def test_sma_batch(self, loaded_data):
        df = loaded_data.copy()
        close = df["close"].values
        
        # Test different periods
        for period in [5, 10, 20]:
            result = sma_batch(close, period)
            
            # Check output shape
            assert len(result) == len(close)
            
            # Check NaN values for initial period
            assert np.all(np.isnan(result[:period-1]))
            
            # Verify calculation for a few points
            for i in range(period, min(period + 5, len(close))):
                expected = np.mean(close[i-period+1:i+1])
                assert np.isclose(result[i], expected)
    
    def test_ema_batch(self, loaded_data):
        df = loaded_data.copy()
        close = df["close"].values
        
        for period in [5, 12, 26]:
            result = ema_numba(close, period)
            
            # Check output shape
            assert len(result) == len(close)
            
            # Check that EMA starts from first value
            assert not np.isnan(result[0])
            
            # EMA should be smooth
            for i in range(1, len(result)):
                if not np.isnan(result[i]) and not np.isnan(result[i-1]):
                    # EMA should not jump too much
                    change_pct = abs(result[i] - result[i-1]) / result[i-1] if result[i-1] != 0 else 0
                    assert change_pct < 0.5  # Less than 50% change
    
    def test_rsi_batch(self, loaded_data):
        df = loaded_data.copy()
        close = df["close"].values
        
        for period in [7, 14, 21]:
            result = rsi_batch(close, period)
            
            # Check output shape
            assert len(result) == len(close)
            
            # RSI should be between 0 and 100
            valid_results = result[~np.isnan(result)]
            if len(valid_results) > 0:
                assert np.all(valid_results >= 0)
                assert np.all(valid_results <= 100)
    
    def test_macd_batch(self, loaded_data):
        df = loaded_data.copy()
        close = df["close"].values
        
        fast, slow, signal = 12, 26, 9
        macd_line, signal_line, histogram = macd_batch_update(close, fast, slow, signal)
        
        # Check output shapes
        assert len(macd_line) == len(close)
        assert len(signal_line) == len(close)
        assert len(histogram) == len(close)
        
        # Histogram should be MACD - Signal
        valid_idx = ~np.isnan(histogram) & ~np.isnan(macd_line) & ~np.isnan(signal_line)
        if np.any(valid_idx):
            assert np.allclose(histogram[valid_idx], macd_line[valid_idx] - signal_line[valid_idx])
    
    def test_bollinger_bands_batch(self, loaded_data):
        df = loaded_data.copy()
        close = df["close"].values
        
        window, num_std = 20, 2
        upper, middle, lower, percent_b = bollinger_bands_batch(close, window, num_std)
        
        # Check output shapes
        assert len(upper) == len(close)
        assert len(middle) == len(close)
        assert len(lower) == len(close)
        assert len(percent_b) == len(close)
        
        # Check band relationships
        valid_idx = ~np.isnan(upper)
        if np.any(valid_idx):
            assert np.all(upper[valid_idx] >= middle[valid_idx])
            assert np.all(middle[valid_idx] >= lower[valid_idx])
            
            # Check percent_b calculation
            expected_percent_b = (close[valid_idx] - lower[valid_idx]) / (upper[valid_idx] - lower[valid_idx])
            # Handle division by zero
            expected_percent_b = np.where(
                upper[valid_idx] != lower[valid_idx],
                expected_percent_b,
                0.0
            )
            assert np.allclose(percent_b[valid_idx], expected_percent_b)
    
    def test_atr_batch(self, loaded_data):
        df = loaded_data.copy()
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        
        for period in [7, 14]:
            # Compute true range first
            tr = compute_true_range(high, low, close)
            # Then compute ATR
            result = compute_atr(tr, period)
            
            # Check output shape
            assert len(result) == len(high)
            
            # ATR should be positive
            valid_results = result[~np.isnan(result)]
            if len(valid_results) > 0:
                assert np.all(valid_results >= 0)
                
                # ATR should be less than the maximum daily range
                max_range = np.max(high - low)
                assert np.all(valid_results <= max_range * 2)  # Some buffer for gaps
    
    def test_sar_batch(self, loaded_data):
        df = loaded_data.copy()
        high = df["high"].values
        low = df["low"].values
        
        # SAR requires acceleration parameters
        sar = sar_batch(high, low, 0.02, 0.2)  # Default SAR parameters
        
        # Check output shape
        assert len(sar) == len(high)
        
        # SAR should be within the range of high and low (with some buffer for acceleration)
        valid_idx = ~np.isnan(sar)
        if np.any(valid_idx):
            min_price = np.min(low)
            max_price = np.max(high)
            assert np.all(sar[valid_idx] >= min_price * 0.9)
            assert np.all(sar[valid_idx] <= max_price * 1.1)
    
    def test_keltner_channel_batch(self, loaded_data):
        df = loaded_data.copy()
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        
        ema_window, atr_window, multiplier = 20, 10, 2
        upper, middle, lower, percent_k = keltner_channel_batch(
            high, low, close, ema_window, atr_window, multiplier
        )
        
        # Check output shapes
        assert len(upper) == len(high)
        assert len(middle) == len(high)
        assert len(lower) == len(high)
        assert len(percent_k) == len(high)
        
        # Check channel relationships
        valid_idx = ~np.isnan(upper)
        if np.any(valid_idx):
            assert np.all(upper[valid_idx] >= middle[valid_idx])
            assert np.all(middle[valid_idx] >= lower[valid_idx])
    
    def test_ultimate_rsi_batch(self, loaded_data):
        df = loaded_data.copy()
        
        length, smooth_length = 14, 14
        # ultimate_rsi_batch takes prices array, not DataFrame
        ursi, signal = ultimate_rsi_batch(df['close'].values, length, smooth_length)
        
        # Check output shapes
        assert len(ursi) == len(df)
        assert len(signal) == len(df)
        
        # URSI and signal should be between reasonable bounds
        valid_ursi = ursi[~np.isnan(ursi)]
        valid_signal = signal[~np.isnan(signal)]
        
        if len(valid_ursi) > 0:
            # Ultimate RSI can go outside 0-100 range but should be reasonable
            assert np.all(valid_ursi >= -50)
            assert np.all(valid_ursi <= 150)
        
        if len(valid_signal) > 0:
            assert np.all(valid_signal >= -50)
            assert np.all(valid_signal <= 150)


class TestBatchIndicatorEdgeCases:
    
    def test_empty_input(self):
        empty_array = np.array([])
        
        # Test that functions handle empty input gracefully
        result = sma_batch(empty_array, 10)
        assert len(result) == 0
        
        result = ema_numba(empty_array, 10)
        assert len(result) == 0
    
    def test_single_value_input(self):
        single_value = np.array([100.0])
        
        result = sma_batch(single_value, 10)
        assert len(result) == 1
        assert np.isnan(result[0])  # Not enough data for SMA
        
        result = ema_numba(single_value, 10)
        assert len(result) == 1
        assert result[0] == 100.0  # EMA starts from first value
    
    def test_constant_values(self):
        constant = np.array([100.0] * 50)
        
        # SMA of constant should be the constant
        result = sma_batch(constant, 10)
        valid = result[~np.isnan(result)]
        assert np.allclose(valid, 100.0)
        
        # RSI of constant should handle no price changes
        result = rsi_batch(constant, 14)
        # When price doesn't change, RSI implementation might return NaN or specific value
        # Just check it doesn't crash
        assert len(result) == len(constant)
        
        # Bollinger Bands of constant
        upper, middle, lower, percent_b = bollinger_bands_batch(constant, 20, 2)
        valid_idx = ~np.isnan(middle)
        if np.any(valid_idx):
            assert np.allclose(middle[valid_idx], 100.0)
            # With no volatility, bands should collapse to middle
            assert np.allclose(upper[valid_idx], 100.0, atol=1e-10)
            assert np.allclose(lower[valid_idx], 100.0, atol=1e-10)