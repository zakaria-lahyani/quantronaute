"""
Multi-Symbol Live Trading Main Entry Point.

This is the new main entry point for trading multiple symbols simultaneously.
Each symbol gets its own set of event-driven services for complete isolation.

Benefits:
- Trade multiple symbols concurrently (e.g., XAUUSD + BTCUSD + EURUSD)
- Symbol-specific configurations (pip_value, position_split, etc.)
- Isolated services per symbol (one symbol crash doesn't affect others)
- Shared EventBus for cross-symbol correlation tracking
- Per-symbol health monitoring and metrics
- Automatic service restart on failures

Configuration:
- Set SYMBOLS=XAUUSD,BTCUSD,EURUSD in .env file
- Optional: Symbol-specific configs like XAUUSD_PIP_VALUE=100
- Strategies loaded from config/strategies/{symbol}/
- Indicators loaded from config/indicators/{symbol}/
"""

import os
import sys
import logging
from pathlib import Path

from app.clients.mt5.client import create_client_with_retry
from app.data.data_manger import DataSourceManager
from app.utils.config import LoadEnvironmentVariables
from app.utils.date_helper import DateHelper
from app.utils.multi_symbol_loader import load_all_components_for_symbols

# Import the new multi-symbol infrastructure
from app.infrastructure.multi_symbol_orchestrator import MultiSymbolTradingOrchestrator
from app.infrastructure import (
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

    return logging_manager


def main():
    """
    Main entry point for multi-symbol live trading.

    This uses the new event-driven architecture with MultiSymbolTradingOrchestrator
    to manage services for multiple symbols concurrently.
    """
    # Setup paths
    ROOT_DIR = Path(__file__).parent.parent
    env_path = os.path.join(ROOT_DIR, ".env")
    config_path = os.path.join(ROOT_DIR, "config", "services.yaml")

    # Initialize logging first
    logging_manager = initialize_logging(config_path)
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("Starting Multi-Symbol Live Trading System")
    logger.info("=" * 80)

    try:
        # Load environment configuration
        logger.info("Loading environment configuration...")
        env_config = LoadEnvironmentVariables(env_path)

        # Display configured symbols
        logger.info(f"\nConfigured symbols: {env_config.SYMBOLS}")
        for symbol in env_config.SYMBOLS:
            symbol_config = env_config.get_symbol_config(symbol)
            logger.info(f"  {symbol}:")
            logger.info(f"    - PIP_VALUE: {symbol_config['pip_value']}")
            logger.info(f"    - POSITION_SPLIT: {symbol_config['position_split']}")
            logger.info(f"    - SCALING_TYPE: {symbol_config['scaling_type']}")
            logger.info(f"    - ENTRY_SPACING: {symbol_config['entry_spacing']}")
            logger.info(f"    - RISK_PER_GROUP: {symbol_config['risk_per_group']}")

        # Create shared components
        logger.info("\n=== Initializing Shared Components ===")

        # MT5 Client (shared)
        logger.info("Creating MT5 client...")
        client = create_client_with_retry(env_config.API_BASE_URL)

        # Data Source Manager (shared)
        logger.info("Initializing data source manager...")
        data_source = DataSourceManager(
            mode=env_config.TRADE_MODE,
            client=client,
            date_helper=DateHelper()
        )

        # Date Helper (shared)
        date_helper = DateHelper()

        # Get account balance
        account_balance = client.account.get_balance()
        logger.info(f"Account balance: {account_balance}")

        logger.info("✓ Shared components initialized")

        # Load components for all symbols
        symbol_components = load_all_components_for_symbols(
            symbols=env_config.SYMBOLS,
            env_config=env_config,
            client=client,
            data_source=data_source,
            date_helper=date_helper,
            logger=logger
        )

        # Load system configuration
        logger.info(f"\nLoading system configuration from {config_path}...")
        try:
            system_config = ConfigLoader.load(config_path)
            logger.info("✓ System configuration loaded")
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {config_path}")
            logger.info("Using default configuration...")
            # Create minimal config
            from app.infrastructure.config import SystemConfig, TradingConfig
            system_config = SystemConfig(
                trading=TradingConfig(
                    symbols=env_config.SYMBOLS,
                    timeframes=["1", "5", "15"]
                )
            )

        # Create multi-symbol orchestrator
        logger.info("\n=== Creating Multi-Symbol Orchestrator ===")
        orchestrator = MultiSymbolTradingOrchestrator.from_config(
            config=system_config,
            client=client,
            data_source=data_source,
            symbol_components=symbol_components,
            date_helper=date_helper,
            logger=logger
        )
        logger.info("✓ Orchestrator created successfully")

        # Start all services
        logger.info("\n" + "=" * 80)
        orchestrator.start()
        logger.info("=" * 80)

        # Display initial metrics
        logger.info("\n=== Initial System Status ===")
        health_status = orchestrator.get_service_health()
        for symbol, services in health_status.items():
            healthy_count = sum(1 for h in services.values() if h)
            total = len(services)
            logger.info(f"{symbol}: {healthy_count}/{total} services healthy")

        # Run trading loop with correlation context
        logger.info("\n=== Starting Trading Loop ===")
        logger.info("Press Ctrl+C to stop gracefully")
        logger.info("=" * 80)

        # Get fetch interval from config or use default
        fetch_interval = 5
        try:
            fetch_interval = system_config.services.data_fetching.fetch_interval
        except:
            pass

        logger.info(f"Fetch interval: {fetch_interval} seconds\n")

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
                logger.info(f"Symbols: {all_metrics['orchestrator']['symbols']}")
                logger.info(f"Total Services: {all_metrics['orchestrator']['total_services']}")

                # Per-symbol metrics
                for symbol in all_metrics['orchestrator']['symbols']:
                    logger.info(f"\n--- {symbol} Metrics ---")
                    symbol_services = all_metrics['services'][symbol]

                    # Data & Indicators
                    data_metrics = symbol_services['data_fetching']
                    logger.info(f"Data Fetches: {data_metrics.get('data_fetches', 0)}")
                    logger.info(f"New Candles: {data_metrics.get('new_candles_detected', 0)}")

                    indicator_metrics = symbol_services['indicator_calculation']
                    logger.info(f"Indicators Calculated: {indicator_metrics.get('indicators_calculated', 0)}")

                    # Strategy Evaluation
                    strategy_metrics = symbol_services['strategy_evaluation']
                    logger.info(f"Strategies Evaluated: {strategy_metrics.get('strategies_evaluated', 0)}")
                    logger.info(f"Entry Signals: {strategy_metrics.get('entry_signals_generated', 0)}")
                    logger.info(f"Exit Signals: {strategy_metrics.get('exit_signals_generated', 0)}")

                    # Trade Execution
                    trade_metrics = symbol_services['trade_execution']
                    logger.info(f"Trades Executed: {trade_metrics.get('trades_executed', 0)}")
                    logger.info(f"Orders Placed: {trade_metrics.get('orders_placed', 0)}")
                    logger.info(f"Orders Rejected: {trade_metrics.get('orders_rejected', 0)}")
                    logger.info(f"Positions Closed: {trade_metrics.get('positions_closed', 0)}")
                    logger.info(f"Risk Breaches: {trade_metrics.get('risk_breaches', 0)}")

                # Event bus metrics
                event_bus_metrics = all_metrics['event_bus']
                logger.info(f"\n--- Event Bus ---")
                logger.info(f"Total Events Published: {event_bus_metrics.get('events_published', 0)}")
                logger.info(f"Event Types: {event_bus_metrics.get('event_types_subscribed', 0)}")

        except Exception as e:
            logger.error(f"Error displaying final metrics: {e}")

        logger.info("\n" + "=" * 80)
        logger.info("Shutdown complete. Thank you for trading!")
        logger.info("=" * 80)


if __name__ == "__main__":
    main()
