from app.clients.mt5.client import MT5Client
from app.data.data_interface import DataSourceInterface
from app.strategy_builder.core.domain.enums import TimeFrameEnum
from app.utils.date_helper import DateHelper
import pandas as pd


class LiveDataSource(DataSourceInterface):
    """Data source for live trading using MT5 client"""

    def __init__(self, client: MT5Client, date_helper: DateHelper):
        self.client = client
        self.date_helper = date_helper
        self.HISTORY_DAYS_LOOKUP = { "1": 7, "5": 7, "15": 10, "30": 10, "60": 15, "240": 15 }


    def get_historical_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Fetch historical data from MT5 client"""
        # Find the corresponding TimeFrameEnum by value and get its name
        tf_name = self._get_timeframe_name(timeframe)

        start_date = self.date_helper.get_date_days_ago( self.HISTORY_DAYS_LOOKUP.get(timeframe, 7) )
        end_date = self.date_helper.get_date_days_ago(-1)


        data = self.client.data.fetch_bars(
            symbol,
            timeframe=tf_name,
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
        date_today = self.date_helper.get_today()
        max_time = df["time"].max()

        if max_time.date() == date_today:
            # Exclude the max time row
            df = df[df["time"] != max_time]

        return df

    def get_stream_data(self, symbol: str, timeframe: str, nbr_bars: int = 3) -> pd.DataFrame:
        """Get streaming data from MT5 client"""
        tf_name = self._get_timeframe_name(timeframe)

        data = self.client.data.fetch_bars(symbol, timeframe=tf_name, num_bars=nbr_bars)

        # Convert list of HistoricalBar objects to list of dictionaries
        bars_dict = [bar.model_dump() for bar in data]
        df = pd.DataFrame(bars_dict)

        if not df.empty:
            df["time"] = pd.to_datetime(df["time"])

        return df

    def _get_timeframe_name(self, timeframe_value: str) -> str:
        """Convert timeframe value to MT5 timeframe name"""
        for tf in TimeFrameEnum:
            if tf.value == timeframe_value:
                return tf.name
        raise ValueError(f"Invalid timeframe value: {timeframe_value}")

