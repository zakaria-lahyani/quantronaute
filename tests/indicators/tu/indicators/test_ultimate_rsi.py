import pytest
import numpy as np
import pandas as pd
from app.indicators.incremental.ultimate_rsi import UltimateRsi
from tests.indicators.reader import load_test_data

FILENAME = "history.csv"
TOLERANCES = {
    "mean": 1e-9,
    "max": 1e-8,
}

@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)



def test_ultimate_rsi_step_vs_batch(loaded_data):
    df = loaded_data.copy()
    prices = df["close"].values
    length = 14
    smooth_length = 14
    ma_type1 = 'RMA'
    ma_type2 = 'RMA'

    # Step-by-step
    ursi_inc = UltimateRsi(src='close', length=length, smooth_length=smooth_length )

    step_ursi = []
    step_signal = []

    for i in range(len(prices)):
        row = {'close': prices[i]}
        u, s = ursi_inc.update(row)
        step_ursi.append(u)
        step_signal.append(s)

    step_ursi = np.array(step_ursi, dtype=np.float64)
    step_signal = np.array(step_signal, dtype=np.float64)

    # Batch

    batch_ursi, batch_signal = UltimateRsi(src='close', length=length, smooth_length=smooth_length).batch_update(df)
    valid_mask = ~np.isnan(step_signal) & ~np.isnan(batch_signal)

    print("Max diff step_signal vs batch_signal:", np.nanmax(np.abs(step_signal - batch_signal)))
    print("Mean diff:", np.nanmean(np.abs(step_signal - batch_signal)))


    assert np.allclose(step_ursi[valid_mask], batch_ursi[valid_mask], atol=1), "URSI mismatch"
    assert np.allclose(step_signal[valid_mask], batch_signal[valid_mask], atol=1), "Signal mismatch"
