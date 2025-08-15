import pandas as pd

from app.clients.mt5.client import MT5Client
from app.strategy_builder.core.domain.enums import TimeFrameEnum


def fetch_historical_data(client: MT5Client, symbol:str, timeframe:str, date_today:str, start_date:str, end_date:str):
    data = client.data.fetch_bars(
        symbol,
        timeframe=timeframe,  # e.g., "30" -> "M30"
        start=f"{start_date}T00:00:00Z",
        end=f"{end_date}T00:00:00Z"
    )

    # Convert list of HistoricalBar objects to list of dictionaries
    bars_dict = [bar.model_dump() for bar in data]
    
    df = pd.DataFrame(bars_dict)

    # Handle empty dataframe case
    if df.empty:
        return df
    
    df["time"] = pd.to_datetime(df["time"])

    # Get the row with the max time
    max_time = df["time"].max()

    if max_time.date() == date_today:
        # Exclude the max time row
        df = df[df["time"] != max_time]

    return df


def get_stream_data(client: MT5Client, symbol:str, timeframe:str, nbr_bars:int=3):
    # Find the corresponding TimeFrameEnum by value and get its name
    tf_name = None
    for tf in TimeFrameEnum:
        if tf.value == timeframe:
            tf_name = tf.name
            break
    
    if not tf_name:
        raise ValueError(f"Invalid timeframe value: {timeframe}")
    
    data = client.data.fetch_bars(symbol, timeframe=tf_name, num_bars=nbr_bars)
    # Convert list of HistoricalBar objects to list of dictionaries
    bars_dict = [bar.model_dump() for bar in data]
    # Handle empty dataframe case
    df = pd.DataFrame(bars_dict)

    if df.empty:
        return df

    df["time"] = pd.to_datetime(df["time"])

    return df


def has_new_candle(current_df: pd.DataFrame, last_known_bar, candle_index):
    """Check if a new candle has closed."""
    if last_known_bar is None:
        return True  # Initial fetch
    current_latest_time = pd.to_datetime(current_df.iloc[-candle_index]["time"])
    last_known_time = pd.to_datetime(last_known_bar["time"])
    return current_latest_time > last_known_time
