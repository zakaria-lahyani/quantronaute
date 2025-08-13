

import pytest
import pandas as pd
import numpy as np
from app.indicators.incremental.rma import RMA

from test.reader import load_test_data

FILENAME = "history.csv"
TOLERANCES = {
    "mean": 1e-6,
    "max": 1e-5,
}


@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)

def test_rma_batch_step_wise(loaded_data):
    df = loaded_data.copy()
    prices = df["close"]
    p = 14

    rma = RMA(period=p)
    rma_batch = RMA(period=p)

    rma_result = []
    for price in prices:
        rma_up = rma.update(price)
        rma_result.append(rma_up)

    rma_result = np.array(rma_result)

    batch_rma = rma_batch.batch_update(prices)

    print(rma_result)
    print(batch_rma)
    assert np.allclose(
        rma_result[~np.isnan(rma_result)],
        batch_rma[~np.isnan(batch_rma)],
        atol=1e-6
    ), "RMA batch vs step-by-step mismatch"

