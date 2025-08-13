import pytest
import numpy as np
import pandas as pd
from app.indicators.incremental.supertrend import Supertrend
from test.reader import load_test_data

FILENAME = "history.csv"
TOLERANCES = {
    "mean": 1e-9,
    "max": 1e-8,
}

@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)

def test_supertrend_update_matches_batch(loaded_data):
    df = loaded_data.copy()
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values

    period = 10
    multiplier = 3.0

    # Step-by-step
    st = Supertrend(period, multiplier)
    step_vals = []
    step_trends = []

    for h, l, c in zip(high, low, close):
        res = st.update(h, l, c)
        if res is None:
            step_vals.append(np.nan)
            step_trends.append(None)
        else:
            val, trend = res
            step_vals.append(val)
            step_trends.append(trend)

    # Batch
    st_batch = Supertrend(period, multiplier)
    batch_vals, batch_trends = st_batch.batch_update(high, low, close)

    # Compare with np.allclose ignoring NaNs
    step_vals = np.array(step_vals, dtype=np.float64)
    batch_vals = np.array(batch_vals, dtype=np.float64)

    # Align trends as strings
    batch_trends = np.array(batch_trends, dtype=object)
    step_trends = np.array(step_trends, dtype=object)

    # Tolerance for numerical errors
    close_mask = ~np.isnan(step_vals)
    assert np.allclose(batch_vals[close_mask], step_vals[close_mask], atol=1e-8), "Supertrend values mismatch"

    # Check trend strings match (ignoring initial None)
    trend_mask = step_trends != None
    assert np.all(batch_trends[trend_mask] == step_trends[trend_mask]), "Trend labels mismatch"


