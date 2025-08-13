import pytest
import pandas as pd
import numpy as np
from app.indicators.incremental.obv import OBV
from tests.indicators.reader import load_test_data

FILENAME = "history.csv"
TOLERANCES = {
    "mean": 1e-6,
    "max": 1e-5,
}


@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)


def test_obv_update_matches_batch(loaded_data):
    df = loaded_data.copy()
    close = df["close"]
    volume = df["tick_volume"]

    period = 14  # example EMA period
    obv_obj = OBV(period)

    # Step-by-step incremental update
    obv_list = []
    osc_list = []
    for c, v in zip(close, volume):
        obv_val, osc_val = obv_obj.update(c, v)
        obv_list.append(obv_val)
        osc_list.append(osc_val)

    obv_list = np.array(obv_list)
    osc_list = np.array(osc_list)

    # Batch update
    obv_obj_batch = OBV(period)
    obv_batch, osc_batch = obv_obj_batch.batch_update(close, volume)

    # Compare OBV values ignoring initial NaNs if any (shouldn't be NaN in OBV but EMA might cause NaNs)
    # For EMA initial values, NaNs may appear, so we compare only valid indices
    valid_idx = ~np.isnan(osc_list) & ~np.isnan(osc_batch)

    mean_diff_obv = np.mean(np.abs(obv_list[valid_idx] - obv_batch[valid_idx]))
    max_diff_obv = np.max(np.abs(obv_list[valid_idx] - obv_batch[valid_idx]))

    mean_diff_osc = np.mean(np.abs(osc_list[valid_idx] - osc_batch[valid_idx]))
    max_diff_osc = np.max(np.abs(osc_list[valid_idx] - osc_batch[valid_idx]))

    assert mean_diff_obv < TOLERANCES["mean"], f"Mean OBV difference too high: {mean_diff_obv}"
    assert max_diff_obv < TOLERANCES["max"], f"Max OBV difference too high: {max_diff_obv}"

    assert mean_diff_osc < TOLERANCES["mean"], f"Mean oscillator difference too high: {mean_diff_osc}"
    assert max_diff_osc < TOLERANCES["max"], f"Max oscillator difference too high: {max_diff_osc}"
