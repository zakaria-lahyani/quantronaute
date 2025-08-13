import pytest
import pandas as pd
import numpy as np
from app.indicators.incremental.ema import EMA
from test.reader import load_test_data

FILENAME = "history.csv"

TOLERANCES = {
    "mean": 1e-6,
    "max": 1e-5,
}


@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)


def test_ema_update_matches_batch(loaded_data):
    df = loaded_data.copy()
    close = df["close"]
    period = 20

    # Batch computation
    ema_batch = EMA(period).batch_update(close)

    # Step-by-step computation
    ema_step = EMA(period)
    step_values = []
    for val in close:
        step_values.append(ema_step.update(val))

    step_series = pd.Series(step_values)

    # Drop first None (if any)
    mask = ~pd.isna(ema_batch)

    diff = np.abs(ema_batch[mask] - step_series[mask])
    assert diff.mean() <= TOLERANCES["mean"], f"EMA mean diff too high: {diff.mean()}"
    assert diff.max() <= TOLERANCES["max"], f"EMA max diff too high: {diff.max()}"
