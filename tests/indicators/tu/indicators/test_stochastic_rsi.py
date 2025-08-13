import pytest
import numpy as np
import pandas as pd
from app.indicators.incremental.stochastic_rsi import StochasticRSI
from test.reader import load_test_data

FILENAME = "history.csv"
TOLERANCES = {
    "mean": 1e-6,
    "max": 1e-5,
}

@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)

def test_stochrsi_update_matches_batch(loaded_data):
    df = loaded_data.copy()
    prices = df["close"].values

    rsi_period = 14
    stochrsi_period = 14
    k_smooth = 3
    d_smooth = 3

    stochrsi_obj = StochasticRSI(rsi_period, stochrsi_period, k_smooth, d_smooth)

    k_step, d_step = [], []
    for price in prices:
        k_val, d_val = stochrsi_obj.update(price)
        k_step.append(np.nan if k_val is None else k_val)
        d_step.append(np.nan if d_val is None else d_val)
    k_step = np.array(k_step, dtype=np.float64)
    d_step = np.array(d_step, dtype=np.float64)

    stochrsi_obj_batch = StochasticRSI(rsi_period, stochrsi_period, k_smooth, d_smooth)
    k_batch, d_batch = stochrsi_obj_batch.batch_update(prices)

    valid_k = ~np.isnan(k_step)
    valid_d = ~np.isnan(d_step)

    assert np.any(valid_k), "No valid %K values to compare"
    assert np.any(valid_d), "No valid %D values to compare"

    mean_diff_k = np.mean(np.abs(k_step[valid_k] - k_batch[valid_k]))
    max_diff_k = np.max(np.abs(k_step[valid_k] - k_batch[valid_k]))

    mean_diff_d = np.mean(np.abs(d_step[valid_d] - d_batch[valid_d]))
    max_diff_d = np.max(np.abs(d_step[valid_d] - d_batch[valid_d]))

    assert mean_diff_k < TOLERANCES["mean"], f"Mean %K difference too high: {mean_diff_k}"
    assert max_diff_k < TOLERANCES["max"], f"Max %K difference too high: {max_diff_k}"
    assert mean_diff_d < TOLERANCES["mean"], f"Mean %D difference too high: {mean_diff_d}"
    assert max_diff_d < TOLERANCES["max"], f"Max %D difference too high: {max_diff_d}"
