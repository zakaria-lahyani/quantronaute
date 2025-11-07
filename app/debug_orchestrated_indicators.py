"""
Orchestrated Debug - DATA FETCH + INDICATORS

This script:
1. Uses DataFetchingService to fetch data
2. Uses IndicatorCalculationService to calculate indicators
3. Shows candles with ALL calculated indicators
4. No strategies or trading
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
from app.main_backtest import load_indicator_configuration

# Import event-driven infrastructure
from app.infrastructure import EventBus
from app.services.data_fetching import DataFetchingService
from app.services.indicator_calculation import IndicatorCalculationService
from app.events import NewCandleEvent, IndicatorsCalculatedEvent

# Import indicator processor and regime manager
from app.indicators.indicator_processor import IndicatorProcessor
from app.regime.regime_manager import RegimeManager


def setup_minimal_logging():
    """Setup minimal logging - only show our custom logs."""
    # Disable noisy loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('trading-engine').setLevel(logging.WARNING)

    # Setup our logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[logging.StreamHandler()]
    )

    return logging.getLogger(__name__)


def print_separator(char="=", length=80):
    """Print a separator line."""
    print(char * length)


def print_enriched_candle(timeframe, recent_rows):
    """Print candle with all calculated indicators."""
    if timeframe not in recent_rows or len(recent_rows[timeframe]) == 0:
        print(f"      ⚠️  No data available for {timeframe}")
        return

    # Get the most recent row
    latest_row = recent_rows[timeframe][-1]

    print(f"\n      📊 ENRICHED CANDLE for {timeframe}:")
    print(f"      " + "─" * 70)

    # Show all fields in the row
    for key, value in latest_row.items():
        # Format the value
        if isinstance(value, float):
            value_str = f"{value:.5f}"
        elif isinstance(value, (int, str)):
            value_str = str(value)
        else:
            value_str = str(value)

        # Add emoji for key fields
        if key == 'close':
            emoji = "💰"
        elif key == 'regime':
            emoji = "🎯"
        elif 'sma' in key.lower() or 'ema' in key.lower():
            emoji = "📈"
        elif 'rsi' in key.lower():
            emoji = "📊"
        elif 'bb' in key.lower():
            emoji = "🎸"
        elif 'atr' in key.lower():
            emoji = "📏"
        else:
            emoji = "  "

        print(f"      {emoji} {key:30s} = {value_str}")

    print(f"      " + "─" * 70)


def main():
    """Main function - data fetch + indicators."""
    logger = setup_minimal_logging()

    print_separator()
    print("🔍 ORCHESTRATED DEBUG: DATA FETCH + INDICATORS")
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

    # Load indicator configuration
    logger.info(f"\n📈 Loading indicator configuration...")
    indicator_config = load_indicator_configuration(
        folder_path=env_config.CONF_FOLDER_PATH,
        symbol=env_config.SYMBOL
    )
    logger.info(f"   ✅ Loaded indicators for timeframes: {list(indicator_config.keys())}")

    # Fetch historical data for indicators
    logger.info(f"\n📚 Fetching historical data for indicator initialization...")
    historicals = {}
    for tf in indicator_config.keys():
        hist = data_source.get_historical_data(
            symbol=env_config.SYMBOL,
            timeframe=tf
        )
        historicals[tf] = hist
        logger.info(f"   ✅ {tf}: {len(hist)} historical bars")

    # Initialize indicator processor
    logger.info(f"\n🧮 Initializing indicator processor...")
    indicator_processor = IndicatorProcessor(
        configs=indicator_config,
        historicals=historicals,
        is_bulk=False
    )
    logger.info(f"   ✅ Indicator processor initialized")

    # Initialize regime manager
    logger.info(f"\n🎯 Initializing regime manager...")
    regime_manager = RegimeManager(
        warmup_bars=500,
        persist_n=2,
        transition_bars=3,
        bb_threshold_len=200
    )
    regime_manager.setup(list(indicator_config.keys()), historicals)
    logger.info(f"   ✅ Regime manager initialized")

    # Create EventBus
    logger.info(f"\n🚌 Creating EventBus...")
    event_bus = EventBus()

    # Event handler to display indicators
    def on_indicators_calculated(event: IndicatorsCalculatedEvent):
        """Handle IndicatorsCalculatedEvent - show enriched data."""
        logger.info(f"\n   ✅ [INDICATORS CALCULATED] {event.symbol} {event.timeframe}")
        logger.info(f"      Regime: {event.enriched_data.get('regime')}")
        logger.info(f"      Regime confidence: {event.enriched_data.get('regime_confidence')}")
        logger.info(f"      Is transition: {event.enriched_data.get('is_transition')}")

        # Print the enriched candle with all indicators
        print_enriched_candle(event.timeframe, event.recent_rows)

    # Subscribe to events
    event_bus.subscribe(IndicatorsCalculatedEvent, on_indicators_calculated)
    logger.info(f"   ✅ EventBus created and subscribed")

    # Load config from YAML
    logger.info(f"\n📄 Loading service configuration...")
    config_path = ROOT_DIR / "config" / "services.yaml"
    candle_index = 1
    nbr_bars = 3

    if config_path.exists():
        try:
            import yaml
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)
                data_fetch_config = yaml_config.get('services', {}).get('data_fetching', {})
                candle_index = data_fetch_config.get('candle_index', 1)
                nbr_bars = data_fetch_config.get('nbr_bars', 3)
                logger.info(f"   ✅ Loaded config from: {config_path}")
        except Exception as e:
            logger.warning(f"   ⚠️  Failed to load YAML config: {e}")

    # Create DataFetchingService
    logger.info(f"\n🔄 Creating DataFetchingService...")
    data_config = {
        'symbol': env_config.SYMBOL,
        'timeframes': list(indicator_config.keys()),
        'candle_index': candle_index,
        'nbr_bars': nbr_bars,
    }

    data_service = DataFetchingService(
        event_bus=event_bus,
        data_source=data_source,
        config=data_config
    )
    logger.info(f"   ✅ DataFetchingService created")
    logger.info(f"      Candle index: {candle_index}")
    logger.info(f"      Bars to fetch: {nbr_bars}")

    # Create IndicatorCalculationService
    logger.info(f"\n🧮 Creating IndicatorCalculationService...")
    indicator_config_dict = {
        'symbol': env_config.SYMBOL,
        'timeframes': list(indicator_config.keys()),
        'recent_rows_limit': 6,
        'track_regime_changes': True,
    }

    indicator_service = IndicatorCalculationService(
        event_bus=event_bus,
        indicator_processor=indicator_processor,
        regime_manager=regime_manager,
        config=indicator_config_dict
    )
    logger.info(f"   ✅ IndicatorCalculationService created")

    # Start services
    logger.info(f"\n▶️  Starting services...")
    data_service.start()
    indicator_service.start()
    logger.info(f"   ✅ Services started")

    print_separator()
    print("🚀 STARTING DATA FETCH + INDICATORS LOOP")
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

            # Trigger data fetch (this will trigger the whole chain)
            success_count = data_service.fetch_streaming_data()

            logger.info(f"\n✅ Fetch complete: {success_count}/{len(data_config['timeframes'])} timeframes")

            # Show metrics
            data_metrics = data_service.get_metrics()
            indicator_metrics = indicator_service.get_metrics()

            logger.info(f"\n📊 Metrics:")
            logger.info(f"   Data fetches: {data_metrics['data_fetches']}")
            logger.info(f"   New candles: {data_metrics['new_candles_detected']}")
            logger.info(f"   Indicators calculated: {indicator_metrics['indicators_calculated']}")
            logger.info(f"   Regime changes: {indicator_metrics['regime_changes_detected']}")

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

        # Stop services
        logger.info(f"\n⏹️  Stopping services...")
        indicator_service.stop()
        data_service.stop()
        logger.info(f"   ✅ Services stopped")

        # Final metrics
        data_metrics = data_service.get_metrics()
        indicator_metrics = indicator_service.get_metrics()

        logger.info(f"\n📊 Final Metrics:")
        logger.info(f"   Iterations: {iteration}")
        logger.info(f"   Data fetches: {data_metrics['data_fetches']}")
        logger.info(f"   New candles: {data_metrics['new_candles_detected']}")
        logger.info(f"   Indicators calculated: {indicator_metrics['indicators_calculated']}")
        logger.info(f"   Regime changes: {indicator_metrics['regime_changes_detected']}")

        print_separator()
        logger.info("✅ Debug session finished successfully")
        print_separator()


if __name__ == "__main__":
    main()
