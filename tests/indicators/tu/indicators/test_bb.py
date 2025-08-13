import pytest
import pandas as pd
import numpy as np
from app.indicators.incremental.bollinger_bands import BollingerBands

from tests.indicators.reader import load_test_data

FILENAME = "history.csv"
PERIOD = 14

TOLERANCES = {
    "mean": 1e-6,
    "max": 1e-5,
}


@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)


def test_bb_update_matches_batch(loaded_data):
    # Sample close data
    df = loaded_data.copy()
    close = df["close"]

    # Parameters
    window = 20
    num_std_dev = 2

    # Batch calculation
    bb = BollingerBands(window, num_std_dev)
    batch_upper, batch_middle, batch_lower, batch_percent_b = bb.batch_update(close)

    # Step-by-step calculation
    bb_step = BollingerBands(window, num_std_dev)
    step_upper, step_middle, step_lower, step_percent_b = [], [], [], []

    for val in close:
        u, m, l, p = bb_step.update(val)
        step_upper.append(u)
        step_middle.append(m)
        step_lower.append(l)
        step_percent_b.append(p)

    # Convert step results to Series
    step_upper = pd.Series(step_upper)
    step_middle = pd.Series(step_middle)
    step_lower = pd.Series(step_lower)
    step_percent_b = pd.Series(step_percent_b)

    # Drop NaNs for comparison
    valid_idx = ~pd.isna(batch_upper)
    assert np.allclose(batch_upper[valid_idx], step_upper[valid_idx], atol=0), "Upper band mismatch"
    assert np.allclose(batch_middle[valid_idx], step_middle[valid_idx], atol=0), "Middle band mismatch"
    assert np.allclose(batch_lower[valid_idx], step_lower[valid_idx], atol=0), "Lower band mismatch"
    assert np.allclose(batch_percent_b[valid_idx], step_percent_b[valid_idx], atol=0), "%B mismatch"
