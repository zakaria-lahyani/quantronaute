import pytest
import numpy as np
from app.indicators.incremental.sar import SAR
import pandas as pd
from test.reader import load_test_data

FILENAME = "history.csv"
TOLERANCES = {
    "mean": 1e-6,
    "max": 1e-5,
}

@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)

def test_sar_update_matches_batch(loaded_data):
    df = loaded_data.copy()
    highs = df["high"].values
    lows = df["low"].values

    acceleration = 0.02
    max_acceleration = 0.2

    sar_obj = SAR(acceleration, max_acceleration)

    # Step-by-step updates
    sar_step = []
    for h, l in zip(highs, lows):
        sar_val = sar_obj.update(h, l)
        sar_step.append(sar_val)
    sar_step = np.array(sar_step)

    # Batch update
    sar_obj_batch = SAR(acceleration, max_acceleration)
    sar_batch_vals = sar_obj_batch.batch_update(highs, lows)

    # Compare ignoring NaNs (if any)
    valid_idx = ~np.isnan(sar_step) & ~np.isnan(sar_batch_vals)

    mean_diff = np.mean(np.abs(sar_step[valid_idx] - sar_batch_vals[valid_idx]))
    max_diff = np.max(np.abs(sar_step[valid_idx] - sar_batch_vals[valid_idx]))

    assert mean_diff < TOLERANCES["mean"], f"Mean SAR difference too high: {mean_diff}"
    assert max_diff < TOLERANCES["max"], f"Max SAR difference too high: {max_diff}"
