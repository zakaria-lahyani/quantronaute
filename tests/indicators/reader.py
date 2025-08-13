import pandas as pd
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(CURRENT_DIR, "data")

def load_test_data(filename):
    try:
        df = pd.read_csv(f"{DATA_PATH}/{filename}")
        required_cols = {'high', 'low', 'close'}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"CSV must contain columns: {required_cols}")
        return df
    except Exception as e:
        print(e)
