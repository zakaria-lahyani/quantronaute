
import os
from pathlib import Path
import time

from app.clients.mt5.client import create_client_with_retry
from app.data.data_manger import DataSourceManager
from app.entry_manager.manager import RiskManager
from app.indicators.indicator_processor import IndicatorProcessor
from app.utils.config import LoadEnvironmentVariables
from app.utils.date_helper import DateHelper

# TODO: refactor
from app.main_backtest import load_strategies_configuration, load_indicator_configuration
from app.utils.functions_helper import has_new_candle


def main():
    candle_index = 2

    # Load configuration
    ROOT_DIR = Path(__file__).parent.parent
    config = LoadEnvironmentVariables(os.path.join(ROOT_DIR, ".env"))

    client = create_client_with_retry(config.API_BASE_URL)

    # strategy configuration
    strategies, engine = load_strategies_configuration(folder_path=config.CONF_FOLDER_PATH, symbol=config.SYMBOL)
    entry_manager = RiskManager(strategies, symbol=config.SYMBOL, pip_value=100.0)

    # indicator configuration
    indicator_config = load_indicator_configuration(folder_path=config.CONF_FOLDER_PATH, symbol=config.SYMBOL)

    # timeframes
    timeframes = list(indicator_config)
    last_known_bars = {tf: None for tf in timeframes}

    data_source = DataSourceManager(mode=config.TRADE_MODE, client=client, date_helper=DateHelper() )

    historicals = {
        tf: data_source.get_historical_data(symbol=config.SYMBOL, timeframe = tf) for tf in timeframes
    }

    # -----------------------------
    # WARMUP INDICATORs
    # -----------------------------
    indicators = IndicatorProcessor(configs=indicator_config, historicals=historicals, is_bulk=False)

    # get stream data
    while True:
        for tf in timeframes:
            df_stream = data_source.get_stream_data(symbol=config.SYMBOL, timeframe = tf, nbr_bars=candle_index)
            if has_new_candle(df_stream, last_known_bars[tf], candle_index):
                print(f"[{tf}] New candle detected!")
                last_known_bars[tf] = df_stream.iloc[-candle_index]  # Save the closed one
                indicators.process_new_row(tf, df_stream.iloc[-candle_index])

        recent_rows = indicators.get_recent_rows()
        print(recent_rows)
        strateg_result = engine.evaluate(indicators.get_recent_rows())
        print(strateg_result)

        # entry_manager.manage_trades()
        print("here goes the the strategy evaluate ! ")
        print("here goes the the entry manager ! ")
        print("here goes the the trade manager ! ")

        time.sleep(20)

if __name__ == "__main__":
    main()