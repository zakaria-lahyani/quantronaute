import pytest
import pandas as pd
import numpy as np
from app.indicators.incremental.atr import ATR

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

def test_atr_update_matches_batch(loaded_data):
    df = loaded_data.copy()
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # Batch calculation
    atr_batch = ATR(window=PERIOD)
    batch_result = atr_batch.batch_update(high, low, close)

    # Step-by-step calculation
    atr_step = ATR(window=PERIOD)
    step_result = []
    for h, l, c in zip(high, low, close):
        val = atr_step.update(h, l, c)
        step_result.append(val)

    step_result = pd.Series(step_result, index=high.index)

    # Drop initial NaNs (before ATR becomes valid)
    compare_df = pd.DataFrame({
        "batch": batch_result,
        "step": step_result
    }).dropna()

    diff = (compare_df["batch"] - compare_df["step"]).abs()

    assert diff.mean() <= TOLERANCES["mean"], f"Mean ATR difference too high: {diff.mean()}"
    assert diff.max() <= TOLERANCES["max"], f"Max ATR difference too high: {diff.max()}"
