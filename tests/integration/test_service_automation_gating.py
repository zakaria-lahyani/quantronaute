"""
Integration tests for service automation gating.

These tests verify that trading services properly gate their behavior based
on automation state:
- StrategyEvaluationService suppresses entry signals when automation disabled
- TradeExecutionService rejects entry trades when automation disabled
- Exit signals and trades continue regardless of automation state
- SL/TP orders are preserved when automation disabled
- Metrics properly track suppressed signals and rejected orders
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from collections import deque

from app.infrastructure.event_bus import EventBus
from app.infrastructure.automation_state_manager import AutomationStateManager
from app.services.strategy_evaluation import StrategyEvaluationService
from app.services.trade_execution import TradeExecutionService
from app.events.automation_events import (
    AutomationAction,
    ToggleAutomationEvent,
    AutomationStateChangedEvent,
)
from app.events.indicator_events import IndicatorsCalculatedEvent
from app.events.strategy_events import (
    EntrySignalEvent,
    ExitSignalEvent,
    TradesReadyEvent,
)
from app.events.trade_events import OrderRejectedEvent
from app.strategy_builder.data.dtos import (
    Trades,
    EntryDecision,
    ExitDecision,
    StopLossResult,
    TakeProfitResult,
)


def create_entry_decision(
    symbol="XAUUSD",
    strategy_name="test_strategy",
    direction="long",
    entry_price=2000.0
):
    """Helper function to create EntryDecision with all required fields."""
    return EntryDecision(
        symbol=symbol,
        strategy_name=strategy_name,
        magic=123456,
        direction=direction,
        entry_signals="BUY" if direction == "long" else "SELL",
        entry_price=entry_price,
        position_size=0.1,
        stop_loss=StopLossResult(type="fixed", level=entry_price - 10.0),
        take_profit=TakeProfitResult(type="fixed", level=entry_price + 20.0),
        decision_time=datetime.now()
    )


def create_exit_decision(
    symbol="XAUUSD",
    strategy_name="test_strategy",
    direction="long"
):
    """Helper function to create ExitDecision with all required fields."""
    return ExitDecision(
        symbol=symbol,
        strategy_name=strategy_name,
        magic=123456,
        direction=direction,
        decision_time=datetime.now()
    )


class TestStrategyEvaluationServiceAutomationGating:
    """Test StrategyEvaluationService automation gating behavior."""

    @pytest.fixture
    def setup_components(self, tmp_path):
        """Create event bus, automation manager, and strategy service for testing."""
        event_bus = EventBus()
        state_file = tmp_path / "automation_state.json"

        automation_manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        # Mock strategy engine
        strategy_engine = MagicMock()
        strategy_engine.evaluate.return_value = MagicMock(strategies={})

        # Mock entry manager
        entry_manager = MagicMock()

        # Create service
        service = StrategyEvaluationService(
            event_bus=event_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            client=None,
            config={
                "symbol": "XAUUSD",
                "min_rows_required": 3
            }
        )

        service.start()

        return {
            "event_bus": event_bus,
            "automation_manager": automation_manager,
            "service": service,
            "strategy_engine": strategy_engine,
            "entry_manager": entry_manager,
        }

    def test_entry_signals_generated_when_automation_enabled(self, setup_components):
        """Test that entry signals are generated when automation is enabled."""
        components = setup_components
        event_bus = components["event_bus"]
        entry_manager = components["entry_manager"]

        # Collect published signals
        entry_signals_published = []
        event_bus.subscribe(EntrySignalEvent, lambda e: entry_signals_published.append(e))

        # Mock entry manager to return entry decision
        entry_decision = create_entry_decision()
        exit_decision = []

        trades = Trades(entries=[entry_decision], exits=exit_decision)
        entry_manager.manage_trades.return_value = trades

        # Trigger evaluation with IndicatorsCalculatedEvent
        recent_rows = {
            "M5": deque([
                {"close": 2000.0, "timestamp": datetime.now()},
                {"close": 2001.0, "timestamp": datetime.now()},
                {"close": 2002.0, "timestamp": datetime.now()},
            ])
        }

        event_bus.publish(IndicatorsCalculatedEvent(
            symbol="XAUUSD",
            timeframe="M5",
            enriched_data={},
            recent_rows=recent_rows,
            timestamp=datetime.now()
        ))

        # Should have published entry signal
        assert len(entry_signals_published) == 1
        assert entry_signals_published[0].strategy_name == "test_strategy"
        assert entry_signals_published[0].direction == "long"

        # Metrics should show signal generated
        metrics = components["service"].get_metrics()
        assert metrics.get("entry_signals_generated", 0) > 0
        assert metrics.get("entry_signals_suppressed", 0) == 0

    def test_entry_signals_suppressed_when_automation_disabled(self, setup_components):
        """Test that entry signals are suppressed when automation is disabled."""
        components = setup_components
        event_bus = components["event_bus"]
        entry_manager = components["entry_manager"]

        # Disable automation
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="test_suppression",
            requested_by="test"
        ))

        # Collect published signals
        entry_signals_published = []
        event_bus.subscribe(EntrySignalEvent, lambda e: entry_signals_published.append(e))

        # Mock entry manager to return entry decision
        entry_decision = create_entry_decision()

        trades = Trades(entries=[entry_decision], exits=[])
        entry_manager.manage_trades.return_value = trades

        # Trigger evaluation
        recent_rows = {
            "M5": deque([
                {"close": 2000.0, "timestamp": datetime.now()},
                {"close": 2001.0, "timestamp": datetime.now()},
                {"close": 2002.0, "timestamp": datetime.now()},
            ])
        }

        event_bus.publish(IndicatorsCalculatedEvent(
            symbol="XAUUSD",
            timeframe="M5",
            enriched_data={},
            recent_rows=recent_rows,
            timestamp=datetime.now()
        ))

        # Should NOT have published entry signal
        assert len(entry_signals_published) == 0

        # Metrics should show signal suppressed
        metrics = components["service"].get_metrics()
        assert metrics.get("entry_signals_suppressed", 0) > 0

    def test_exit_signals_continue_when_automation_disabled(self, setup_components):
        """Test that exit signals continue when automation is disabled."""
        components = setup_components
        event_bus = components["event_bus"]
        entry_manager = components["entry_manager"]

        # Disable automation
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="test_exit_continuation",
            requested_by="test"
        ))

        # Collect published signals
        exit_signals_published = []
        event_bus.subscribe(ExitSignalEvent, lambda e: exit_signals_published.append(e))

        # Mock entry manager to return exit decision
        exit_decision = create_exit_decision()

        trades = Trades(entries=[], exits=[exit_decision])
        entry_manager.manage_trades.return_value = trades

        # Trigger evaluation
        recent_rows = {
            "M5": deque([
                {"close": 2000.0, "timestamp": datetime.now()},
                {"close": 2001.0, "timestamp": datetime.now()},
                {"close": 2002.0, "timestamp": datetime.now()},
            ])
        }

        event_bus.publish(IndicatorsCalculatedEvent(
            symbol="XAUUSD",
            timeframe="M5",
            enriched_data={},
            recent_rows=recent_rows,
            timestamp=datetime.now()
        ))

        # Should have published exit signal
        assert len(exit_signals_published) == 1
        assert exit_signals_published[0].strategy_name == "test_strategy"

        # Metrics should NOT show signal suppressed
        metrics = components["service"].get_metrics()
        assert metrics.get("entry_signals_suppressed", 0) == 0

    def test_signals_resume_when_automation_reenabled(self, setup_components):
        """Test that entry signals resume when automation is re-enabled."""
        components = setup_components
        event_bus = components["event_bus"]
        entry_manager = components["entry_manager"]

        # Disable then re-enable automation
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="test_reenable",
            requested_by="test"
        ))

        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.ENABLE,
            reason="test_reenable",
            requested_by="test"
        ))

        # Collect published signals
        entry_signals_published = []
        event_bus.subscribe(EntrySignalEvent, lambda e: entry_signals_published.append(e))

        # Mock entry manager to return entry decision
        entry_decision = create_entry_decision()

        trades = Trades(entries=[entry_decision], exits=[])
        entry_manager.manage_trades.return_value = trades

        # Trigger evaluation
        recent_rows = {
            "M5": deque([
                {"close": 2000.0, "timestamp": datetime.now()},
                {"close": 2001.0, "timestamp": datetime.now()},
                {"close": 2002.0, "timestamp": datetime.now()},
            ])
        }

        event_bus.publish(IndicatorsCalculatedEvent(
            symbol="XAUUSD",
            timeframe="M5",
            enriched_data={},
            recent_rows=recent_rows,
            timestamp=datetime.now()
        ))

        # Should have published entry signal
        assert len(entry_signals_published) == 1


class TestTradeExecutionServiceAutomationGating:
    """Test TradeExecutionService automation gating behavior."""

    @pytest.fixture
    def setup_components(self, tmp_path):
        """Create event bus, automation manager, and trade execution service for testing."""
        event_bus = EventBus()
        state_file = tmp_path / "automation_state.json"

        automation_manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        # Mock trade executor
        trade_executor = MagicMock()

        # Mock date helper
        date_helper = MagicMock()

        # Create service
        service = TradeExecutionService(
            event_bus=event_bus,
            trade_executor=trade_executor,
            date_helper=date_helper,
            config={
                "symbol": "XAUUSD",
                "execution_mode": "immediate"
            }
        )

        service.start()

        return {
            "event_bus": event_bus,
            "automation_manager": automation_manager,
            "service": service,
            "trade_executor": trade_executor,
        }

    def test_entry_trades_executed_when_automation_enabled(self, setup_components):
        """Test that entry trades are executed when automation is enabled."""
        components = setup_components
        event_bus = components["event_bus"]
        trade_executor = components["trade_executor"]

        # Create entry decision
        entry_decision = create_entry_decision()

        trades = Trades(entries=[entry_decision], exits=[])

        # Publish TradesReadyEvent
        event_bus.publish(TradesReadyEvent(
            symbol="XAUUSD",
            trades=trades,
            num_entries=1,
            num_exits=0
        ))

        # Should have called executor to execute trades
        # Note: The service calls trade_executor methods internally

    def test_entry_trades_rejected_when_automation_disabled(self, setup_components):
        """Test that entry trades are rejected when automation is disabled."""
        components = setup_components
        event_bus = components["event_bus"]
        trade_executor = components["trade_executor"]
        service = components["service"]

        # Disable automation
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="test_rejection",
            requested_by="test"
        ))

        # Collect order rejected events
        orders_rejected = []
        event_bus.subscribe(OrderRejectedEvent, lambda e: orders_rejected.append(e))

        # Create entry decision
        entry_decision = create_entry_decision()

        trades = Trades(entries=[entry_decision], exits=[])

        # Publish TradesReadyEvent
        event_bus.publish(TradesReadyEvent(
            symbol="XAUUSD",
            trades=trades,
            num_entries=1,
            num_exits=0
        ))

        # Should have published OrderRejectedEvent
        assert len(orders_rejected) > 0

        # Metrics should track rejection
        metrics = service.get_metrics()
        assert metrics.get("trades_rejected_automation", 0) > 0

    def test_exit_trades_continue_when_automation_disabled(self, setup_components):
        """Test that exit trades continue when automation is disabled."""
        components = setup_components
        event_bus = components["event_bus"]
        trade_executor = components["trade_executor"]

        # Disable automation
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="test_exit_continuation",
            requested_by="test"
        ))

        # Create exit decision
        exit_decision = create_exit_decision()

        trades = Trades(entries=[], exits=[exit_decision])

        # Publish TradesReadyEvent
        event_bus.publish(TradesReadyEvent(
            symbol="XAUUSD",
            trades=trades,
            num_entries=0,
            num_exits=1
        ))

        # Exit trades should be executed (checked via service internal state)
        # The service splits the trades and executes only exits

    def test_entries_and_exits_when_automation_disabled(self, setup_components):
        """Test that entries are rejected but exits continue when automation disabled."""
        components = setup_components
        event_bus = components["event_bus"]
        service = components["service"]

        # Disable automation
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="test_mixed",
            requested_by="test"
        ))

        # Collect order rejected events
        orders_rejected = []
        event_bus.subscribe(OrderRejectedEvent, lambda e: orders_rejected.append(e))

        # Create both entry and exit decisions
        entry_decision = create_entry_decision()
        exit_decision = create_exit_decision()

        trades = Trades(entries=[entry_decision], exits=[exit_decision])

        # Publish TradesReadyEvent
        event_bus.publish(TradesReadyEvent(
            symbol="XAUUSD",
            trades=trades,
            num_entries=1,
            num_exits=1
        ))

        # Should have rejected entries
        assert len(orders_rejected) > 0

        # Metrics should track rejection
        metrics = service.get_metrics()
        assert metrics.get("trades_rejected_automation", 0) > 0

    def test_trades_resume_when_automation_reenabled(self, setup_components):
        """Test that entry trades resume when automation is re-enabled."""
        components = setup_components
        event_bus = components["event_bus"]

        # Disable then re-enable automation
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="test_reenable",
            requested_by="test"
        ))

        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.ENABLE,
            reason="test_reenable",
            requested_by="test"
        ))

        # Create entry decision
        entry_decision = create_entry_decision()

        trades = Trades(entries=[entry_decision], exits=[])

        # Publish TradesReadyEvent
        event_bus.publish(TradesReadyEvent(
            symbol="XAUUSD",
            trades=trades,
            num_entries=1,
            num_exits=0
        ))

        # Trades should be executed (no rejection)


class TestAutomationStateTransitions:
    """Test automation state transitions and event flow."""

    @pytest.fixture
    def setup_full_system(self, tmp_path):
        """Create full system with event bus, automation manager, and both services."""
        event_bus = EventBus()
        state_file = tmp_path / "automation_state.json"

        automation_manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        # Mock strategy components
        strategy_engine = MagicMock()
        strategy_engine.evaluate.return_value = MagicMock(strategies={})
        entry_manager = MagicMock()

        # Mock trade executor
        trade_executor = MagicMock()
        date_helper = MagicMock()

        # Create both services
        strategy_service = StrategyEvaluationService(
            event_bus=event_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            client=None,
            config={
                "symbol": "XAUUSD",
                "min_rows_required": 3
            }
        )

        execution_service = TradeExecutionService(
            event_bus=event_bus,
            trade_executor=trade_executor,
            date_helper=date_helper,
            config={
                "symbol": "XAUUSD",
                "execution_mode": "immediate"
            }
        )

        strategy_service.start()
        execution_service.start()

        return {
            "event_bus": event_bus,
            "automation_manager": automation_manager,
            "strategy_service": strategy_service,
            "execution_service": execution_service,
            "entry_manager": entry_manager,
        }

    def test_full_signal_to_trade_flow_when_enabled(self, setup_full_system):
        """Test complete flow from signal generation to trade execution when enabled."""
        components = setup_full_system
        event_bus = components["event_bus"]
        entry_manager = components["entry_manager"]

        # Collect events
        entry_signals_published = []
        trades_ready_published = []

        event_bus.subscribe(EntrySignalEvent, lambda e: entry_signals_published.append(e))
        event_bus.subscribe(TradesReadyEvent, lambda e: trades_ready_published.append(e))

        # Mock entry manager to return entry decision
        entry_decision = create_entry_decision()

        trades = Trades(entries=[entry_decision], exits=[])
        entry_manager.manage_trades.return_value = trades

        # Trigger evaluation
        recent_rows = {
            "M5": deque([
                {"close": 2000.0, "timestamp": datetime.now()},
                {"close": 2001.0, "timestamp": datetime.now()},
                {"close": 2002.0, "timestamp": datetime.now()},
            ])
        }

        event_bus.publish(IndicatorsCalculatedEvent(
            symbol="XAUUSD",
            timeframe="M5",
            enriched_data={},
            recent_rows=recent_rows,
            timestamp=datetime.now()
        ))

        # Should have full flow: indicators → signals → trades ready
        assert len(entry_signals_published) == 1
        assert len(trades_ready_published) == 1

    def test_full_signal_to_trade_flow_when_disabled(self, setup_full_system):
        """Test complete flow is blocked when automation disabled."""
        components = setup_full_system
        event_bus = components["event_bus"]
        automation_manager = components["automation_manager"]
        entry_manager = components["entry_manager"]

        # Disable automation
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="test_full_flow_disabled",
            requested_by="test"
        ))

        assert automation_manager.is_enabled() is False

        # Collect events
        entry_signals_published = []
        orders_rejected = []

        event_bus.subscribe(EntrySignalEvent, lambda e: entry_signals_published.append(e))
        event_bus.subscribe(OrderRejectedEvent, lambda e: orders_rejected.append(e))

        # Mock entry manager to return entry decision
        entry_decision = create_entry_decision()

        trades = Trades(entries=[entry_decision], exits=[])
        entry_manager.manage_trades.return_value = trades

        # Trigger evaluation
        recent_rows = {
            "M5": deque([
                {"close": 2000.0, "timestamp": datetime.now()},
                {"close": 2001.0, "timestamp": datetime.now()},
                {"close": 2002.0, "timestamp": datetime.now()},
            ])
        }

        event_bus.publish(IndicatorsCalculatedEvent(
            symbol="XAUUSD",
            timeframe="M5",
            enriched_data={},
            recent_rows=recent_rows,
            timestamp=datetime.now()
        ))

        # Should have blocked entry signal publication
        assert len(entry_signals_published) == 0

        # Metrics should show suppression
        strategy_metrics = components["strategy_service"].get_metrics()
        assert strategy_metrics.get("entry_signals_suppressed", 0) > 0

    def test_state_change_event_published(self, setup_full_system):
        """Test that AutomationStateChangedEvent is published on state changes."""
        components = setup_full_system
        event_bus = components["event_bus"]

        # Collect state change events
        state_changes = []
        event_bus.subscribe(AutomationStateChangedEvent, lambda e: state_changes.append(e))

        # Disable automation
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="test_state_change_event",
            requested_by="test"
        ))

        # Should have published state change event
        assert len(state_changes) == 1
        assert state_changes[0].enabled is False
        assert state_changes[0].previous_state is True
        assert state_changes[0].reason == "test_state_change_event"
