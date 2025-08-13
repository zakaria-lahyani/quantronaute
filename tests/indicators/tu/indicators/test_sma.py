import pytest
import numpy as np
import pandas as pd
from app.indicators.incremental.sma import SMA
from test.reader import load_test_data

FILENAME = "history.csv"
TOLERANCES = {
    "mean": 1e-9,
    "max": 1e-8,
}

@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)

def test_sma_update_matches_batch(loaded_data):
    df = loaded_data.copy()
    prices = df["close"].values

    period = 14

    sma_obj = SMA(period)

    sma_step = []
    for val in prices:
        sma_val = sma_obj.update(val)
        # Convert None to np.nan for numpy compatibility
        if sma_val is None:
            sma_step.append(np.nan)
        else:
            sma_step.append(sma_val)
    sma_step = np.array(sma_step, dtype=np.float64)  # now safe to use np.isnan

    sma_obj_batch = SMA(period)
    sma_batch = sma_obj_batch.batch_update(prices)

    valid_idx = ~np.isnan(sma_step)

    mean_diff = np.mean(np.abs(sma_step[valid_idx] - sma_batch[valid_idx]))
    max_diff = np.max(np.abs(sma_step[valid_idx] - sma_batch[valid_idx]))

    assert mean_diff < TOLERANCES["mean"], f"Mean SMA difference too high: {mean_diff}"
    assert max_diff < TOLERANCES["max"], f"Max SMA difference too high: {max_diff}"
