import pytest
import pandas as pd
import numpy as np
from app.indicators.incremental.aroon import Aroon  # Adjust if needed
from tests.indicators.reader import load_test_data

FILENAME = "history.csv"
PERIOD = 14

# Tolerances for numerical comparison
TOLERANCES = {
    "mean_aroon_up": 1.0,
    "mean_aroon_down": 1.0,
    "max_aroon_up": 3.0,
    "max_aroon_down": 3.0,
}

@pytest.fixture(scope="module")
def loaded_data():
    return load_test_data(FILENAME)


def test_aroon_update_matches(loaded_data):
        df = loaded_data.copy()

        # Batch calculation
        aroon_batch = Aroon(period=PERIOD)
        batch_up, batch_down = aroon_batch.batch_update(df['high'].values, df['low'].values)

        # Incremental update
        aroon_step = Aroon(period=PERIOD)
        step_up, step_down = [], []

        for h, l in zip(df['high'], df['low']):
            result = aroon_step.update(h, l)
            if result is not None:
                up, down = result
            else:
                up, down = np.nan, np.nan
            step_up.append(up)
            step_down.append(down)

        df['batch_up'] = batch_up
        df['batch_down'] = batch_down
        df['step_up'] = step_up
        df['step_down'] = step_down

        compare_df = df.dropna(subset=['batch_up', 'step_up'])

        diff_up = np.abs(compare_df['batch_up'] - compare_df['step_up'])
        diff_down = np.abs(compare_df['batch_down'] - compare_df['step_down'])

        assert diff_up.mean() <= TOLERANCES["mean_aroon_up"], f"Mean Aroon Up diff too high: {diff_up.mean()}"
        assert diff_down.mean() <= TOLERANCES["mean_aroon_down"], f"Mean Aroon Down diff too high: {diff_down.mean()}"
        assert diff_up.max() <= TOLERANCES["max_aroon_up"], f"Max Aroon Up diff too high: {diff_up.max()}"
        assert diff_down.max() <= TOLERANCES["max_aroon_down"], f"Max Aroon Down diff too high: {diff_down.max()}"
