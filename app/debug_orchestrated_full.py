"""
Orchestrated Debug - FULL PIPELINE

This script:
1. Uses DataFetchingService to fetch data
2. Uses IndicatorCalculationService to calculate indicators
3. Uses StrategyEvaluationService to evaluate strategies
4. Uses TradeExecutionService to execute trades
5. Shows complete pipeline with trade execution logs
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
from app.main_backtest import load_indicator_configuration, load_strategies_configuration
from app.entry_manager.manager import EntryManager

# Import event-driven infrastructure
from app.infrastructure import EventBus
from app.services.data_fetching import DataFetchingService
from app.services.indicator_calculation import IndicatorCalculationService
from app.services.strategy_evaluation import StrategyEvaluationService
from app.services.trade_execution import TradeExecutionService
from app.events import (
    EntrySignalEvent,
    ExitSignalEvent,
    TradesReadyEvent,
    OrderPlacedEvent,
    OrderRejectedEvent,
    PositionClosedEvent,
    RiskLimitBreachedEvent,
    TradingBlockedEvent,
    TradingAuthorizedEvent,
)

# Import indicator processor and regime manager
from app.indicators.indicator_processor import IndicatorProcessor
from app.regime.regime_manager import RegimeManager

# Import trade executor components
from app.trader.executor_builder import ExecutorBuilder


def setup_minimal_logging():
    """Setup minimal logging - only show our custom logs."""
    # Disable noisy loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('trading-engine').setLevel(logging.WARNING)
    logging.getLogger('risk-manager').setLevel(logging.WARNING)

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


def main():
    """Main function - full pipeline with trade execution."""
    logger = setup_minimal_logging()

    print_separator()
    print("🔍 ORCHESTRATED DEBUG: FULL PIPELINE (DATA + INDICATORS + STRATEGIES + TRADES)")
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

    # Load strategy configuration
    logger.info(f"\n🎯 Loading strategy configuration...")
    strategy_engine = load_strategies_configuration(
        folder_path=env_config.CONF_FOLDER_PATH,
        symbol=env_config.SYMBOL
    )
    strategies = {
        name: strategy_engine.get_strategy_info(name)
        for name in strategy_engine.list_available_strategies()
    }
    logger.info(f"   ✅ Loaded {len(strategies)} strategies: {list(strategies.keys())}")

    # Create entry manager
    entry_manager = EntryManager(
        strategies,
        symbol=env_config.SYMBOL,
        pip_value=env_config.PIP_VALUE
    )
    logger.info(f"   ✅ Entry manager created")

    # Load indicator configuration
    logger.info(f"\n📈 Loading indicator configuration...")
    indicator_config = load_indicator_configuration(
        folder_path=env_config.CONF_FOLDER_PATH,
        symbol=env_config.SYMBOL
    )
    timeframes = list(indicator_config.keys())
    logger.info(f"   ✅ Loaded indicators for timeframes: {timeframes}")

    # Fetch historical data for indicators
    logger.info(f"\n📚 Fetching historical data for indicator initialization...")
    historicals = {}
    for tf in timeframes:
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
    regime_manager.setup(timeframes, historicals)
    logger.info(f"   ✅ Regime manager initialized")

    # Initialize trade executor
    logger.info(f"\n💼 Initializing trade executor...")
    try:
        trade_executor = ExecutorBuilder.build_from_config(
            config=env_config,
            client=client,
            logger=logging.getLogger("trade-executor")
        )
        logger.info(f"   ✅ Trade executor initialized")
    except Exception as e:
        logger.error(f"   ❌ Trade executor initialization failed: {e}")
        sys.exit(1)

    # Create EventBus
    logger.info(f"\n🚌 Creating EventBus...")
    event_bus = EventBus()

    # Event handlers for all trading events
    entry_count = 0
    exit_count = 0
    orders_placed = 0
    orders_rejected = 0
    positions_closed = 0
    risk_breaches = 0
    trading_blocked_count = 0
    trading_authorized_count = 0

    def on_entry_signal(event: EntrySignalEvent):
        """Handle EntrySignalEvent - show entry details."""
        nonlocal entry_count
        entry_count += 1

        logger.info(f"\n   🟢 ═══════════════════════════════════════════════════════")
        logger.info(f"   🟢 ENTRY SIGNAL #{entry_count}")
        logger.info(f"   🟢 ═══════════════════════════════════════════════════════")
        logger.info(f"      Strategy: {event.strategy_name}")
        logger.info(f"      Symbol:   {event.symbol}")
        logger.info(f"      Direction: {event.direction.upper()}")
        if event.entry_price:
            logger.info(f"      Price:    {event.entry_price:.5f}")
        logger.info(f"   🟢 ═══════════════════════════════════════════════════════\n")

    def on_exit_signal(event: ExitSignalEvent):
        """Handle ExitSignalEvent - show exit details."""
        nonlocal exit_count
        exit_count += 1

        logger.info(f"\n   🔴 ═══════════════════════════════════════════════════════")
        logger.info(f"   🔴 EXIT SIGNAL #{exit_count}")
        logger.info(f"   🔴 ═══════════════════════════════════════════════════════")
        logger.info(f"      Strategy: {event.strategy_name}")
        logger.info(f"      Symbol:   {event.symbol}")
        logger.info(f"      Direction: {event.direction.upper()}")
        logger.info(f"      Reason:   {event.reason}")
        logger.info(f"   🔴 ═══════════════════════════════════════════════════════\n")

    def on_trades_ready(event: TradesReadyEvent):
        """Handle TradesReadyEvent - show trade execution start."""
        logger.info(f"\n   💼 ═══════════════════════════════════════════════════════")
        logger.info(f"   💼 EXECUTING TRADES")
        logger.info(f"   💼 ═══════════════════════════════════════════════════════")
        logger.info(f"      Symbol:  {event.symbol}")
        logger.info(f"      Entries: {event.num_entries}")
        logger.info(f"      Exits:   {event.num_exits}")
        logger.info(f"   💼 ═══════════════════════════════════════════════════════\n")

    def on_trading_authorized(event: TradingAuthorizedEvent):
        """Handle TradingAuthorizedEvent."""
        nonlocal trading_authorized_count
        trading_authorized_count += 1

        logger.info(f"\n   ✅ ═══════════════════════════════════════════════════════")
        logger.info(f"   ✅ TRADING AUTHORIZED #{trading_authorized_count}")
        logger.info(f"   ✅ ═══════════════════════════════════════════════════════")
        logger.info(f"      Symbol: {event.symbol}")
        logger.info(f"      Reason: {event.reason}")
        logger.info(f"   ✅ ═══════════════════════════════════════════════════════\n")

    def on_trading_blocked(event: TradingBlockedEvent):
        """Handle TradingBlockedEvent."""
        nonlocal trading_blocked_count
        trading_blocked_count += 1

        logger.info(f"\n   🚫 ═══════════════════════════════════════════════════════")
        logger.info(f"   🚫 TRADING BLOCKED #{trading_blocked_count}")
        logger.info(f"   🚫 ═══════════════════════════════════════════════════════")
        logger.info(f"      Symbol:  {event.symbol}")
        logger.info(f"      Reasons: {', '.join(event.reasons)}")
        logger.info(f"   🚫 ═══════════════════════════════════════════════════════\n")

    def on_risk_breach(event: RiskLimitBreachedEvent):
        """Handle RiskLimitBreachedEvent."""
        nonlocal risk_breaches
        risk_breaches += 1

        logger.info(f"\n   ⚠️  ═══════════════════════════════════════════════════════")
        logger.info(f"   ⚠️  RISK LIMIT BREACHED #{risk_breaches}")
        logger.info(f"   ⚠️  ═══════════════════════════════════════════════════════")
        logger.info(f"      Symbol:        {event.symbol}")
        logger.info(f"      Limit Type:    {event.limit_type}")
        logger.info(f"      Current Value: {event.current_value}")
        logger.info(f"      Limit Value:   {event.limit_value}")
        logger.info(f"   ⚠️  ═══════════════════════════════════════════════════════\n")

    def on_order_placed(event: OrderPlacedEvent):
        """Handle OrderPlacedEvent."""
        nonlocal orders_placed
        orders_placed += 1

        logger.info(f"\n   📤 ═══════════════════════════════════════════════════════")
        logger.info(f"   📤 ORDER PLACED #{orders_placed}")
        logger.info(f"   📤 ═══════════════════════════════════════════════════════")
        logger.info(f"      Order ID:  {event.order_id}")
        logger.info(f"      Symbol:    {event.symbol}")
        logger.info(f"      Direction: {event.direction}")
        logger.info(f"      Volume:    {event.volume}")
        logger.info(f"      Price:     {event.price}")
        if event.sl:
            logger.info(f"      Stop Loss: {event.sl}")
        if event.tp:
            logger.info(f"      Take Profit: {event.tp}")
        logger.info(f"   📤 ═══════════════════════════════════════════════════════\n")

    def on_order_rejected(event: OrderRejectedEvent):
        """Handle OrderRejectedEvent."""
        nonlocal orders_rejected
        orders_rejected += 1

        logger.info(f"\n   ❌ ═══════════════════════════════════════════════════════")
        logger.info(f"   ❌ ORDER REJECTED #{orders_rejected}")
        logger.info(f"   ❌ ═══════════════════════════════════════════════════════")
        logger.info(f"      Symbol:    {event.symbol}")
        logger.info(f"      Direction: {event.direction}")
        logger.info(f"      Reason:    {event.reason}")
        logger.info(f"   ❌ ═══════════════════════════════════════════════════════\n")

    def on_position_closed(event: PositionClosedEvent):
        """Handle PositionClosedEvent."""
        nonlocal positions_closed
        positions_closed += 1

        logger.info(f"\n   🔒 ═══════════════════════════════════════════════════════")
        logger.info(f"   🔒 POSITION CLOSED #{positions_closed}")
        logger.info(f"   🔒 ═══════════════════════════════════════════════════════")
        logger.info(f"      Position ID: {event.position_id}")
        logger.info(f"      Symbol:      {event.symbol}")
        logger.info(f"      Profit:      {event.profit}")
        logger.info(f"      Reason:      {event.reason}")
        logger.info(f"   🔒 ═══════════════════════════════════════════════════════\n")

    # Subscribe to all events
    event_bus.subscribe(EntrySignalEvent, on_entry_signal)
    event_bus.subscribe(ExitSignalEvent, on_exit_signal)
    event_bus.subscribe(TradesReadyEvent, on_trades_ready)
    event_bus.subscribe(TradingAuthorizedEvent, on_trading_authorized)
    event_bus.subscribe(TradingBlockedEvent, on_trading_blocked)
    event_bus.subscribe(RiskLimitBreachedEvent, on_risk_breach)
    event_bus.subscribe(OrderPlacedEvent, on_order_placed)
    event_bus.subscribe(OrderRejectedEvent, on_order_rejected)
    event_bus.subscribe(PositionClosedEvent, on_position_closed)
    logger.info(f"   ✅ EventBus created and subscribed to all events")

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
        'timeframes': timeframes,
        'candle_index': candle_index,
        'nbr_bars': nbr_bars,
    }

    data_service = DataFetchingService(
        event_bus=event_bus,
        data_source=data_source,
        config=data_config
    )
    logger.info(f"   ✅ DataFetchingService created")

    # Create IndicatorCalculationService
    logger.info(f"\n🧮 Creating IndicatorCalculationService...")
    indicator_config_dict = {
        'symbol': env_config.SYMBOL,
        'timeframes': timeframes,
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

    # Create StrategyEvaluationService
    logger.info(f"\n🎲 Creating StrategyEvaluationService...")
    strategy_config = {
        'symbol': env_config.SYMBOL,
        'evaluation_mode': 'on_new_candle',
        'min_rows_required': 3,
    }

    strategy_service = StrategyEvaluationService(
        event_bus=event_bus,
        strategy_engine=strategy_engine,
        entry_manager=entry_manager,
        config=strategy_config
    )
    logger.info(f"   ✅ StrategyEvaluationService created")

    # Create TradeExecutionService
    logger.info(f"\n💼 Creating TradeExecutionService...")
    trade_config = {
        'symbol': env_config.SYMBOL,
        'execution_mode': 'immediate',
        'batch_size': 1,
    }

    trade_service = TradeExecutionService(
        event_bus=event_bus,
        trade_executor=trade_executor,
        date_helper=DateHelper(),
        config=trade_config
    )
    logger.info(f"   ✅ TradeExecutionService created")

    # Start services
    logger.info(f"\n▶️  Starting services...")
    data_service.start()
    indicator_service.start()
    strategy_service.start()
    trade_service.start()
    logger.info(f"   ✅ All services started")

    print_separator()
    print("🚀 STARTING FULL PIPELINE: DATA → INDICATORS → STRATEGIES → TRADES")
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

            logger.info(f"\n✅ Pipeline triggered: {success_count}/{len(timeframes)} timeframes")

            # Show metrics
            data_metrics = data_service.get_metrics()
            indicator_metrics = indicator_service.get_metrics()
            strategy_metrics = strategy_service.get_metrics()
            trade_metrics = trade_service.get_metrics()

            logger.info(f"\n📊 Metrics Summary:")
            logger.info(f"   ├─ Data fetches:          {data_metrics['data_fetches']}")
            logger.info(f"   ├─ New candles:           {data_metrics['new_candles_detected']}")
            logger.info(f"   ├─ Indicators calculated: {indicator_metrics['indicators_calculated']}")
            logger.info(f"   ├─ Regime changes:        {indicator_metrics['regime_changes_detected']}")
            logger.info(f"   ├─ Strategies evaluated:  {strategy_metrics['strategies_evaluated']}")
            logger.info(f"   ├─ Entry signals:         {strategy_metrics['entry_signals_generated']} (Total: {entry_count})")
            logger.info(f"   ├─ Exit signals:          {strategy_metrics['exit_signals_generated']} (Total: {exit_count})")
            logger.info(f"   ├─ Trades executed:       {trade_metrics['trades_executed']}")
            logger.info(f"   ├─ Orders placed:         {orders_placed}")
            logger.info(f"   ├─ Orders rejected:       {orders_rejected}")
            logger.info(f"   ├─ Positions closed:      {positions_closed}")
            logger.info(f"   ├─ Trading authorized:    {trading_authorized_count}")
            logger.info(f"   ├─ Trading blocked:       {trading_blocked_count}")
            logger.info(f"   └─ Risk breaches:         {risk_breaches}")

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
        trade_service.stop()
        strategy_service.stop()
        indicator_service.stop()
        data_service.stop()
        logger.info(f"   ✅ All services stopped")

        # Final metrics
        data_metrics = data_service.get_metrics()
        indicator_metrics = indicator_service.get_metrics()
        strategy_metrics = strategy_service.get_metrics()
        trade_metrics = trade_service.get_metrics()

        logger.info(f"\n📊 Final Metrics:")
        logger.info(f"   Iterations:             {iteration}")
        logger.info(f"   Data fetches:           {data_metrics['data_fetches']}")
        logger.info(f"   New candles:            {data_metrics['new_candles_detected']}")
        logger.info(f"   Indicators calculated:  {indicator_metrics['indicators_calculated']}")
        logger.info(f"   Regime changes:         {indicator_metrics['regime_changes_detected']}")
        logger.info(f"   Strategies evaluated:   {strategy_metrics['strategies_evaluated']}")
        logger.info(f"   Entry signals:          {entry_count}")
        logger.info(f"   Exit signals:           {exit_count}")
        logger.info(f"   Trades executed:        {trade_metrics['trades_executed']}")
        logger.info(f"   Orders placed:          {orders_placed}")
        logger.info(f"   Orders rejected:        {orders_rejected}")
        logger.info(f"   Positions closed:       {positions_closed}")
        logger.info(f"   Trading authorized:     {trading_authorized_count}")
        logger.info(f"   Trading blocked:        {trading_blocked_count}")
        logger.info(f"   Risk breaches:          {risk_breaches}")

        print_separator()
        logger.info("✅ Debug session finished successfully")
        print_separator()


if __name__ == "__main__":
    main()
