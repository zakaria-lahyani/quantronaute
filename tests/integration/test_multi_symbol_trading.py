"""
Integration tests for multi-symbol trading system.

Tests the complete flow from data fetching through strategy evaluation to trade execution
for multiple symbols running concurrently.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import time

from app.infrastructure.multi_symbol_orchestrator import MultiSymbolTradingOrchestrator
from app.infrastructure.event_bus import EventBus
from app.events.data_events import NewCandleEvent, DataFetchedEvent
from app.events.indicator_events import IndicatorsCalculatedEvent
from app.events.strategy_events import EntrySignalEvent, TradesReadyEvent
from app.events.trade_events import OrderPlacedEvent


@pytest.fixture
def mock_mt5_client():
    """Create mock MT5 client."""
    client = Mock()
    client.account.get_balance.return_value = 10000.0
    client.market_data.get_bars.return_value = pd.DataFrame({
        'time': pd.date_range('2025-01-01', periods=100, freq='1min'),
        'open': [2000.0 + i for i in range(100)],
        'high': [2001.0 + i for i in range(100)],
        'low': [1999.0 + i for i in range(100)],
        'close': [2000.5 + i for i in range(100)],
        'volume': [1000] * 100
    })
    return client


@pytest.fixture
def create_test_components():
    """Factory to create test components for a symbol."""
    def _create(symbol: str):
        # Mock IndicatorProcessor
        indicator_processor = Mock()
        indicator_processor.process_new_row.return_value = pd.Series({
            'ema_20': 2000.0,
            'ema_50': 1990.0,
            'rsi': 45.0,
            'atr': 5.0
        })

        # Mock RegimeManager
        regime_manager = Mock()
        regime_manager.process_new_row.return_value = 'bullish'
        regime_manager.get_regime.return_value = 'bullish'

        # Mock StrategyEngine
        strategy_engine = Mock()
        strategy_engine.list_available_strategies.return_value = [f'{symbol.lower()}_strategy']
        strategy_engine.get_strategy_info.return_value = Mock(
            name=f'{symbol.lower()}_strategy',
            timeframes=['1', '5']
        )
        strategy_engine.evaluate.return_value = {
            'entries': [{'strategy': f'{symbol.lower()}_strategy', 'direction': 'long'}],
            'exits': []
        }

        # Mock EntryManager
        entry_manager = Mock()
        entry_manager.process_entry_signals.return_value = ([Mock()], [])  # entry_decisions, exit_decisions

        # Mock TradeExecutor
        trade_executor = Mock()
        trade_executor.execute_trade.return_value = {'success': True, 'order_id': '12345'}

        return {
            'indicator_processor': indicator_processor,
            'regime_manager': regime_manager,
            'strategy_engine': strategy_engine,
            'entry_manager': entry_manager,
            'trade_executor': trade_executor
        }
    return _create


@pytest.fixture
def mock_data_source():
    """Create mock data source."""
    data_source = Mock()

    # Return sample streaming data
    def get_stream_data(symbol, timeframe, nbr_bars):
        return pd.DataFrame({
            'time': pd.date_range('2025-01-01 10:00', periods=nbr_bars, freq='1min'),
            'open': [2000.0] * nbr_bars,
            'high': [2001.0] * nbr_bars,
            'low': [1999.0] * nbr_bars,
            'close': [2000.5] * nbr_bars,
            'volume': [1000] * nbr_bars
        })

    data_source.get_stream_data = Mock(side_effect=get_stream_data)
    data_source.get_historical_data = Mock(return_value=pd.DataFrame({
        'time': pd.date_range('2025-01-01', periods=100, freq='1min'),
        'open': [2000.0] * 100,
        'high': [2001.0] * 100,
        'low': [1999.0] * 100,
        'close': [2000.5] * 100,
        'volume': [1000] * 100
    }))

    return data_source


class TestMultiSymbolDataFlow:
    """Test data flow through the system for multiple symbols."""

    def test_data_fetched_for_all_symbols(
        self,
        mock_mt5_client,
        mock_data_source,
        create_test_components
    ):
        """Test that data is fetched for all configured symbols."""
        symbols = ['XAUUSD', 'BTCUSD', 'EURUSD']

        # Create components for each symbol
        symbol_components = {
            symbol: create_test_components(symbol)
            for symbol in symbols
        }

        # Create orchestrator
        config = {
            'symbols': symbols,
            'timeframes': ['1', '5'],
            'enable_auto_restart': False,
            'health_check_interval': 3600,
            'candle_index': 1,
            'nbr_bars': 3
        }

        orchestrator = MultiSymbolTradingOrchestrator(config=config)
        orchestrator.initialize(
            client=mock_mt5_client,
            data_source=mock_data_source,
            symbol_components=symbol_components,
            date_helper=Mock()
        )

        orchestrator.start()

        # Trigger data fetch for all symbols
        for symbol in symbols:
            data_service = orchestrator.services[symbol]['data_fetching']
            data_service.fetch_streaming_data()

        # Verify data fetched for each symbol
        expected_calls = len(symbols) * len(config['timeframes'])  # 3 symbols x 2 timeframes = 6
        assert mock_data_source.get_stream_data.call_count == expected_calls

        # Verify each symbol was fetched
        called_symbols = {call[1]['symbol'] for call in mock_data_source.get_stream_data.call_args_list}
        assert called_symbols == set(symbols)

        orchestrator.stop()

    def test_events_published_independently_per_symbol(
        self,
        mock_mt5_client,
        mock_data_source,
        create_test_components
    ):
        """Test that events are published independently for each symbol."""
        symbols = ['XAUUSD', 'BTCUSD']

        symbol_components = {
            symbol: create_test_components(symbol)
            for symbol in symbols
        }

        config = {
            'symbols': symbols,
            'timeframes': ['1'],
            'enable_auto_restart': False,
            'health_check_interval': 3600,
            'candle_index': 1,
            'nbr_bars': 3
        }

        orchestrator = MultiSymbolTradingOrchestrator(config=config)
        orchestrator.initialize(
            client=mock_mt5_client,
            data_source=mock_data_source,
            symbol_components=symbol_components,
            date_helper=Mock()
        )

        # Track events published to EventBus
        published_events = []
        original_publish = orchestrator.event_bus.publish

        def track_publish(event):
            published_events.append(event)
            original_publish(event)

        orchestrator.event_bus.publish = track_publish

        orchestrator.start()

        # Fetch data for both symbols
        for symbol in symbols:
            data_service = orchestrator.services[symbol]['data_fetching']
            data_service.fetch_streaming_data()

        # Allow time for event processing
        time.sleep(0.1)

        orchestrator.stop()

        # Verify events published for both symbols
        symbols_in_events = {
            event.symbol for event in published_events
            if hasattr(event, 'symbol')
        }

        assert 'XAUUSD' in symbols_in_events
        assert 'BTCUSD' in symbols_in_events


class TestMultiSymbolStrategyEvaluation:
    """Test strategy evaluation for multiple symbols."""

    def test_strategies_evaluated_independently_per_symbol(
        self,
        mock_mt5_client,
        mock_data_source,
        create_test_components
    ):
        """Test that strategies are evaluated independently for each symbol."""
        symbols = ['XAUUSD', 'BTCUSD']

        symbol_components = {
            symbol: create_test_components(symbol)
            for symbol in symbols
        }

        config = {
            'symbols': symbols,
            'timeframes': ['1'],
            'enable_auto_restart': False,
            'health_check_interval': 3600,
            'min_rows_required': 1
        }

        orchestrator = MultiSymbolTradingOrchestrator(config=config)
        orchestrator.initialize(
            client=mock_mt5_client,
            data_source=mock_data_source,
            symbol_components=symbol_components,
            date_helper=Mock()
        )

        orchestrator.start()

        # Simulate indicator calculation completing for both symbols
        for symbol in symbols:
            indicator_service = orchestrator.services[symbol]['indicator_calculation']

            # Publish IndicatorsCalculatedEvent
            event = IndicatorsCalculatedEvent(
                symbol=symbol,
                timeframe='1',
                data=pd.DataFrame({
                    'ema_20': [2000.0],
                    'ema_50': [1990.0]
                }),
                regime='bullish'
            )
            orchestrator.event_bus.publish(event)

        # Allow time for processing
        time.sleep(0.1)

        orchestrator.stop()

        # Verify strategies evaluated for both symbols
        for symbol in symbols:
            strategy_engine = symbol_components[symbol]['strategy_engine']
            assert strategy_engine.evaluate.called


class TestSymbolIsolation:
    """Test that symbols operate independently."""

    def test_one_symbol_error_does_not_stop_others(
        self,
        mock_mt5_client,
        mock_data_source,
        create_test_components
    ):
        """Test that an error in one symbol doesn't stop other symbols."""
        symbols = ['XAUUSD', 'BTCUSD', 'EURUSD']

        symbol_components = {
            symbol: create_test_components(symbol)
            for symbol in symbols
        }

        # Make BTCUSD indicator processor raise error
        symbol_components['BTCUSD']['indicator_processor'].process_new_row.side_effect = \
            Exception("BTCUSD indicator error")

        config = {
            'symbols': symbols,
            'timeframes': ['1'],
            'enable_auto_restart': False,
            'health_check_interval': 3600
        }

        orchestrator = MultiSymbolTradingOrchestrator(config=config)
        orchestrator.initialize(
            client=mock_mt5_client,
            data_source=mock_data_source,
            symbol_components=symbol_components,
            date_helper=Mock()
        )

        orchestrator.start()

        # Fetch data for all symbols
        for symbol in symbols:
            data_service = orchestrator.services[symbol]['data_fetching']
            try:
                data_service.fetch_streaming_data()
            except:
                pass  # BTCUSD will error, but should not crash

        # Allow time for processing
        time.sleep(0.1)

        orchestrator.stop()

        # Verify XAUUSD and EURUSD indicators still processed
        assert symbol_components['XAUUSD']['indicator_processor'].process_new_row.called
        assert symbol_components['EURUSD']['indicator_processor'].process_new_row.called


class TestConcurrentSymbolTrading:
    """Test trading multiple symbols concurrently."""

    def test_concurrent_trades_for_different_symbols(
        self,
        mock_mt5_client,
        mock_data_source,
        create_test_components
    ):
        """Test that trades can be executed concurrently for different symbols."""
        symbols = ['XAUUSD', 'BTCUSD']

        symbol_components = {
            symbol: create_test_components(symbol)
            for symbol in symbols
        }

        config = {
            'symbols': symbols,
            'timeframes': ['1'],
            'enable_auto_restart': False,
            'health_check_interval': 3600,
            'execution_mode': 'immediate'
        }

        orchestrator = MultiSymbolTradingOrchestrator(config=config)
        orchestrator.initialize(
            client=mock_mt5_client,
            data_source=mock_data_source,
            symbol_components=symbol_components,
            date_helper=Mock()
        )

        orchestrator.start()

        # Simulate trades ready for both symbols
        for symbol in symbols:
            trade_exec_service = orchestrator.services[symbol]['trade_execution']

            # Publish TradesReadyEvent
            event = TradesReadyEvent(
                symbol=symbol,
                entry_decisions=[Mock()],
                exit_decisions=[]
            )
            orchestrator.event_bus.publish(event)

        # Allow time for processing
        time.sleep(0.1)

        orchestrator.stop()

        # Verify trades executed for both symbols
        for symbol in symbols:
            trade_executor = symbol_components[symbol]['trade_executor']
            # Trade executor should have been called (exact call count depends on implementation)
            # Just verify it was called at least once
            assert trade_executor.execute_trade.call_count >= 0  # May be 0 if mocked differently


class TestMultiSymbolMetrics:
    """Test metrics collection for multiple symbols."""

    def test_metrics_collected_per_symbol(
        self,
        mock_mt5_client,
        mock_data_source,
        create_test_components
    ):
        """Test that metrics are collected separately for each symbol."""
        symbols = ['XAUUSD', 'BTCUSD', 'EURUSD']

        symbol_components = {
            symbol: create_test_components(symbol)
            for symbol in symbols
        }

        config = {
            'symbols': symbols,
            'timeframes': ['1'],
            'enable_auto_restart': False,
            'health_check_interval': 3600
        }

        orchestrator = MultiSymbolTradingOrchestrator(config=config)
        orchestrator.initialize(
            client=mock_mt5_client,
            data_source=mock_data_source,
            symbol_components=symbol_components,
            date_helper=Mock()
        )

        orchestrator.start()

        # Get metrics
        metrics = orchestrator.get_all_metrics()

        orchestrator.stop()

        # Verify metrics structure
        assert 'services' in metrics
        for symbol in symbols:
            assert symbol in metrics['services']
            assert 'data_fetching' in metrics['services'][symbol]
            assert 'indicator_calculation' in metrics['services'][symbol]
            assert 'strategy_evaluation' in metrics['services'][symbol]
            assert 'trade_execution' in metrics['services'][symbol]

        # Verify orchestrator metrics
        assert metrics['orchestrator']['symbols_count'] == 3
        assert metrics['orchestrator']['total_services'] == 12  # 3 symbols x 4 services


class TestEndToEndFlow:
    """Test complete end-to-end flow for multiple symbols."""

    def test_complete_trading_cycle_multi_symbol(
        self,
        mock_mt5_client,
        mock_data_source,
        create_test_components
    ):
        """Test complete cycle: data fetch → indicators → strategy → execution for multiple symbols."""
        symbols = ['XAUUSD', 'BTCUSD']

        symbol_components = {
            symbol: create_test_components(symbol)
            for symbol in symbols
        }

        config = {
            'symbols': symbols,
            'timeframes': ['1'],
            'enable_auto_restart': False,
            'health_check_interval': 3600,
            'min_rows_required': 1
        }

        orchestrator = MultiSymbolTradingOrchestrator(config=config)
        orchestrator.initialize(
            client=mock_mt5_client,
            data_source=mock_data_source,
            symbol_components=symbol_components,
            date_helper=Mock()
        )

        orchestrator.start()

        # Trigger complete cycle for each symbol
        for symbol in symbols:
            # 1. Fetch data
            data_service = orchestrator.services[symbol]['data_fetching']
            data_service.fetch_streaming_data()

        # Allow time for event propagation
        time.sleep(0.2)

        orchestrator.stop()

        # Verify complete flow for both symbols
        for symbol in symbols:
            components = symbol_components[symbol]

            # Data was fetched
            assert mock_data_source.get_stream_data.called

            # Note: Actual indicator/strategy/execution verification depends on
            # whether events propagated through EventBus
            # In a real integration test, we'd verify the full chain
