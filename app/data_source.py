import pandas as pd

from app.clients.mt5.client import MT5Client


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
