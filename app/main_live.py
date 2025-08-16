
import os
from pathlib import Path
import time
import logging
from typing import Optional

from app.clients.mt5.client import create_client_with_retry
from app.data.data_manger import DataSourceManager
from app.entry_manager.manager import RiskManager
from app.indicators.indicator_processor import IndicatorProcessor
from app.utils.config import LoadEnvironmentVariables
from app.utils.date_helper import DateHelper

# TODO: refactor
from app.main_backtest import load_strategies_configuration, load_indicator_configuration
from app.utils.functions_helper import has_new_candle

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while True:
        try:
            success_count = 0
            for tf in timeframes:
                try:
                    df_stream = data_source.get_stream_data(symbol=config.SYMBOL, timeframe=tf, nbr_bars=candle_index)
                    success_count += 1
                    
                    if has_new_candle(df_stream, last_known_bars[tf], candle_index):
                        print(f"[{tf}] New candle detected!")
                        print(df_stream)
                        last_known_bars[tf] = df_stream.iloc[-candle_index]  # Save the closed one

                        try:
                            indicators.process_new_row(tf, df_stream.iloc[-candle_index])
                        except Exception as e:
                            logger.error(f"Error processing indicators for {tf}: {e}")
                            continue
                            
                except Exception as e:
                    logger.warning(f"Error fetching stream data for {tf}: {e}")
                    continue

            # Only evaluate strategy if we got data from at least one timeframe
            if success_count > 0:
                try:
                    print(last_known_bars["1"])
                    # signal results
                    strateg_result = engine.evaluate(indicators.get_recent_rows())

                    print(strateg_result)

                    entry_manager.manage_trades()
                    print("here goes the the entry manager ! ")
                    print("here goes the the trade manager ! ")
                    
                    # Reset error counter on successful iteration
                    consecutive_errors = 0
                    
                except Exception as e:
                    logger.error(f"Error in strategy evaluation: {e}")
                    consecutive_errors += 1
            else:
                logger.warning("No data fetched from any timeframe this iteration")
                consecutive_errors += 1

            # Check if we've had too many consecutive errors
            if consecutive_errors >= max_consecutive_errors:
                logger.error(f"Too many consecutive errors ({consecutive_errors}). Exiting...")
                break

            time.sleep(5)
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt. Shutting down gracefully...")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            consecutive_errors += 1
            
            if consecutive_errors >= max_consecutive_errors:
                logger.error(f"Too many consecutive errors ({consecutive_errors}). Exiting...")
                break
            
            logger.info(f"Continuing after error... (attempt {consecutive_errors}/{max_consecutive_errors})")
            time.sleep(10)  # Wait longer after major errors

if __name__ == "__main__":
    main()