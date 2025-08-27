
import os
from collections import deque
from pathlib import Path
import time
import logging
import pandas as pd

from app.clients.mt5.client import create_client_with_retry
from app.data.data_manger import DataSourceManager
from app.entry_manager.manager import EntryManager
from app.indicators.indicator_processor import IndicatorProcessor
from app.strategy_builder.data.dtos import Trades, AllStrategiesEvaluationResult
from app.trader.trade_executor import TradeExecutor
from app.utils.config import LoadEnvironmentVariables
from app.utils.date_helper import DateHelper
from app.regime.regime_manager import RegimeManager
from app.main_backtest import load_strategies_configuration, load_indicator_configuration
# TODO: refactor
from app.utils.functions_helper import has_new_candle

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    candle_index = 2
    iteration_counter = 0  # Counter for iterations

    # Load configuration
    ROOT_DIR = Path(__file__).parent.parent
    config = LoadEnvironmentVariables(os.path.join(ROOT_DIR, ".env"))

    client = create_client_with_retry(config.API_BASE_URL)

    # strategy configuration
    engine = load_strategies_configuration(folder_path=config.CONF_FOLDER_PATH, symbol=config.SYMBOL)
    strategies = {
        name: engine.get_strategy_info(name)
        for name in engine.list_available_strategies()
    }
    entry_manager = EntryManager(strategies, symbol=config.SYMBOL, pip_value=config.PIP_VALUE)

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

    # -----------------------------
    # SETUP REGIME DETECTION
    # -----------------------------
    regime_manager = RegimeManager(
        warmup_bars=500,
        persist_n=2,
        transition_bars=3,
        bb_threshold_len=200
    )
    regime_manager.setup(timeframes, historicals)

    mode = "live"
    trade_executor = TradeExecutor(mode, config, client=client)

    account_balance = client.account.get_balance()

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
                        last_known_bars[tf] = df_stream.iloc[-candle_index]
                        try:
                            # Update regime for this timeframe first
                            regime_data = regime_manager.update(tf, df_stream.iloc[-candle_index])

                            # Process indicators with regime data
                            indicators.process_new_row(tf, df_stream.iloc[-candle_index], regime_data)

                        except Exception as e:
                            logger.error(f"Error processing indicators for {tf}: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"Error fetching stream data for {tf}: {e}")
                    continue

            # Only evaluate strategy if we got data from at least one timeframe
            if success_count > 0:
                iteration_counter += 1
                try:
                    # Get recent rows from indicators (already enriched with regime data)
                    recent_rows: dict[str, deque] = indicators.get_recent_rows()

                    # Evaluate strategies with regime-enriched data
                    strateg_result: AllStrategiesEvaluationResult = engine.evaluate(recent_rows)
                    entries: Trades = entry_manager.manage_trades(strateg_result.strategies, recent_rows, account_balance)

                    trade_executor.manage(entries, date_helper=DateHelper())

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
            time.sleep(60)

if __name__ == "__main__":
    main()