from app.indicators.indicator_processor import IndicatorProcessor
from test.reader import load_test_data
import pandas as pd

pd.set_option('display.max_rows', 100)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 100)

timeframe = "240"
indicator_config = {
    timeframe: {
        "ursi": {'src': 'close', 'length': 14, 'smooth_length': 14},
        "bb": {'window': 20, 'num_std_dev': 2},
        "atr": {'window': 14},
        "rsi": {'period': 14, "signal_period":14},
        "sar": {'acceleration':0.02, 'max_acceleration':0.2},
        "stochrsi": {'rsi_period': 14, 'stochrsi_period': 14, 'k_smooth':3 , 'd_smooth':3 },
        "supertrend": {'period':10 , 'multiplier':3.0 },
        "macd": {'fast': 3, 'slow': 6, 'signal': 3},
        "ichimoku": {'tenkan_period':9 , 'kijun_period':26 , 'senkou_b_period': 52, 'chikou_shift':26 },
        "adx": {'period': 10},
        "obv": {'period': 10},
        "aroon": {'period': 10},
        "keltner": {'ema_window': 20, 'atr_window': 10, 'multiplier': 2},
        "ema": {'period': 10},
        "sma": {'period': 10},
        "rma": {'period': 10},
    }
}


df_stream = load_test_data("stream.csv")
df_history = load_test_data("history.csv")

bulk_indicators = IndicatorProcessor(configs=indicator_config, historicals={timeframe: df_history}, is_bulk=True, recent_rows_limit=20)
df_bulk_history = bulk_indicators.get_historical_indicator_data(timeframe)
bulk_recent_rows = bulk_indicators.get_recent_rows(timeframe=timeframe)

print(df_bulk_history.columns)
print(bulk_recent_rows.tail(1))

step_indicator = IndicatorProcessor(configs=indicator_config, historicals={timeframe: df_history}, is_bulk=False, recent_rows_limit=20)
df_step_history = step_indicator.get_historical_indicator_data(timeframe)
step_recent_rows = step_indicator.get_recent_rows(timeframe=timeframe)

print(df_step_history.columns)
print(step_recent_rows.tail(1))

# stream one row
for i in range(0, 1):
    row = df_stream.iloc[i]
    step_indicator.process_new_row(timeframe, row)

print(step_indicator.get_recent_rows(timeframe=timeframe).tail(1))

