import pytest
import pandas as pd
import numpy as np
from app.indicators.incremental.ichimoku import Ichimoku
from test.reader import load_test_data

FILENAME = "history.csv"

TOLERANCES = {
    "mean": 1e-6,
    "max": 1e-5,
}


@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)


def test_ichimoku_update_matches_batch(loaded_data):
    df = loaded_data.copy()
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # Standard Ichimoku parameters
    tenkan_period = 9
    kijun_period = 26
    senkou_b_period = 52
    chikou_shift = 26

    # Batch
    ichimoku = Ichimoku(tenkan_period, kijun_period, senkou_b_period, chikou_shift)
    b_tenkan, b_kijun, b_senkou_a, b_senkou_b, b_chikou, b_cloud = ichimoku.batch_update(high, low, close)

    # Step-by-step
    ichimoku_step = Ichimoku(tenkan_period, kijun_period, senkou_b_period, chikou_shift)
    s_tenkan, s_kijun, s_senkou_a, s_senkou_b, s_chikou, s_cloud = [], [], [], [], [], []

    for h, l, c in zip(high, low, close):
        t, k, sa, sb, ck, cl = ichimoku_step.update(h, l, c)
        s_tenkan.append(t)
        s_kijun.append(k)
        s_senkou_a.append(sa)
        s_senkou_b.append(sb)
        s_chikou.append(ck)
        s_cloud.append(cl)

    # Convert to arrays
    def series_masked(a, b):
        a = np.array(a, dtype=object)
        b = np.array(b, dtype=object)
        mask = np.array([x is not None and not (isinstance(x, float) and np.isnan(x)) for x in a]) & \
               np.array([x is not None and not (isinstance(x, float) and np.isnan(x)) for x in b])
        a_masked = np.array([x for x, m in zip(a, mask) if m], dtype=float)
        b_masked = np.array([x for x, m in zip(b, mask) if m], dtype=float)
        return a_masked, b_masked

    for name, batch, step in [
        ("tenkan", b_tenkan, s_tenkan),
        ("kijun", b_kijun, s_kijun),
        ("senkou_a", b_senkou_a, s_senkou_a),
        ("senkou_b", b_senkou_b, s_senkou_b),
        ("chikou", b_chikou, s_chikou),
    ]:
        b_vals, s_vals = series_masked(batch, step)
        diff = np.abs(b_vals - s_vals)
        assert diff.mean() <= TOLERANCES["mean"], f"{name} mean diff too high: {diff.mean()}"
        assert diff.max() <= TOLERANCES["max"], f"{name} max diff too high: {diff.max()}"

    # Cloud comparison
    for i, (b, s) in enumerate(zip(b_cloud, s_cloud)):
        if b is not None and s is not None:
            assert b == s, f"Cloud mismatch at index {i}: batch={b}, step={s}"
