"""
Minimal orchestrated system - DATA FETCH ONLY

This script:
1. Uses the DataFetchingService (event-driven)
2. Shows only data fetch logs
3. Displays what data is fetched and which row is selected
4. No indicators, strategies, or trading
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.clients.mt5.client import create_client_with_retry
from app.data.data_manger import DataSourceManager
from app.utils.config import LoadEnvironmentVariables
from app.utils.date_helper import DateHelper

# Import event-driven infrastructure
from app.infrastructure import EventBus, LoggingManager
from app.services.data_fetching import DataFetchingService
from app.events import DataFetchedEvent, NewCandleEvent


def setup_minimal_logging():
    """Setup minimal logging - only show our custom logs."""
    # Disable noisy loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)

    # Setup our logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',  # Simple format - just the message
        handlers=[logging.StreamHandler()]
    )

    return logging.getLogger(__name__)


def print_separator(char="=", length=80):
    """Print a separator line."""
    print(char * length)


def main():
    """Main function - data fetch only."""
    logger = setup_minimal_logging()

    print_separator()
    print("🔍 ORCHESTRATED DATA FETCH DEBUG")
    print("   (Event-Driven - DataFetchingService Only)")
    print_separator()

    # Load environment configuration
    env_path = ROOT_DIR / ".env"
    logger.info(f"\n📁 Loading configuration from: {env_path}")

    if not env_path.exists():
        logger.error(f"❌ ERROR: .env file not found at {env_path}")
        sys.exit(1)

    env_config = LoadEnvironmentVariables(str(env_path))

    # Display configuration
    logger.info(f"\n⚙️  Configuration:")
    logger.info(f"   Symbol: {env_config.SYMBOL}")
    logger.info(f"   API URL: {env_config.API_BASE_URL}")

    # Get timeframes
    timeframes = os.getenv("TIMEFRAMES", "1,5,15").split(",")
    timeframes = [tf.strip() for tf in timeframes]
    logger.info(f"   Timeframes: {timeframes}")

    # Create components
    logger.info(f"\n🔌 Connecting to MT5 API...")
    try:
        client = create_client_with_retry(env_config.API_BASE_URL)
        logger.info(f"   ✅ Connected successfully")
    except Exception as e:
        logger.error(f"   ❌ Connection failed: {e}")
        sys.exit(1)

    logger.info(f"\n📊 Initializing data source manager...")
    data_source = DataSourceManager(
        mode=env_config.TRADE_MODE,
        client=client,
        date_helper=DateHelper()
    )
    logger.info(f"   ✅ Data source initialized")

    # Create EventBus
    logger.info(f"\n🚌 Creating EventBus...")
    event_bus = EventBus()

    # Event handlers to display what's happening
    def on_data_fetched(event: DataFetchedEvent):
        """Handle DataFetchedEvent - show what was fetched."""
        logger.info(f"\n   📥 [EVENT] DataFetchedEvent: {event.symbol} {event.timeframe}")
        logger.info(f"      Bars received: {event.num_bars}")

        if not event.bars.empty:
            latest = event.bars.iloc[-1]
            logger.info(f"      Latest bar: close={latest['close']:.5f}, volume={latest.get('tick_volume', 'N/A')}")

    def on_new_candle(event: NewCandleEvent):
        """Handle NewCandleEvent - show the new candle."""
        logger.info(f"\n   🆕 [EVENT] NewCandleEvent: {event.symbol} {event.timeframe}")
        logger.info(f"      Time: {event.bar.name}")
        logger.info(f"      Open: {event.get_open():.5f}")
        logger.info(f"      High: {event.get_high():.5f}")
        logger.info(f"      Low: {event.get_low():.5f}")
        logger.info(f"      Close: {event.get_close():.5f}")
        logger.info(f"      Volume: {event.bar.get('tick_volume', 'N/A')}")

    # Subscribe to events
    event_bus.subscribe(DataFetchedEvent, on_data_fetched)
    event_bus.subscribe(NewCandleEvent, on_new_candle)
    logger.info(f"   ✅ EventBus created and subscribed")

    # Create DataFetchingService
    logger.info(f"\n🔄 Creating DataFetchingService...")

    # Try to load config from YAML, fallback to defaults
    config_path = ROOT_DIR / "config" / "services.yaml"
    candle_index = 1
    nbr_bars = 3
    retry_attempts = 3
    fetch_interval = 30

    if config_path.exists():
        try:
            import yaml
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)
                data_fetch_config = yaml_config.get('services', {}).get('data_fetching', {})
                candle_index = data_fetch_config.get('candle_index', 1)
                nbr_bars = data_fetch_config.get('nbr_bars', 3)
                retry_attempts = data_fetch_config.get('retry_attempts', 3)
                fetch_interval = data_fetch_config.get('fetch_interval', 30)
                logger.info(f"   📄 Loaded config from: {config_path}")
        except Exception as e:
            logger.warning(f"   ⚠️  Failed to load YAML config: {e}")
            logger.info(f"   Using default values")
    else:
        logger.info(f"   ℹ️  Config file not found, using defaults")

    config = {
        'symbol': env_config.SYMBOL,
        'timeframes': timeframes,
        'candle_index': candle_index,
        'nbr_bars': nbr_bars,
        'retry_attempts': retry_attempts,
        'fetch_interval': fetch_interval,
    }

    data_service = DataFetchingService(
        event_bus=event_bus,
        data_source=data_source,
        config=config
    )

    logger.info(f"   ✅ DataFetchingService created")
    logger.info(f"      Candle index: {config['candle_index']} ({'most recent closed' if config['candle_index'] == 1 else f'{config['candle_index']} bars back'})")
    logger.info(f"      Bars to fetch: {config['nbr_bars']}")

    # Start the service
    logger.info(f"\n▶️  Starting DataFetchingService...")
    data_service.start()
    logger.info(f"   ✅ Service started")

    print_separator()
    print("🚀 STARTING DATA FETCH LOOP")
    print_separator()
    print("Press Ctrl+C to stop\n")

    iteration = 0

    try:
        import time

        while True:
            iteration += 1

            print_separator("─")
            logger.info(f"📍 ITERATION {iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print_separator("─")

            logger.info(f"\n🔄 Fetching data for all timeframes...")

            # Trigger data fetch
            success_count = data_service.fetch_streaming_data()

            logger.info(f"\n✅ Fetch complete: {success_count}/{len(timeframes)} timeframes successful")

            # Show metrics
            metrics = data_service.get_metrics()
            logger.info(f"\n📊 Service Metrics:")
            logger.info(f"   Total fetches: {metrics['data_fetches']}")
            logger.info(f"   New candles detected: {metrics['new_candles_detected']}")
            logger.info(f"   Fetch errors: {metrics['fetch_errors']}")

            # Wait
            wait_time = 30
            logger.info(f"\n⏳ Waiting {wait_time} seconds before next fetch...")
            print_separator("─")

            time.sleep(wait_time)

    except KeyboardInterrupt:
        logger.info("\n")
        print_separator()
        logger.info("🛑 STOPPED BY USER")
        print_separator()

        # Stop service
        logger.info(f"\n⏹️  Stopping DataFetchingService...")
        data_service.stop()
        logger.info(f"   ✅ Service stopped")

        # Final metrics
        metrics = data_service.get_metrics()
        logger.info(f"\n📊 Final Metrics:")
        logger.info(f"   Iterations: {iteration}")
        logger.info(f"   Total fetches: {metrics['data_fetches']}")
        logger.info(f"   New candles: {metrics['new_candles_detected']}")
        logger.info(f"   Errors: {metrics['fetch_errors']}")

        print_separator()
        logger.info("✅ Debug session finished successfully")
        print_separator()


if __name__ == "__main__":
    main()
