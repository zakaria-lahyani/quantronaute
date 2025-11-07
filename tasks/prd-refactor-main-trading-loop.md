# PRD: Refactor Main Trading Loop - Extract Services for Better Testability

## Document Information
- **Feature Name**: Main Trading Loop Refactoring
- **Version**: 1.0
- **Created**: 2025-01-06
- **Status**: Draft
- **Priority**: High
- **Target Release**: Sprint 1-2

---

## Introduction/Overview

The current main trading loop (`main_live_regime.py`) is a monolithic orchestrator with 318 lines of code that directly manages data fetching, indicator processing, regime detection, strategy evaluation, and trade execution. This creates tight coupling, makes testing difficult, and limits extensibility.

This refactoring will decompose the monolithic loop into independent, event-driven services that communicate through a publish/subscribe pattern. Each service will have a single, well-defined responsibility and be independently testable.

### Problem Statement
- **Testing**: Current main loop is difficult to test in isolation due to tight coupling with 7+ packages
- **Maintainability**: Changes to one area require understanding the entire flow
- **Extensibility**: Adding new features requires modifying the main loop
- **Coupling**: Direct dependencies between components limit flexibility
- **Reusability**: Logic cannot be reused in different contexts (e.g., backtesting vs live vs paper trading)

### Solution
Implement an event-driven architecture with extracted services:
1. **DataFetchingService** - Market data retrieval
2. **IndicatorCalculationService** - Technical indicator processing
3. **StrategyEvaluationService** - Trading strategy evaluation
4. **TradeExecutionService** - Trade execution and risk management
5. **EventBus** - Central event publishing/subscription mechanism
6. **TradingOrchestrator** - Lightweight coordinator managing service lifecycle

---

## Goals

1. **Improve Testability**: Each service can be tested independently with mocked dependencies
2. **Reduce Coupling**: Services communicate through events, not direct method calls
3. **Enhance Maintainability**: Single responsibility per service, clear boundaries
4. **Enable Extensibility**: New services can be added without modifying existing code
5. **Increase Reusability**: Services can be composed differently for various trading modes
6. **Maintain Performance**: Refactoring should not degrade system performance
7. **Comprehensive Testing**: Achieve >90% test coverage for new services

---

## User Stories

### As a Developer
1. **US-1**: As a developer, I want to test the data fetching logic independently so that I can verify data retrieval without running the entire trading system.

2. **US-2**: As a developer, I want to mock external dependencies (MT5 API, database) so that I can run tests in isolation without external services.

3. **US-3**: As a developer, I want to add new services (e.g., NotificationService, LoggingService) without modifying existing services so that the system remains extensible.

4. **US-4**: As a developer, I want clear service interfaces so that I can understand each component's responsibilities and contracts.

5. **US-5**: As a developer, I want comprehensive test coverage so that I can refactor with confidence.

### As a System Architect
6. **US-6**: As a system architect, I want loosely coupled services so that individual components can be replaced or upgraded independently.

7. **US-7**: As a system architect, I want event-driven communication so that services remain decoupled and can be distributed in the future.

8. **US-8**: As a system architect, I want service health monitoring so that I can detect and recover from failures.

### As a Trader/End User
9. **US-9**: As a trader, I want the refactored system to maintain the same trading behavior so that my strategies continue to work correctly.

10. **US-10**: As a trader, I want better error handling and recovery so that temporary failures don't stop my trading system.

---

## Functional Requirements

### Core Services

#### FR-1: DataFetchingService
**Description**: Responsible for fetching market data from data sources.

**Requirements**:
1. FR-1.1: The service MUST fetch streaming data for configured symbols and timeframes
2. FR-1.2: The service MUST publish a `DataFetchedEvent` when new data is available
3. FR-1.3: The service MUST handle data source failures gracefully with retry logic
4. FR-1.4: The service MUST support both live and backtest data sources
5. FR-1.5: The service MUST detect new candle formation and trigger appropriate events
6. FR-1.6: The service MUST validate fetched data before publishing events
7. FR-1.7: The service MUST log all data fetching operations with timestamps

**Interface**:
```python
class DataFetchingService(EventDrivenService):
    def fetch_streaming_data(self, symbol: str, timeframes: List[str]) -> None
    def on_new_candle(self, timeframe: str, bar: pd.Series) -> None
```

**Events Published**:
- `DataFetchedEvent(symbol, timeframe, bars, timestamp)`
- `NewCandleEvent(symbol, timeframe, bar, timestamp)`
- `DataFetchErrorEvent(symbol, timeframe, error, timestamp)`

#### FR-2: IndicatorCalculationService
**Description**: Responsible for calculating technical indicators and market regime.

**Requirements**:
1. FR-2.1: The service MUST subscribe to `NewCandleEvent` from DataFetchingService
2. FR-2.2: The service MUST process indicators for the received bar
3. FR-2.3: The service MUST update regime detection for the timeframe
4. FR-2.4: The service MUST enrich the bar with indicator values and regime data
5. FR-2.5: The service MUST maintain recent rows buffer for each timeframe
6. FR-2.6: The service MUST publish `IndicatorsCalculatedEvent` with enriched data
7. FR-2.7: The service MUST handle indicator calculation errors without stopping the system
8. FR-2.8: The service MUST support both batch (warmup) and incremental (streaming) modes

**Interface**:
```python
class IndicatorCalculationService(EventDrivenService):
    def on_new_candle(self, event: NewCandleEvent) -> None
    def calculate_indicators(self, timeframe: str, bar: pd.Series) -> dict
    def update_regime(self, timeframe: str, bar: pd.Series) -> dict
```

**Events Subscribed**:
- `NewCandleEvent`

**Events Published**:
- `IndicatorsCalculatedEvent(symbol, timeframe, enriched_data, recent_rows, timestamp)`
- `RegimeChangedEvent(symbol, timeframe, old_regime, new_regime, timestamp)`
- `IndicatorCalculationErrorEvent(symbol, timeframe, error, timestamp)`

#### FR-3: StrategyEvaluationService
**Description**: Responsible for evaluating trading strategies and generating signals.

**Requirements**:
1. FR-3.1: The service MUST subscribe to `IndicatorsCalculatedEvent`
2. FR-3.2: The service MUST evaluate all active strategies when recent rows are updated
3. FR-3.3: The service MUST check strategy activation rules (schedule, conditions)
4. FR-3.4: The service MUST generate entry signals for long and short directions
5. FR-3.5: The service MUST generate exit signals for open positions
6. FR-3.6: The service MUST publish `EntrySignalEvent` for each entry opportunity
7. FR-3.7: The service MUST publish `ExitSignalEvent` for each exit condition
8. FR-3.8: The service MUST track which strategies are currently active
9. FR-3.9: The service MUST log all signal generation with strategy details

**Interface**:
```python
class StrategyEvaluationService(EventDrivenService):
    def on_indicators_calculated(self, event: IndicatorsCalculatedEvent) -> None
    def evaluate_strategies(self, recent_rows: dict) -> StrategyEvaluationResult
    def check_entry_conditions(self, strategy: TradingStrategy, recent_rows: dict) -> bool
    def check_exit_conditions(self, strategy: TradingStrategy, recent_rows: dict) -> bool
```

**Events Subscribed**:
- `IndicatorsCalculatedEvent`

**Events Published**:
- `EntrySignalEvent(strategy_name, symbol, direction, timestamp)`
- `ExitSignalEvent(strategy_name, symbol, direction, timestamp)`
- `StrategyActivatedEvent(strategy_name, timestamp)`
- `StrategyDeactivatedEvent(strategy_name, reason, timestamp)`
- `StrategyEvaluationErrorEvent(strategy_name, error, timestamp)`

#### FR-4: TradeExecutionService
**Description**: Responsible for executing trades, managing risk, and interfacing with the broker.

**Requirements**:
1. FR-4.1: The service MUST subscribe to `EntrySignalEvent` and `ExitSignalEvent`
2. FR-4.2: The service MUST calculate risk parameters (position size, SL, TP) for entry signals
3. FR-4.3: The service MUST check trading restrictions (news, market close, risk limits)
4. FR-4.4: The service MUST filter duplicate trades
5. FR-4.5: The service MUST execute entry orders through the broker interface
6. FR-4.6: The service MUST close positions based on exit signals
7. FR-4.7: The service MUST monitor daily P&L and enforce loss limits
8. FR-4.8: The service MUST publish `OrderPlacedEvent` for successful orders
9. FR-4.9: The service MUST publish `OrderRejectedEvent` for rejected orders
10. FR-4.10: The service MUST publish `PositionClosedEvent` for closed positions
11. FR-4.11: The service MUST maintain trading context (authorization, risk status)
12. FR-4.12: The service MUST log all trading operations with full details

**Interface**:
```python
class TradeExecutionService(EventDrivenService):
    def on_entry_signal(self, event: EntrySignalEvent) -> None
    def on_exit_signal(self, event: ExitSignalEvent) -> None
    def calculate_trade_parameters(self, signal: EntrySignalEvent) -> EntryDecision
    def execute_entry(self, entry_decision: EntryDecision) -> None
    def execute_exit(self, exit_signal: ExitSignalEvent) -> None
    def check_trading_authorization(self) -> bool
```

**Events Subscribed**:
- `EntrySignalEvent`
- `ExitSignalEvent`

**Events Published**:
- `OrderPlacedEvent(order_id, symbol, direction, volume, price, sl, tp, timestamp)`
- `OrderRejectedEvent(symbol, direction, reason, timestamp)`
- `PositionClosedEvent(position_id, symbol, profit, timestamp)`
- `RiskLimitBreachedEvent(limit_type, current_value, limit_value, timestamp)`
- `TradingAuthorizedEvent(timestamp)`
- `TradingBlockedEvent(reasons, timestamp)`

### Event Bus Infrastructure

#### FR-5: EventBus
**Description**: Central event publishing and subscription mechanism.

**Requirements**:
1. FR-5.1: The EventBus MUST support event registration by event type
2. FR-5.2: The EventBus MUST allow services to subscribe to specific event types
3. FR-5.3: The EventBus MUST allow services to unsubscribe from events
4. FR-5.4: The EventBus MUST deliver events to all registered subscribers
5. FR-5.5: The EventBus MUST support synchronous event delivery (same thread)
6. FR-5.6: The EventBus MUST support asynchronous event delivery (background thread) - optional
7. FR-5.7: The EventBus MUST handle subscriber errors without affecting other subscribers
8. FR-5.8: The EventBus MUST log all published events with metadata
9. FR-5.9: The EventBus MUST track event delivery metrics (count, timing)
10. FR-5.10: The EventBus MUST support event filtering by criteria
11. FR-5.11: The EventBus MUST maintain event history for debugging (configurable retention)

**Interface**:
```python
class EventBus:
    def subscribe(self, event_type: Type[Event], handler: Callable[[Event], None]) -> str
    def unsubscribe(self, subscription_id: str) -> None
    def publish(self, event: Event) -> None
    def publish_async(self, event: Event) -> None
    def get_subscribers(self, event_type: Type[Event]) -> List[Callable]
    def clear_history(self) -> None
    def get_event_history(self, event_type: Optional[Type[Event]] = None) -> List[Event]
```

#### FR-6: Event Models
**Description**: Define event data structures for all system events.

**Requirements**:
1. FR-6.1: All events MUST inherit from base `Event` class
2. FR-6.2: All events MUST include a timestamp field
3. FR-6.3: All events MUST include an event_id (UUID) for tracking
4. FR-6.4: All events MUST be immutable (frozen dataclass)
5. FR-6.5: All events MUST be serializable (for logging/debugging)
6. FR-6.6: Events MUST include all necessary context for handlers

**Event Hierarchy**:
```python
@dataclass(frozen=True)
class Event:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class DataFetchedEvent(Event):
    symbol: str
    timeframe: str
    bars: pd.DataFrame

@dataclass(frozen=True)
class NewCandleEvent(Event):
    symbol: str
    timeframe: str
    bar: pd.Series

# ... (other event types)
```

### Service Orchestration

#### FR-7: TradingOrchestrator
**Description**: Lightweight coordinator managing service lifecycle and system startup/shutdown.

**Requirements**:
1. FR-7.1: The orchestrator MUST initialize all services in correct order
2. FR-7.2: The orchestrator MUST inject dependencies into services (DI)
3. FR-7.3: The orchestrator MUST start services and subscribe them to events
4. FR-7.4: The orchestrator MUST handle graceful shutdown on termination signal
5. FR-7.5: The orchestrator MUST provide health check endpoint for monitoring
6. FR-7.6: The orchestrator MUST restart failed services (configurable retry policy)
7. FR-7.7: The orchestrator MUST log service lifecycle events
8. FR-7.8: The orchestrator MUST expose service metrics (uptime, event counts)

**Interface**:
```python
class TradingOrchestrator:
    def __init__(self, config: TradingConfig, event_bus: EventBus)
    def initialize_services(self) -> None
    def start(self) -> None
    def stop(self) -> None
    def restart_service(self, service_name: str) -> None
    def get_service_health(self) -> dict
    def get_service_metrics(self) -> dict
```

#### FR-8: Service Base Class
**Description**: Abstract base class for all event-driven services.

**Requirements**:
1. FR-8.1: All services MUST inherit from `EventDrivenService`
2. FR-8.2: Services MUST implement `start()` and `stop()` lifecycle methods
3. FR-8.3: Services MUST implement `health_check()` for monitoring
4. FR-8.4: Services MUST have access to EventBus for publishing events
5. FR-8.5: Services MUST have access to Logger for logging
6. FR-8.6: Services MUST handle errors gracefully and publish error events
7. FR-8.7: Services MUST track their own metrics (events processed, errors)

**Interface**:
```python
class EventDrivenService(ABC):
    def __init__(self, event_bus: EventBus, logger: Logger, config: dict)

    @abstractmethod
    def start(self) -> None
        """Initialize and start the service."""

    @abstractmethod
    def stop(self) -> None
        """Gracefully stop the service."""

    @abstractmethod
    def health_check(self) -> HealthStatus
        """Return service health status."""

    def publish_event(self, event: Event) -> None
        """Publish event to event bus."""

    def get_metrics(self) -> dict
        """Return service metrics."""
```

### Testing Infrastructure

#### FR-9: Test Fixtures and Mocks
**Description**: Provide comprehensive test infrastructure for all services.

**Requirements**:
1. FR-9.1: Create `MockEventBus` for testing event publishing/subscription
2. FR-9.2: Create `MockDataSource` for testing data fetching
3. FR-9.3: Create `MockBroker` for testing trade execution
4. FR-9.4: Create test fixtures for common objects (bars, indicators, strategies)
5. FR-9.5: Create builders for constructing test events
6. FR-9.6: Create assertion helpers for validating events

**Test Fixtures Location**: `tests/fixtures/`

**Mock Implementations**: `tests/mocks/`

#### FR-10: Service Unit Tests
**Description**: Unit tests for each service in isolation.

**Requirements**:
1. FR-10.1: Each service MUST have unit tests with >90% coverage
2. FR-10.2: Tests MUST use mocked dependencies (no external services)
3. FR-10.3: Tests MUST verify event publishing for all scenarios
4. FR-10.4: Tests MUST verify error handling
5. FR-10.5: Tests MUST verify service lifecycle (start/stop)

**Test Organization**:
```
tests/services/
├── test_data_fetching_service.py
├── test_indicator_calculation_service.py
├── test_strategy_evaluation_service.py
└── test_trade_execution_service.py
```

#### FR-11: Integration Tests
**Description**: End-to-end tests for service interactions.

**Requirements**:
1. FR-11.1: Test complete trading cycle from data fetch to trade execution
2. FR-11.2: Test event flow between all services
3. FR-11.3: Test error propagation and recovery
4. FR-11.4: Test concurrent event handling
5. FR-11.5: Test service restart and recovery
6. FR-11.6: Use real EventBus but mocked external dependencies

**Test Organization**:
```
tests/integration/
├── test_trading_cycle.py
├── test_event_flow.py
└── test_service_orchestration.py
```

### Configuration

#### FR-12: Service Configuration
**Description**: Configuration system for services.

**Requirements**:
1. FR-12.1: Each service MUST have its own configuration section
2. FR-12.2: Configuration MUST be loaded from YAML files
3. FR-12.3: Configuration MUST be validated using Pydantic models
4. FR-12.4: Configuration MUST support environment variable overrides
5. FR-12.5: Invalid configuration MUST prevent system startup with clear errors

**Configuration Structure**:
```yaml
services:
  data_fetching:
    enabled: true
    fetch_interval: 5  # seconds
    retry_attempts: 3
    retry_backoff: 1.0

  indicator_calculation:
    enabled: true
    recent_rows_limit: 6

  strategy_evaluation:
    enabled: true
    evaluation_mode: "on_new_candle"

  trade_execution:
    enabled: true
    daily_loss_limit: 1000.0
    max_positions: 10

event_bus:
  mode: synchronous  # or asynchronous
  event_history_limit: 1000
  log_all_events: true
```

### Logging and Monitoring

#### FR-13: Enhanced Logging
**Description**: Structured logging for all services and events.

**Requirements**:
1. FR-13.1: All services MUST use structured logging (JSON format)
2. FR-13.2: All events MUST be logged with full context
3. FR-13.3: Logs MUST include correlation IDs for tracing event flow
4. FR-13.4: Logs MUST include service name, event type, timestamp
5. FR-13.5: Log levels MUST be configurable per service
6. FR-13.6: Logs MUST be written to both file and console (configurable)

**Log Format**:
```json
{
  "timestamp": "2025-01-06T14:30:25.123Z",
  "service": "DataFetchingService",
  "level": "INFO",
  "event_type": "NewCandleEvent",
  "event_id": "uuid-here",
  "symbol": "EURUSD",
  "timeframe": "1",
  "message": "New candle detected"
}
```

#### FR-14: Metrics Collection
**Description**: Collect and expose service metrics.

**Requirements**:
1. FR-14.1: Each service MUST track events processed count
2. FR-14.2: Each service MUST track errors count
3. FR-14.3: Each service MUST track processing time (average, min, max)
4. FR-14.4: EventBus MUST track total events published
5. FR-14.5: Metrics MUST be accessible via API endpoint
6. FR-14.6: Metrics MUST be logged periodically

**Metrics Output**:
```python
{
  "DataFetchingService": {
    "events_published": 1234,
    "errors": 5,
    "uptime_seconds": 3600,
    "avg_processing_time_ms": 45
  },
  # ... other services
}
```

---

## Non-Goals (Out of Scope)

The following are explicitly **NOT** included in this refactoring:

1. **Broker Abstraction**: This refactoring will NOT add support for multiple brokers (remains MT5-only)
2. **Distributed Architecture**: Services will run in the same process (no microservices, no message queue)
3. **Async/Await**: This refactoring will NOT convert to async IO (remains synchronous)
4. **Database Integration**: No database for event persistence (in-memory event history only)
5. **UI/Dashboard**: No web interface or dashboard for monitoring
6. **Portfolio Management**: Multi-symbol trading remains out of scope
7. **Historical Refactoring**: Existing packages (indicators, regime, strategy_builder) will NOT be refactored
8. **Performance Optimization**: Focus is on architecture, not performance improvements
9. **Advanced Event Features**: No event replay, no event sourcing, no CQRS
10. **Service Discovery**: No dynamic service registration (services configured at startup)

---

## Design Considerations

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      TradingOrchestrator                         │
│  (Manages service lifecycle, dependency injection, monitoring)   │
└────────────┬────────────────────────────────────────────────────┘
             │
             ├──> Initializes & Manages Services
             │
┌────────────▼────────────────────────────────────────────────────┐
│                          EventBus                                │
│     (Central pub/sub mechanism for service communication)        │
└─────┬──────┬──────┬──────┬──────────────────────────────────────┘
      │      │      │      │
      │      │      │      │
┌─────▼──────▼──────▼──────▼──────────────────────────────────────┐
│                                                                   │
│  ┌──────────────────┐    ┌──────────────────────────────────┐  │
│  │ DataFetching     │───>│ IndicatorCalculation             │  │
│  │ Service          │    │ Service                          │  │
│  │                  │    │                                  │  │
│  │ Publishes:       │    │ Subscribes: NewCandleEvent       │  │
│  │ - DataFetchedEvent│   │ Publishes: IndicatorsCalculated  │  │
│  │ - NewCandleEvent │    │           RegimeChangedEvent     │  │
│  └──────────────────┘    └──────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────┐    ┌──────────────────┐  │
│  │ StrategyEvaluation               │───>│ TradeExecution   │  │
│  │ Service                          │    │ Service          │  │
│  │                                  │    │                  │  │
│  │ Subscribes: IndicatorsCalculated │    │ Subscribes:      │  │
│  │ Publishes: EntrySignalEvent      │    │ - EntrySignal    │  │
│  │           ExitSignalEvent        │    │ - ExitSignal     │  │
│  └──────────────────────────────────┘    │ Publishes:       │  │
│                                           │ - OrderPlaced    │  │
│                                           │ - PositionClosed │  │
│                                           └──────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### Event Flow Sequence

```
1. DataFetchingService fetches market data
2. Detects new candle → Publishes NewCandleEvent
3. IndicatorCalculationService receives NewCandleEvent
4. Calculates indicators & regime → Publishes IndicatorsCalculatedEvent
5. StrategyEvaluationService receives IndicatorsCalculatedEvent
6. Evaluates strategies → Publishes EntrySignalEvent/ExitSignalEvent
7. TradeExecutionService receives signals
8. Calculates risk & executes trades → Publishes OrderPlacedEvent/PositionClosedEvent
```

### Service Communication Pattern

Services follow **Observer Pattern** through EventBus:
- **Loose Coupling**: Services don't know about each other
- **Scalability**: New services can be added without modifying existing ones
- **Testability**: Each service can be tested with mock EventBus
- **Flexibility**: Event flow can be modified by changing subscriptions

### Error Handling Strategy

1. **Service-Level Errors**:
   - Catch exceptions within service methods
   - Publish error events (e.g., `DataFetchErrorEvent`)
   - Log with full context
   - Continue processing (don't crash)

2. **Event Handler Errors**:
   - EventBus wraps handler calls in try/catch
   - Logs handler errors
   - Continues delivering to other subscribers

3. **Critical Errors**:
   - TradingOrchestrator monitors for critical errors
   - Can restart individual services
   - Can stop entire system if needed

### Dependency Injection

Services receive dependencies through constructor:
```python
# Example: DataFetchingService
def __init__(
    self,
    event_bus: EventBus,
    data_source_manager: DataSourceManager,
    date_helper: DateHelper,
    logger: Logger,
    config: DataFetchingConfig
):
    self.event_bus = event_bus
    self.data_source = data_source_manager
    # ...
```

**Benefits**:
- Easy to mock dependencies in tests
- Clear service dependencies
- Flexible configuration

---

## Technical Considerations

### Implementation Strategy

**Phase 1: Core Infrastructure (Week 1)**
1. Implement `Event` base class and all event types
2. Implement `EventBus` with synchronous delivery
3. Implement `EventDrivenService` base class
4. Create test infrastructure (MockEventBus, fixtures)

**Phase 2: Service Extraction (Week 2-3)**
1. Implement `DataFetchingService`
2. Implement `IndicatorCalculationService`
3. Implement `StrategyEvaluationService`
4. Implement `TradeExecutionService`
5. Write unit tests for each service (>90% coverage)

**Phase 3: Orchestration (Week 4)**
1. Implement `TradingOrchestrator`
2. Implement service configuration system
3. Implement health checks and metrics
4. Write integration tests

**Phase 4: Migration (Week 5)**
1. Create new main entry point using orchestrator
2. Run parallel testing (old vs new system)
3. Validate identical behavior
4. Switch to new system
5. Deprecate old main_live_regime.py

### File Structure

```
app/
├── events/
│   ├── __init__.py
│   ├── base.py                  # Event base class
│   ├── data_events.py           # Data-related events
│   ├── indicator_events.py      # Indicator-related events
│   ├── strategy_events.py       # Strategy-related events
│   └── trade_events.py          # Trade-related events
├── services/
│   ├── __init__.py
│   ├── base.py                  # EventDrivenService base
│   ├── data_fetching.py         # DataFetchingService
│   ├── indicator_calculation.py # IndicatorCalculationService
│   ├── strategy_evaluation.py   # StrategyEvaluationService
│   └── trade_execution.py       # TradeExecutionService
├── infrastructure/
│   ├── __init__.py
│   ├── event_bus.py             # EventBus implementation
│   └── orchestrator.py          # TradingOrchestrator
├── config/
│   └── services.yaml            # Service configuration
└── main_orchestrated.py         # New main entry point

tests/
├── fixtures/
│   ├── __init__.py
│   ├── events.py                # Event fixtures
│   ├── market_data.py           # Market data fixtures
│   └── strategies.py            # Strategy fixtures
├── mocks/
│   ├── __init__.py
│   ├── event_bus.py             # MockEventBus
│   ├── data_source.py           # MockDataSource
│   └── broker.py                # MockBroker
├── services/
│   ├── test_data_fetching_service.py
│   ├── test_indicator_calculation_service.py
│   ├── test_strategy_evaluation_service.py
│   └── test_trade_execution_service.py
└── integration/
    ├── test_trading_cycle.py
    └── test_event_flow.py
```

### Dependencies

**New Dependencies**:
- No new external packages required
- Uses existing packages: pandas, pydantic, logging

**Internal Dependencies**:
- Services depend on EventBus (injected)
- Services depend on existing packages (indicators, regime, strategy_builder, trader)
- Services do NOT depend on each other directly

### Backward Compatibility

**Breaking Changes** (Complete rewrite approach):
1. New main entry point: `main_orchestrated.py`
2. New configuration file: `config/services.yaml`
3. Old `main_live_regime.py` will be deprecated but kept for reference

**Migration Path**:
1. Keep both systems running in parallel during testing
2. Validate identical trading behavior
3. Switch to new system after validation
4. Remove old main loop after 1-2 weeks of stable operation

### Performance Considerations

**Event Bus Overhead**:
- Synchronous event delivery: minimal overhead (<1ms per event)
- Event history: limited to 1000 events (configurable)
- No serialization overhead (in-memory objects)

**Service Overhead**:
- Each service adds ~1-2ms processing time
- Total overhead: ~5-10ms per trading cycle
- Acceptable for 5-second loop interval

**Memory**:
- Event history: ~1MB for 1000 events
- Service instances: ~5MB total
- No significant memory increase

---

## Success Metrics

### Code Quality Metrics
1. **Test Coverage**: Achieve >90% test coverage for all new services
2. **Cyclomatic Complexity**: Each service method should have complexity <10
3. **Lines of Code**: Each service should be <300 lines (excluding tests)
4. **Code Duplication**: <5% code duplication across services

### Performance Metrics
1. **Trading Cycle Time**: Maintain current cycle time (<500ms)
2. **Event Delivery Time**: <1ms average event delivery
3. **Service Processing Time**: <50ms per service per cycle
4. **Memory Usage**: <10% increase from current baseline

### Reliability Metrics
1. **Error Rate**: <0.1% error rate for event handling
2. **Service Uptime**: 99.9% uptime for each service
3. **Event Delivery Success**: 100% event delivery to active subscribers

### Maintainability Metrics
1. **Service Independence**: Each service can be tested independently
2. **Easy Testing**: Developers can write tests without external dependencies
3. **Clear Interfaces**: All service interfaces documented with examples
4. **Quick Onboarding**: New developers can understand a service in <30 minutes

### Behavioral Metrics
1. **Trading Accuracy**: 100% identical trading decisions compared to old system
2. **Signal Latency**: <10ms difference in signal generation time
3. **No Regressions**: Zero regressions in strategy behavior

---

## Open Questions

1. **Q1**: Should EventBus support asynchronous event delivery in Phase 1, or defer to future phase?
   - **Recommendation**: Start with synchronous only, add async in Phase 2 if needed

2. **Q2**: Should events be persisted to disk for debugging, or kept in-memory only?
   - **Recommendation**: In-memory with configurable history limit (1000 events default)

3. **Q3**: Should services be able to cancel or modify events in transit?
   - **Recommendation**: No, events should be immutable and non-cancellable for simplicity

4. **Q4**: How should service startup order be determined?
   - **Recommendation**: Explicit ordering in TradingOrchestrator based on dependencies

5. **Q5**: Should the old main_live_regime.py be deleted immediately or kept for reference?
   - **Recommendation**: Keep for 1-2 weeks as reference, then move to `deprecated/` folder

6. **Q6**: Should we add metrics export (Prometheus, Grafana) in this phase?
   - **Recommendation**: Defer to future phase, focus on basic metrics collection first

7. **Q7**: How should configuration validation errors be handled at startup?
   - **Recommendation**: Fail fast with clear error messages, prevent system start

8. **Q8**: Should services have their own configuration files or single file?
   - **Recommendation**: Single `config/services.yaml` file with sections per service

9. **Q9**: How detailed should event history be (full objects or summaries)?
   - **Recommendation**: Store full event objects for debugging, add summary view method

10. **Q10**: Should integration tests use real or mocked data sources?
    - **Recommendation**: Mocked data sources for speed and reliability

---

## Appendix

### Example Event Flow (Complete Trading Cycle)

```python
# 1. DataFetchingService fetches data
stream_data = data_source.get_stream_data("EURUSD", "1", 3)
event_bus.publish(DataFetchedEvent(symbol="EURUSD", timeframe="1", bars=stream_data))

# 2. Detect new candle
if new_candle_detected(stream_data):
    event_bus.publish(NewCandleEvent(symbol="EURUSD", timeframe="1", bar=stream_data.iloc[-1]))

# 3. IndicatorCalculationService receives NewCandleEvent
def on_new_candle(event: NewCandleEvent):
    regime_data = regime_manager.update(event.timeframe, event.bar)
    enriched_row = indicator_processor.process_new_row(event.timeframe, event.bar, regime_data)
    recent_rows = indicator_processor.get_recent_rows()
    event_bus.publish(IndicatorsCalculatedEvent(
        symbol=event.symbol,
        timeframe=event.timeframe,
        enriched_data=enriched_row,
        recent_rows=recent_rows
    ))

# 4. StrategyEvaluationService receives IndicatorsCalculatedEvent
def on_indicators_calculated(event: IndicatorsCalculatedEvent):
    strategy_results = strategy_engine.evaluate(event.recent_rows)
    for strategy_name, result in strategy_results.strategies.items():
        if result.entry.long:
            event_bus.publish(EntrySignalEvent(
                strategy_name=strategy_name,
                symbol=event.symbol,
                direction="long"
            ))

# 5. TradeExecutionService receives EntrySignalEvent
def on_entry_signal(event: EntrySignalEvent):
    entry_decision = entry_manager.calculate_entry_decision(
        strategy_name=event.strategy_name,
        symbol=event.symbol,
        direction=event.direction,
        # ... other params
    )
    if can_trade():
        result = trader.create_market_order(
            symbol=entry_decision.symbol,
            direction=entry_decision.direction,
            volume=entry_decision.position_size,
            # ... other params
        )
        event_bus.publish(OrderPlacedEvent(
            order_id=result['ticket'],
            symbol=entry_decision.symbol,
            direction=entry_decision.direction,
            volume=entry_decision.position_size
        ))
```

### Example Unit Test

```python
# tests/services/test_data_fetching_service.py
import pytest
from unittest.mock import Mock, MagicMock
from app.services.data_fetching import DataFetchingService
from app.events.data_events import NewCandleEvent
from tests.mocks.event_bus import MockEventBus
from tests.fixtures.market_data import create_mock_bars

def test_data_fetching_publishes_new_candle_event():
    # Arrange
    mock_event_bus = MockEventBus()
    mock_data_source = Mock()
    mock_data_source.get_stream_data.return_value = create_mock_bars(3)

    service = DataFetchingService(
        event_bus=mock_event_bus,
        data_source_manager=mock_data_source,
        date_helper=Mock(),
        logger=Mock(),
        config={"fetch_interval": 5}
    )

    # Act
    service.fetch_streaming_data("EURUSD", ["1"])

    # Assert
    published_events = mock_event_bus.get_published_events(NewCandleEvent)
    assert len(published_events) == 1
    assert published_events[0].symbol == "EURUSD"
    assert published_events[0].timeframe == "1"
```

### Example Integration Test

```python
# tests/integration/test_trading_cycle.py
import pytest
from app.infrastructure.orchestrator import TradingOrchestrator
from app.infrastructure.event_bus import EventBus
from tests.fixtures.market_data import create_mock_bars
from tests.mocks.data_source import MockDataSource
from tests.mocks.broker import MockBroker

def test_complete_trading_cycle_from_data_to_order():
    # Arrange: Setup orchestrator with mocked external dependencies
    event_bus = EventBus()
    mock_data_source = MockDataSource()
    mock_broker = MockBroker()

    orchestrator = TradingOrchestrator(
        config=test_config,
        event_bus=event_bus,
        data_source=mock_data_source,
        broker=mock_broker
    )
    orchestrator.initialize_services()
    orchestrator.start()

    # Act: Simulate new market data
    mock_data_source.emit_new_data("EURUSD", "1", create_mock_bars(1))

    # Wait for event propagation
    time.sleep(0.1)

    # Assert: Verify order was placed
    placed_orders = mock_broker.get_placed_orders()
    assert len(placed_orders) >= 1
    assert placed_orders[0].symbol == "EURUSD"

    # Cleanup
    orchestrator.stop()
```

---

## Acceptance Criteria

This refactoring will be considered complete when:

1. ✅ All 4 core services are implemented and tested (>90% coverage)
2. ✅ EventBus is fully functional with comprehensive tests
3. ✅ TradingOrchestrator manages service lifecycle correctly
4. ✅ Integration tests verify complete trading cycle works
5. ✅ New system produces identical trading decisions as old system
6. ✅ Performance metrics meet or exceed targets
7. ✅ All documentation is updated with examples
8. ✅ Code review approved by 2+ developers
9. ✅ 1 week of parallel testing shows zero regressions
10. ✅ Old main_live_regime.py is deprecated and marked for removal

---

## Timeline Estimate

- **Week 1**: Core infrastructure (Events, EventBus, base classes, test fixtures)
- **Week 2**: DataFetchingService + IndicatorCalculationService + tests
- **Week 3**: StrategyEvaluationService + TradeExecutionService + tests
- **Week 4**: TradingOrchestrator + integration tests + configuration
- **Week 5**: Migration, parallel testing, validation, documentation

**Total Estimated Time**: 5 weeks (1 sprint for infrastructure + 4 weeks implementation)

---

**End of PRD**
