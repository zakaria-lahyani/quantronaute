
import os
from collections import deque
from pathlib import Path
import time
import logging

# Configure warnings early (must be before other imports)
from app.utils.warnings_config import configure_warnings
configure_warnings()

from app.clients.mt5.client import create_client_with_retry
from app.data.data_manger import DataSourceManager
from app.entry_manager.manager import EntryManager
from app.indicators.indicator_processor import IndicatorProcessor
from app.strategy_builder.data.dtos import Trades, AllStrategiesEvaluationResult
from app.trader.risk_manager.models import ScalingConfig, RiskEntryResult
from app.trader.risk_manager.risk_calculator import RiskCalculator
from app.trader.trade_executor import TradeExecutor
from app.utils.config import LoadEnvironmentVariables
from app.utils.date_helper import DateHelper

# Regime detection imports
from app.regime.regime_detector import RegimeDetector
from app.regime.data_structure import BarData

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
    engine = load_strategies_configuration(folder_path=config.CONF_FOLDER_PATH, symbol=config.SYMBOL)
    strategies = {
        name: engine.get_strategy_info(name)
        for name in engine.list_available_strategies()
    }
    entry_manager = EntryManager(strategies, symbol=config.SYMBOL, pip_value=config.PIP_VALUE)
    #
    # # indicator configuration
    # indicator_config = load_indicator_configuration(folder_path=config.CONF_FOLDER_PATH, symbol=config.SYMBOL)
    #
    # # timeframes
    # timeframes = list(indicator_config)
    # last_known_bars = {tf: None for tf in timeframes}
    #
    # data_source = DataSourceManager(mode=config.TRADE_MODE, client=client, date_helper=DateHelper() )
    #
    # historicals = {
    #     tf: data_source.get_historical_data(symbol=config.SYMBOL, timeframe = tf) for tf in timeframes
    # }
    #
    # # -----------------------------
    # # WARMUP INDICATORs
    # # -----------------------------
    # indicators = IndicatorProcessor(configs=indicator_config, historicals=historicals, is_bulk=False)

    mode = "live"
    trade_executor = TradeExecutor(mode, config, client=client)
    trade_executor.cancel()

if __name__ == "__main__":
    main()