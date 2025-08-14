from app.clients.mt5.client import create_client_with_retry
from app.data_source import fetch_historical_data
from app.indicators.indicator_processor import IndicatorProcessor
from app.strategy_builder.core.domain.enums import TimeFrameEnum
from app.strategy_builder.factory import StrategyEngineFactory
from app.utils.config import LoadEnvironmentVariables, YamlConfigurationManager

import os
from pathlib import Path

from app.utils.date_helper import DateHelper
from app.utils.functions_helper import list_files_in_folder


HISTORY_DAYS_LOOKUP = {
    "1": 7,
    "5": 7,
    "15": 10,
    "30": 10,
    "60": 15,
    "240": 15
}


# -----------------------------
# LOAD CONFIGURATION
# -----------------------------
ROOT_DIR = Path(__file__).parent.parent
dotenv_path = os.path.join(ROOT_DIR, ".env")
configuration = LoadEnvironmentVariables(dotenv_path)
date_helper = DateHelper()


# -----------------------------
# LOAD STRATEGIES
# -----------------------------
strategy_paths = list_files_in_folder(fr"{configuration.CONF_FOLDER_PATH}/strategies/{configuration.SYMBOL.lower()}")

engine = StrategyEngineFactory.create_engine(
    config_paths=strategy_paths,
    logger_name="trading-engine"
)
strategies = {
    name: engine.get_strategy_info(name)
    for name in engine.list_available_strategies()
}


# -----------------------------
# CREATE CLIENT
# -----------------------------
client = create_client_with_retry(configuration.API_BASE_URL)

# -----------------------------
# LOAD INDICATORS
# -----------------------------
yaml = YamlConfigurationManager()
indicators_paths = list_files_in_folder(fr"{configuration.CONF_FOLDER_PATH}/indicators/{configuration.SYMBOL.lower()}")
files_by_tf = { Path(p).stem.split("_")[-1]: p for p in indicators_paths }

indicator_configs = {
    tf.value: yaml.load_config(files_by_tf[tf.value])
    for tf in TimeFrameEnum
    if tf.value in files_by_tf
}

historicals = {
    tf.value: fetch_historical_data(
        client, configuration.SYMBOL, tf.name,
        date_helper.get_today(),
        date_helper.get_date_days_ago( HISTORY_DAYS_LOOKUP.get(tf.value, 7) ),
        date_helper.get_date_days_ago(-1)
    )
    for tf in TimeFrameEnum
    if tf.value in indicator_configs  # Only fetch data for timeframes with indicator configs
}

print(historicals.keys())

# -----------------------------
# WARMUP INDICATORs
# -----------------------------
indicators = IndicatorProcessor(configs=indicator_configs, historicals=historicals, is_bulk=True)
for tf, _ in historicals.items():
    try:
        df_result = indicators.get_historical_indicator_data(tf)
        path = rf"C:\Users\zak\Desktop\workspace\datalake\gold\xauusd\quantronaute\xauusd_{tf}.parquet"
        df_result.to_parquet(path)
    except Exception as e:
        raise



#
# # Load strategies from configuration
# engine = StrategyEngineFactory.create_engine(
#     config_paths=["../config/dummy.yaml"],
#     logger_name="trading-engine"
# )
#
# # Get strategy configurations
# strategies = {
#     name: engine.get_strategy_info(name)
#     for name in engine.list_available_strategies()
# }

# get data

# compute indicator

# run trader





# print(strategies)
#


#
# print(client)
# account = client.account.get_account_info()
# print(f"Balance: {account['balance']}")
#
# positions = client.positions.get_open_positions()
# print(positions)
#
# # Get positions by symbol
# eurusd_positions = client.positions.get_positions_by_symbol("EURUSD")
# print(eurusd_positions)
# xauusd_positions = client.positions.get_positions_by_symbol("XAUUSD")
# print(xauusd_positions)

