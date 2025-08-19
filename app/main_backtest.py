
import os
from pathlib import Path
from typing import Dict, Any

from app.data.data_manger import DataSourceManager
from app.indicators.indicator_processor import IndicatorProcessor
from app.strategy_builder.core.domain.enums import TimeFrameEnum
from app.strategy_builder.factory import StrategyEngineFactory
from app.utils.config import LoadEnvironmentVariables, YamlConfigurationManager
from app.utils.functions_helper import list_files_in_folder


def load_historical_data(symbol:str, timeframes: list[str], data_source: DataSourceManager, start_date:str, end_date:str) -> Dict[str, Any]:
    """Load historical data for all timeframes"""
    historicals = {}
    for tf in timeframes:
        historicals[tf] = data_source.get_historical_data(symbol, timeframe=tf)

    return historicals


def load_indicator_configuration(folder_path: str, symbol:str):
    # -----------------------------
    # LOAD INDICATORS
    # -----------------------------
    yaml = YamlConfigurationManager()
    indicators_paths = list_files_in_folder(fr"{folder_path}/indicators/{symbol.lower()}")
    files_by_tf = {Path(p).stem.split("_")[-1]: p for p in indicators_paths}

    return {
        tf.value: yaml.load_config(files_by_tf[tf.value])
        for tf in TimeFrameEnum
        if tf.value in files_by_tf
    }

def load_strategies_configuration(folder_path: str, symbol:str):
    strategy_paths = list_files_in_folder(fr"{folder_path}/strategies/{symbol.lower()}")

    engine = StrategyEngineFactory.create_engine(
        config_paths=strategy_paths,
        logger_name="trading-engine"
    )

    return  engine


def main():
    start_date = "2000-01-01 00:00:00"
    end_date = "2026-01-01 00:00:00"

    # Load configuration
    ROOT_DIR = Path(__file__).parent.parent
    config = LoadEnvironmentVariables(os.path.join(ROOT_DIR, ".env.test"))

    # strategy configuration
    strategies = load_strategies_configuration(folder_path=config.CONF_FOLDER_PATH, symbol=config.SYMBOL)

    # indicator configuration
    indicator_config = load_indicator_configuration(folder_path=config.CONF_FOLDER_PATH, symbol=config.SYMBOL)

    # timeframes
    timeframes = list(indicator_config)

    data_source = DataSourceManager(mode=config.TRADE_MODE, data_path=config.BACKTEST_DATA_PATH, symbol=config.SYMBOL )
    data_source.load_backtest_data(timeframes)

    historical_data = load_historical_data(
        symbol=config.SYMBOL, data_source=data_source, timeframes=timeframes, start_date=start_date, end_date=end_date
    )

    # compute indicators
    indicators = IndicatorProcessor(configs=indicator_config, historicals=historical_data, is_bulk=True)

    print(indicators.get_historical_indicator_data("240"))


if __name__ == "__main__":
    main()