
import os
from pathlib import Path

from app.clients.mt5.client import create_client_with_retry
from app.data.data_manger import DataSourceManager
from app.indicators.indicator_processor import IndicatorProcessor
from app.utils.config import LoadEnvironmentVariables
from app.utils.date_helper import DateHelper

# TODO: refactor
from app.main_backtest import load_strategies_configuration, load_indicator_configuration


def main():
    # Load configuration
    ROOT_DIR = Path(__file__).parent.parent
    config = LoadEnvironmentVariables(os.path.join(ROOT_DIR, ".env"))

    client = create_client_with_retry(config.API_BASE_URL)

    # strategy configuration
    strategies = load_strategies_configuration(folder_path=config.CONF_FOLDER_PATH, symbol=config.SYMBOL)

    # indicator configuration
    indicator_config = load_indicator_configuration(folder_path=config.CONF_FOLDER_PATH, symbol=config.SYMBOL)

    # timeframes
    timeframes = list(indicator_config)

    data_source = DataSourceManager(mode=config.TRADE_MODE, client=client, date_helper=DateHelper() )

    historicals = {
        tf: data_source.get_historical_data(symbol=config.SYMBOL, timeframe = tf) for tf in timeframes
    }

    # -----------------------------
    # WARMUP INDICATORs
    # -----------------------------
    indicators = IndicatorProcessor(configs=indicator_config, historicals=historicals, is_bulk=False)

    print(indicators.get_historical_indicator_data("240"))

if __name__ == "__main__":
    main()