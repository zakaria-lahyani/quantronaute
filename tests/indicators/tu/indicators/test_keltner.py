

import pytest
import pandas as pd
import numpy as np
from app.indicators.incremental.keltner_channel import KeltnerChannel
from tests.indicators.reader import load_test_data

FILENAME = "history.csv"
TOLERANCES = {
    "mean": 1e-6,
    "max": 1e-5,
}


@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)


def test_keltner_update_matches_batch(loaded_data):
    df = loaded_data.copy()
    highs = df["high"]
    lows = df["low"]
    closes = df["close"]

    # Params
    ema_window = 5
    atr_window = 3
    multiplier = 2

    # Batch calculation
    kc = KeltnerChannel(ema_window, atr_window, multiplier)
    batch_upper, batch_middle, batch_lower, batch_percent_k = kc.batch_update(highs, lows, closes)

    # Step-by-step calculation
    kc_step = KeltnerChannel(ema_window, atr_window, multiplier)
    step_upper, step_middle, step_lower, step_percent_k = [], [], [], []

    for h, l, c in zip(highs, lows, closes):
        u, m, lo, pk = kc_step.update(h, l, c)
        step_upper.append(u)
        step_middle.append(m)
        step_lower.append(lo)
        step_percent_k.append(pk)

    # Convert to np arrays for comparison
    batch_upper = np.array(batch_upper)
    batch_middle = np.array(batch_middle)
    batch_lower = np.array(batch_lower)
    batch_percent_k = np.array(batch_percent_k)

    step_upper = np.array(step_upper, dtype=np.float64)
    step_middle = np.array(step_middle, dtype=np.float64)
    step_lower = np.array(step_lower, dtype=np.float64)
    step_percent_k = np.array(step_percent_k, dtype=np.float64)

    # Mask invalid (None) values before comparing
    def mask_valid(a, b):
        valid = (~np.isnan(a)) & (~np.isnan(b))
        return a[valid], b[valid]

    for name, batch_arr, step_arr in [
        ("upper", batch_upper, step_upper),
        ("middle", batch_middle, step_middle),
        ("lower", batch_lower, step_lower),
        ("%K", batch_percent_k, step_percent_k),
    ]:
        b_vals, s_vals = mask_valid(batch_arr, step_arr)
        assert np.allclose(b_vals, s_vals, atol=1e-8), f"{name} band mismatch"
