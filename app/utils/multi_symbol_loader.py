"""
Multi-Symbol Configuration Loader.

Utility functions to load configurations and create components for multiple symbols.
Simplifies the main entry point by encapsulating per-symbol component creation logic.
"""

import logging
from typing import Dict, List, Any
from pathlib import Path

from app.utils.config import LoadEnvironmentVariables
from app.data.data_manger import DataSourceManager
from app.entry_manager.manager import EntryManager
from app.indicators.indicator_processor import IndicatorProcessor
from app.regime.regime_manager import RegimeManager
from app.trader.executor_builder import ExecutorBuilder
from app.utils.date_helper import DateHelper


def load_strategies_for_symbol(folder_path: str, symbol: str, logger: logging.Logger):
    """
    Load strategy engine for a specific symbol.

    Args:
        folder_path: Base configuration folder path
        symbol: Trading symbol (e.g., "XAUUSD")
        logger: Logger instance

    Returns:
        StrategyEngine for the symbol
    """
    from app.strategy_builder.factory import StrategyEngineFactory
    from app.utils.functions_helper import list_files_in_folder

    logger.info(f"  Loading strategies for {symbol}...")

    strategy_folder = Path(folder_path) / "strategies" / symbol.lower()

    if not strategy_folder.exists():
        logger.warning(f"  No strategy folder found for {symbol} at {strategy_folder}")
        logger.warning(f"  Creating empty strategy engine for {symbol}")
        # Return empty engine or handle as needed
        return StrategyEngineFactory.create_engine(
            config_paths=[],
            logger_name=f"trading-engine-{symbol.lower()}"
        )

    strategy_paths = list_files_in_folder(str(strategy_folder))

    if not strategy_paths:
        logger.warning(f"  No strategy files found for {symbol}")

    logger.info(f"  Found {len(strategy_paths)} strategy files for {symbol}")

    engine = StrategyEngineFactory.create_engine(
        config_paths=strategy_paths,
        logger_name=f"trading-engine-{symbol.lower()}"
    )

    return engine


def load_indicators_for_symbol(folder_path: str, symbol: str, logger: logging.Logger) -> Dict:
    """
    Load indicator configuration for a specific symbol.

    Args:
        folder_path: Base configuration folder path
        symbol: Trading symbol (e.g., "XAUUSD")
        logger: Logger instance

    Returns:
        Dict mapping timeframe -> indicator config
    """
    from app.utils.config import YamlConfigurationManager
    from app.utils.functions_helper import list_files_in_folder
    from app.strategy_builder.core.domain.enums import TimeFrameEnum

    logger.info(f"  Loading indicators for {symbol}...")

    yaml_manager = YamlConfigurationManager()
    indicator_folder = Path(folder_path) / "indicators" / symbol.lower()

    if not indicator_folder.exists():
        logger.warning(f"  No indicator folder found for {symbol} at {indicator_folder}")
        return {}

    indicator_paths = list_files_in_folder(str(indicator_folder))

    if not indicator_paths:
        logger.warning(f"  No indicator files found for {symbol}")
        return {}

    # Parse timeframe from filename (e.g., "xauusd_1.yaml" -> "1")
    files_by_tf = {
        Path(p).stem.split("_")[-1]: p
        for p in indicator_paths
    }

    logger.info(f"  Found {len(files_by_tf)} indicator configs for {symbol}: {list(files_by_tf.keys())}")

    configs = {}
    for tf in TimeFrameEnum:
        if tf.value in files_by_tf:
            configs[tf.value] = yaml_manager.load_config(files_by_tf[tf.value])

    return configs


def load_all_components_for_symbols(
    symbols: List[str],
    env_config: LoadEnvironmentVariables,
    client: Any,
    data_source: DataSourceManager,
    date_helper: DateHelper,
    logger: logging.Logger
) -> Dict[str, Dict[str, Any]]:
    """
    Load all components for all symbols.

    Args:
        symbols: List of symbols to load components for
        env_config: Environment configuration
        client: MT5 Client
        data_source: DataSourceManager
        date_helper: DateHelper
        logger: Logger instance

    Returns:
        Dict mapping symbol -> components dict with:
            - indicator_processor: IndicatorProcessor
            - regime_manager: RegimeManager
            - strategy_engine: StrategyEngine
            - entry_manager: EntryManager
            - trade_executor: TradeExecutor
            - timeframes: List[str]
            - historicals: Dict[str, DataFrame]

    Example:
        ```python
        components = load_all_components_for_symbols(
            symbols=["XAUUSD", "BTCUSD"],
            env_config=env_config,
            client=client,
            data_source=data_source,
            date_helper=date_helper,
            logger=logger
        )

        # Access components for specific symbol
        xau_processor = components["XAUUSD"]["indicator_processor"]
        btc_engine = components["BTCUSD"]["strategy_engine"]
        ```
    """
    logger.info("\n=== Loading Components for All Symbols ===")

    symbol_components = {}

    for symbol in symbols:
        logger.info(f"\n--- Loading components for {symbol} ---")

        # Get symbol-specific configuration
        symbol_config = env_config.get_symbol_config(symbol)

        # Load strategies
        strategy_engine = load_strategies_for_symbol(
            folder_path=env_config.CONF_FOLDER_PATH,
            symbol=symbol,
            logger=logger
        )

        # Create entry manager
        strategies = {
            name: strategy_engine.get_strategy_info(name)
            for name in strategy_engine.list_available_strategies()
        }

        logger.info(f"  Creating EntryManager for {symbol}...")
        entry_manager = EntryManager(
            strategies=strategies,
            symbol=symbol,
            pip_value=symbol_config['pip_value'],
            logger=logging.getLogger(f'entry-manager-{symbol.lower()}')
        )

        # Load indicator configuration
        indicator_config = load_indicators_for_symbol(
            folder_path=env_config.CONF_FOLDER_PATH,
            symbol=symbol,
            logger=logger
        )

        if not indicator_config:
            logger.warning(f"  No indicator configuration for {symbol}, using default timeframes")
            # Use default timeframes if no indicator config
            indicator_config = {"1": {}, "5": {}, "15": {}}

        timeframes = list(indicator_config.keys())
        logger.info(f"  Timeframes for {symbol}: {timeframes}")

        # Fetch historical data
        logger.info(f"  Fetching historical data for {symbol}...")
        historicals = {}
        for tf in timeframes:
            try:
                historicals[tf] = data_source.get_historical_data(
                    symbol=symbol,
                    timeframe=tf
                )
                logger.info(f"    ✓ Loaded {len(historicals[tf])} bars for {symbol} {tf}")
            except Exception as e:
                logger.error(f"    ✗ Failed to load historical data for {symbol} {tf}: {e}")
                historicals[tf] = None

        # Create indicator processor
        logger.info(f"  Creating IndicatorProcessor for {symbol}...")
        indicator_processor = IndicatorProcessor(
            configs=indicator_config,
            historicals=historicals,
            is_bulk=False
        )

        # Create regime manager
        logger.info(f"  Creating RegimeManager for {symbol}...")
        regime_manager = RegimeManager(
            warmup_bars=500,
            persist_n=2,
            transition_bars=3,
            bb_threshold_len=200
        )
        regime_manager.setup(timeframes, historicals)

        # Create trade executor
        logger.info(f"  Creating TradeExecutor for {symbol}...")

        # Create a config object for this symbol (mimics LoadEnvironmentVariables)
        class SymbolConfig:
            def __init__(self, env_config, symbol, symbol_config):
                # Copy base config
                self.ACCOUNT_TYPE = env_config.ACCOUNT_TYPE
                self.DAILY_LOSS_LIMIT = env_config.DAILY_LOSS_LIMIT
                self.RESTRICTION_CONF_FOLDER_PATH = env_config.RESTRICTION_CONF_FOLDER_PATH
                self.DEFAULT_CLOSE_TIME = env_config.DEFAULT_CLOSE_TIME
                self.NEWS_RESTRICTION_DURATION = env_config.NEWS_RESTRICTION_DURATION
                self.MARKET_CLOSE_RESTRICTION_DURATION = env_config.MARKET_CLOSE_RESTRICTION_DURATION

                # Symbol-specific config
                self.SYMBOL = symbol
                self.PIP_VALUE = symbol_config['pip_value']
                self.POSITION_SPLIT = symbol_config['position_split']
                self.SCALING_TYPE = symbol_config['scaling_type']
                self.ENTRY_SPACING = symbol_config['entry_spacing']
                self.RISK_PER_GROUP = symbol_config['risk_per_group']

        symbol_env_config = SymbolConfig(env_config, symbol, symbol_config)

        trade_executor = ExecutorBuilder.build_from_config(
            config=symbol_env_config,
            client=client,
            event_bus=None,  # Will be injected later by orchestrator
            logger=logging.getLogger(f'trade-executor-{symbol.lower()}')
        )

        # Store all components for this symbol
        symbol_components[symbol] = {
            'indicator_processor': indicator_processor,
            'regime_manager': regime_manager,
            'strategy_engine': strategy_engine,
            'entry_manager': entry_manager,
            'trade_executor': trade_executor,
            'timeframes': timeframes,
            'historicals': historicals,
        }

        logger.info(f"  ✓ All components loaded for {symbol}")

    logger.info(f"\n=== Components loaded for {len(symbol_components)} symbols ===")

    return symbol_components
