import pytest
import pandas as pd
import numpy as np
from pandas.core.roperator import rand_

from app.indicators.incremental.adx import ADX  # Adjust if needed
from tests.indicators.reader import load_test_data

FILENAME = "history.csv"
PERIOD = 14

# Tolerances for numerical comparison
TOLERANCES = {
    "mean_adx": 1e-6,
    "max_adx": 1e-5,
    "mean_plus_di": 1e-6,
    "max_plus_di": 1e-5,
    "mean_minus_di": 1e-6,
    "max_minus_di": 1e-5,
}

@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)

def test_aroon_update_matches(loaded_data):
    df = loaded_data.copy()

    # Batch calculation
    adx_batch = ADX(period=PERIOD)
    batch_adx, batch_plus_di, batch_minus_di = adx_batch.batch_update(
        df['high'].values, df['low'].values, df['close'].values
    )

    # Incremental update
    adx_step = ADX(period=PERIOD)
    step_adx, step_plus_di, step_minus_di = [], [], []

    for i in range(0, len(df)):
        row = df.iloc[i]
        result = adx_step.update(row['high'], row['low'], row['close'])
        if result is not None:
            _adx, _plus_di, _minus_di = result
            step_adx.append(_adx)
            step_plus_di.append(_plus_di)
            step_minus_di.append(_minus_di)

    #
    # # Compute differences ignoring NaNs
    # adx_diff = np.abs(df['batch_adx'] - df['step_adx']).dropna()
    # plus_diff = np.abs(df['batch_plus_di'] - df['step_plus_di']).dropna()
    # minus_diff = np.abs(df['batch_minus_di'] - df['step_minus_di']).dropna()
    #
    # # Ensure there's valid data to compare
    # assert not adx_diff.empty, "No overlapping non-NaN ADX values to compare."
    # assert not plus_diff.empty, "No overlapping non-NaN +DI values to compare."
    # assert not minus_diff.empty, "No overlapping non-NaN -DI values to compare."
    #
    # # Assertions
    # assert adx_diff.mean() < TOLERANCES["mean_adx"], f"Mean ADX diff too high: {adx_diff.mean()}"
    # assert adx_diff.max() < TOLERANCES["max_adx"], f"Max ADX diff too high: {adx_diff.max()}"
    #
    # assert plus_diff.mean() < TOLERANCES["mean_plus_di"], f"Mean +DI diff too high: {plus_diff.mean()}"
    # assert plus_diff.max() < TOLERANCES["max_plus_di"], f"Max +DI diff too high: {plus_diff.max()}"
    #
    # assert minus_diff.mean() < TOLERANCES["mean_minus_di"], f"Mean -DI diff too high: {minus_diff.mean()}"
    # assert minus_diff.max() < TOLERANCES["max_minus_di"], f"Max -DI diff too high: {minus_diff.max()}"
