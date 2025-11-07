"""
Orchestrated Live Trading Main Entry Point.

This is the new main entry point that uses the event-driven architecture
with TradingOrchestrator to manage all services and their lifecycle.

Benefits over the old architecture:
- Event-driven design with loose coupling
- Service lifecycle management
- Health monitoring and automatic restart
- Enhanced logging with correlation IDs
- Configuration management with validation
- Comprehensive metrics and monitoring
- Better error isolation and handling
"""

import os
import sys
import logging
from pathlib import Path

from app.clients.mt5.client import create_client_with_retry
from app.data.data_manger import DataSourceManager
from app.entry_manager.manager import EntryManager
from app.indicators.indicator_processor import IndicatorProcessor
from app.regime.regime_manager import RegimeManager
from app.trader.executor_builder import ExecutorBuilder
from app.utils.config import LoadEnvironmentVariables
from app.utils.date_helper import DateHelper
from app.main_backtest import load_strategies_configuration, load_indicator_configuration

# Import the new orchestration infrastructure
from app.infrastructure import (
    TradingOrchestrator,
    ConfigLoader,
    LoggingManager,
    CorrelationContext,
)


def initialize_logging(config_path: str = "config/services.yaml") -> LoggingManager:
    """
    Initialize enhanced logging system with correlation IDs.

    Args:
        config_path: Path to configuration file

    Returns:
        Configured LoggingManager
    """
    try:
        # Try to load logging config from file
        system_config = ConfigLoader.load(config_path)
        logging_manager = LoggingManager.from_config(system_config)
    except FileNotFoundError:
        # Fallback to default configuration
        logging_manager = LoggingManager(
            level="INFO",
            format_type="text",
            include_correlation_ids=False,  # Disable correlation IDs for cleaner logs
            file_output=False
        )

    logging_manager.configure_root_logger()

    # Suppress noisy loggers for cleaner output
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('trading-engine').setLevel(logging.WARNING)
    logging.getLogger('risk-manager').setLevel(logging.WARNING)

    return logging_manager


def initialize_components(env_config: LoadEnvironmentVariables, logger: logging.Logger):
    """
    Initialize all trading components.

    Args:
        env_config: Environment configuration
        logger: Logger instance

    Returns:
        Dictionary with all initialized components
    """
    logger.info("=== Initializing Trading Components ===")

    # MT5 Client
    logger.info("Creating MT5 client...")
    client = create_client_with_retry(env_config.API_BASE_URL)

    # Strategy Engine and Entry Manager
    logger.info("Loading strategy configuration...")
    strategy_engine = load_strategies_configuration(
        folder_path=env_config.CONF_FOLDER_PATH,
        symbol=env_config.SYMBOL
    )

    strategies = {
        name: strategy_engine.get_strategy_info(name)
        for name in strategy_engine.list_available_strategies()
    }

    entry_manager = EntryManager(
        strategies,
        symbol=env_config.SYMBOL,
        pip_value=env_config.PIP_VALUE
    )

    # Indicator Configuration
    logger.info("Loading indicator configuration...")
    indicator_config = load_indicator_configuration(
        folder_path=env_config.CONF_FOLDER_PATH,
        symbol=env_config.SYMBOL
    )

    timeframes = list(indicator_config)
    logger.info(f"Trading {env_config.SYMBOL} with timeframes: {timeframes}")

    # Data Source Manager
    logger.info("Initializing data source manager...")
    data_source = DataSourceManager(
        mode=env_config.TRADE_MODE,
        client=client,
        date_helper=DateHelper()
    )

    # Fetch historical data for indicators
    logger.info("Fetching historical data...")
    historicals = {
        tf: data_source.get_historical_data(
            symbol=env_config.SYMBOL,
            timeframe=tf
        )
        for tf in timeframes
    }

    # Indicator Processor
    logger.info("Initializing indicator processor...")
    indicator_processor = IndicatorProcessor(
        configs=indicator_config,
        historicals=historicals,
        is_bulk=False
    )

    # Regime Manager
    logger.info("Initializing regime manager...")
    regime_manager = RegimeManager(
        warmup_bars=500,
        persist_n=2,
        transition_bars=3,
        bb_threshold_len=200
    )
    regime_manager.setup(timeframes, historicals)

    # Trade Executor
    logger.info("Initializing trade executor...")
    trade_executor = ExecutorBuilder.build_from_config(
        config=env_config,
        client=client,
        logger=logging.getLogger('trade-executor')
    )

    # Date Helper
    date_helper = DateHelper()

    # Get account balance
    account_balance = client.account.get_balance()
    logger.info(f"Account balance: {account_balance}")

    logger.info("✓ All components initialized successfully")

    return {
        "client": client,
        "data_source": data_source,
        "indicator_processor": indicator_processor,
        "regime_manager": regime_manager,
        "strategy_engine": strategy_engine,
        "entry_manager": entry_manager,
        "trade_executor": trade_executor,
        "date_helper": date_helper,
        "timeframes": timeframes,
        "account_balance": account_balance,
    }


def create_orchestrator_config(env_config: LoadEnvironmentVariables, timeframes: list[str]) -> dict:
    """
    Create orchestrator configuration from environment config.

    Args:
        env_config: Environment configuration
        timeframes: List of timeframes to trade

    Returns:
        Configuration dictionary for TradingOrchestrator
    """
    return {
        "symbol": env_config.SYMBOL,
        "timeframes": timeframes,
        "enable_auto_restart": True,  # Auto-restart services on failure
        "health_check_interval": 60,  # Health check every 60 seconds
        "event_history_limit": 1000,
        "log_all_events": False,
        "candle_index": 1,  # Most recent closed candle
        "nbr_bars": 3,
        "track_regime_changes": True,
        "min_rows_required": 3,
        "execution_mode": "immediate",
    }


def main():
    """
    Main entry point for orchestrated live trading.

    This uses the new event-driven architecture with TradingOrchestrator
    to manage all services and their lifecycle.
    """
    # Setup paths
    ROOT_DIR = Path(__file__).parent.parent
    env_path = os.path.join(ROOT_DIR, ".env")
    config_path = os.path.join(ROOT_DIR, "config", "services.yaml")

    # Initialize logging first
    logging_manager = initialize_logging(config_path)
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("Starting Orchestrated Live Trading System")
    logger.info("=" * 80)

    try:
        # Load environment configuration
        logger.info("Loading environment configuration...")
        env_config = LoadEnvironmentVariables(env_path)

        # Initialize all components
        components = initialize_components(env_config, logger)

        # Create orchestrator configuration
        orchestrator_config = create_orchestrator_config(
            env_config,
            components["timeframes"]
        )

        # Try to load system config from file, fallback to dict
        try:
            logger.info(f"Loading system configuration from {config_path}...")
            system_config = ConfigLoader.load(config_path)

            # Create orchestrator from config
            orchestrator = TradingOrchestrator.from_config(
                config=system_config,
                client=components["client"],
                data_source=components["data_source"],
                indicator_processor=components["indicator_processor"],
                regime_manager=components["regime_manager"],
                strategy_engine=components["strategy_engine"],
                entry_manager=components["entry_manager"],
                trade_executor=components["trade_executor"],
                date_helper=components["date_helper"],
                logger=logger
            )
            logger.info("✓ Orchestrator created from configuration file")

        except FileNotFoundError:
            # Fallback to creating orchestrator from dict
            logger.warning(f"Configuration file not found: {config_path}")
            logger.info("Creating orchestrator with default configuration...")

            orchestrator = TradingOrchestrator(
                config=orchestrator_config,
                logger=logger
            )

            orchestrator.initialize(
                client=components["client"],
                data_source=components["data_source"],
                indicator_processor=components["indicator_processor"],
                regime_manager=components["regime_manager"],
                strategy_engine=components["strategy_engine"],
                entry_manager=components["entry_manager"],
                trade_executor=components["trade_executor"],
                date_helper=components["date_helper"]
            )
            logger.info("✓ Orchestrator created with default configuration")

        # Start all services
        logger.info("=" * 80)
        orchestrator.start()
        logger.info("=" * 80)

        # Display initial metrics
        logger.info("\n=== Initial System Status ===")
        health_status = orchestrator.get_service_health()
        logger.info(f"Services Health: {health_status}")

        # Run trading loop with correlation context
        logger.info("\n=== Starting Trading Loop ===")
        logger.info("Press Ctrl+C to stop gracefully")
        logger.info("=" * 80)

        # Get fetch interval from config or use default
        fetch_interval = 5
        try:
            system_config = ConfigLoader.load(config_path)
            fetch_interval = system_config.services.data_fetching.fetch_interval
        except:
            pass

        with CorrelationContext() as correlation_id:
            logger.info(f"Trading session correlation ID: {correlation_id}")
            orchestrator.run(interval_seconds=fetch_interval)

    except KeyboardInterrupt:
        logger.info("\n" + "=" * 80)
        logger.info("Received shutdown signal (Ctrl+C)")
        logger.info("=" * 80)

    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"Fatal error: {e}", exc_info=True)
        logger.error("=" * 80)
        sys.exit(1)

    finally:
        logger.info("\n=== Final System Metrics ===")
        try:
            if 'orchestrator' in locals():
                all_metrics = orchestrator.get_all_metrics()

                logger.info(f"Orchestrator Status: {all_metrics['orchestrator']['status']}")
                logger.info(f"Uptime: {all_metrics['orchestrator']['uptime_seconds']:.2f}s")
                logger.info(f"Services: {all_metrics['orchestrator']['services_count']}")
                logger.info(f"Healthy Services: {all_metrics['orchestrator']['services_healthy']}")

                # Service-specific metrics
                services_metrics = all_metrics['services']
                logger.info(f"\n--- Data & Indicators ---")
                logger.info(f"Data Fetches: {services_metrics['data_fetching']['data_fetches']}")
                logger.info(f"New Candles: {services_metrics['data_fetching']['new_candles_detected']}")
                logger.info(f"Indicators Calculated: {services_metrics['indicator_calculation']['indicators_calculated']}")

                logger.info(f"\n--- Strategy Evaluation ---")
                logger.info(f"Strategies Evaluated: {services_metrics['strategy_evaluation']['strategies_evaluated']}")
                logger.info(f"Entry Signals: {services_metrics['strategy_evaluation']['entry_signals_generated']}")
                logger.info(f"Exit Signals: {services_metrics['strategy_evaluation']['exit_signals_generated']}")

                # Trade execution metrics
                logger.info(f"\n--- Trade Execution ---")
                trade_metrics = services_metrics['trade_execution']
                logger.info(f"Trades Executed: {trade_metrics['trades_executed']}")
                logger.info(f"Orders Placed: {trade_metrics['orders_placed']}")
                logger.info(f"Orders Rejected: {trade_metrics['orders_rejected']}")
                logger.info(f"Positions Closed: {trade_metrics['positions_closed']}")
                logger.info(f"Risk Breaches: {trade_metrics['risk_breaches']}")
                logger.info(f"Execution Errors: {trade_metrics['execution_errors']}")

                # Event bus metrics
                event_bus_metrics = all_metrics['event_bus']
                logger.info(f"\n--- Event Bus ---")
                logger.info(f"Total Events Published: {event_bus_metrics['events_published']}")
                logger.info(f"Event Types: {event_bus_metrics['event_types_subscribed']}")

        except Exception as e:
            logger.error(f"Error displaying final metrics: {e}")

        logger.info("\n" + "=" * 80)
        logger.info("Shutdown complete. Thank you for trading!")
        logger.info("=" * 80)


if __name__ == "__main__":
    main()
