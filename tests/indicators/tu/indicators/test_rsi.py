import pytest
import pandas as pd
import numpy as np
from app.indicators.incremental.rsi import RSI
from tests.indicators.reader import load_test_data

FILENAME = "history.csv"
TOLERANCES = {
    "mean": 1e-6,
    "max": 1e-5,
}


@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)

def test_rsi_update_matches_batch(loaded_data):
    df = loaded_data.copy()
    prices = df["close"].values

    period = 14
    signal_period = 9
    rsi_obj = RSI(period, signal_period)

    rsi_list = []
    signal_list = []

    # Incremental step-by-step updates
    for price in prices:
        res = rsi_obj.update(price)
        if res is None:
            rsi_list.append(np.nan)
            signal_list.append(np.nan)
        else:
            rsi_val, signal_val = res
            rsi_list.append(rsi_val)
            signal_list.append(signal_val)

    rsi_list = np.array(rsi_list)
    signal_list = np.array(signal_list)

    # Batch update
    rsi_obj_batch = RSI(period, signal_period)
    rsi_batch, signal_batch = rsi_obj_batch.batch_update(prices)

    # Find indices where both incremental and batch have valid numbers
    valid_idx = ~np.isnan(rsi_list) & ~np.isnan(rsi_batch) & ~np.isnan(signal_list) & ~np.isnan(signal_batch)

    mean_diff_rsi = np.mean(np.abs(rsi_list[valid_idx] - rsi_batch[valid_idx]))
    max_diff_rsi = np.max(np.abs(rsi_list[valid_idx] - rsi_batch[valid_idx]))

    mean_diff_signal = np.mean(np.abs(signal_list[valid_idx] - signal_batch[valid_idx]))
    max_diff_signal = np.max(np.abs(signal_list[valid_idx] - signal_batch[valid_idx]))

    assert mean_diff_rsi < TOLERANCES["mean"], f"Mean RSI difference too high: {mean_diff_rsi}"
    assert max_diff_rsi < TOLERANCES["max"], f"Max RSI difference too high: {max_diff_rsi}"

    assert mean_diff_signal < TOLERANCES["mean"], f"Mean RSI signal difference too high: {mean_diff_signal}"
    assert max_diff_signal < TOLERANCES["max"], f"Max RSI signal difference too high: {max_diff_signal}"
