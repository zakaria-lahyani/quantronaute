import pytest
import pandas as pd
import numpy as np
from app.indicators.incremental.macd import MACD
from tests.indicators.reader import load_test_data

FILENAME = "history.csv"
TOLERANCES = {
    "mean": 1e-6,
    "max": 1e-5,
}


@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)


def test_macd_update_matches_batch(loaded_data):
    df = loaded_data.copy()
    prices = df["close"]
    fast = 3
    slow = 5
    signal = 3

    macd_obj = MACD(fast, slow, signal)

    macd_lines = []
    signal_lines = []
    histograms = []

    # Step-by-step incremental update
    for price in prices:
        macd_line, signal_line, hist = macd_obj.update(price)
        macd_lines.append(macd_line)
        signal_lines.append(signal_line)
        histograms.append(hist)

    macd_lines = np.array(macd_lines)
    signal_lines = np.array(signal_lines)
    histograms = np.array(histograms)

    # Batch update
    batch_macd_line, batch_signal_line, batch_hist = MACD(fast, slow, signal).batch_update(prices.to_numpy())


    # Compare results (allow small numerical tolerance)
    assert np.allclose(macd_lines[~np.isnan(macd_lines)], batch_macd_line[~np.isnan(batch_macd_line)], atol=1e-6), "MACD line mismatch"
    assert np.allclose(signal_lines[~np.isnan(signal_lines)], batch_signal_line[~np.isnan(batch_signal_line)], atol=1e-6), "Signal line mismatch"
    assert np.allclose(histograms[~np.isnan(histograms)], batch_hist[~np.isnan(batch_hist)], atol=1e-6), "Histogram mismatch"

    print("Test passed: Incremental and batch MACD calculations match closely.")
