# Architecture Explanation: Decoupled Services with Existing Packages

## Table of Contents
1. [Current Architecture (Before Refactoring)](#current-architecture-before-refactoring)
2. [New Architecture (After Refactoring)](#new-architecture-after-refactoring)
3. [How Existing Packages Are Preserved](#how-existing-packages-are-preserved)
4. [Decoupling Strategy](#decoupling-strategy)
5. [Event Flow Examples](#event-flow-examples)
6. [Migration Path](#migration-path)
7. [Benefits & Trade-offs](#benefits--trade-offs)

---

## Current Architecture (Before Refactoring)

### Current System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     main_live_regime.py                              │
│                    LiveTradingManager                                │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  _initialize_components()                                    │   │
│  │  - Creates MT5Client                                         │   │
│  │  - Loads strategies                                          │   │
│  │  - Creates EntryManager                                      │   │
│  │  - Loads indicator configs                                   │   │
│  │  - Creates DataSourceManager                                 │   │
│  │  - Creates IndicatorProcessor                                │   │
│  │  - Creates RegimeManager                                     │   │
│  │  - Creates TradeExecutor                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  _execute_trading_cycle()                                    │   │
│  │                                                               │   │
│  │  1. _fetch_market_data()                                     │   │
│  │     ├─> DataSourceManager.get_stream_data()                 │   │
│  │     ├─> RegimeManager.update()                              │   │
│  │     └─> IndicatorProcessor.process_new_row()                │   │
│  │                                                               │   │
│  │  2. _evaluate_strategies()                                   │   │
│  │     ├─> IndicatorProcessor.get_recent_rows()                │   │
│  │     ├─> StrategyEngine.evaluate()                           │   │
│  │     └─> EntryManager.manage_trades()                        │   │
│  │                                                               │   │
│  │  3. _execute_trades()                                        │   │
│  │     └─> TradeExecutor.execute_trading_cycle()               │   │
│  │                                                               │   │
│  │  4. _log_trading_status()                                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
           │              │              │              │
           ▼              ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  data/   │  │indicators│  │ regime/  │  │ trader/  │
    └──────────┘  └──────────┘  └──────────┘  └──────────┘
           │              │              │              │
           ▼              ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │strategy_ │  │  entry_  │  │ clients/ │  │  utils/  │
    │ builder/ │  │ manager/ │  │          │  │          │
    └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### Problems with Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ TIGHT COUPLING ISSUES                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  LiveTradingManager                                         │
│       │                                                     │
│       ├─────> DataSourceManager  (direct dependency)       │
│       ├─────> IndicatorProcessor (direct dependency)       │
│       ├─────> RegimeManager      (direct dependency)       │
│       ├─────> StrategyEngine     (direct dependency)       │
│       ├─────> EntryManager       (direct dependency)       │
│       └─────> TradeExecutor      (direct dependency)       │
│                                                             │
│  Problems:                                                  │
│  ✗ Hard to test (need all dependencies)                    │
│  ✗ Hard to modify (changes ripple everywhere)              │
│  ✗ Hard to reuse (monolithic)                              │
│  ✗ Hard to extend (modify main loop for new features)      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## New Architecture (After Refactoring)

### High-Level Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                      main_orchestrated.py                               │
│                     TradingOrchestrator                                 │
│                                                                         │
│  Responsibilities:                                                      │
│  • Initialize services                                                  │
│  • Inject dependencies                                                  │
│  • Start/Stop services                                                  │
│  • Monitor health                                                       │
│  • Handle graceful shutdown                                             │
│                                                                         │
└────────────┬────────────────────────────────────────────────────────────┘
             │
             │ Creates & Manages
             │
             ▼
┌───────────────────────────────────────────────────────────────────────┐
│                          EventBus                                       │
│                   (Pub/Sub Coordinator)                                 │
│                                                                         │
│  • Routes events between services                                       │
│  • Maintains event history                                              │
│  • Tracks metrics                                                       │
│  • Isolates services from each other                                    │
│                                                                         │
└──────┬──────────┬──────────┬──────────┬───────────────────────────────┘
       │          │          │          │
       │          │          │          │
       │          │          │          │
   ┌───▼───┐  ┌──▼───┐  ┌───▼───┐  ┌──▼───┐
   │ Data  │  │Indic.│  │Strat. │  │Trade │
   │Fetch  │  │Calc. │  │Eval.  │  │Exec. │
   │Service│  │Service│  │Service│  │Service│
   └───┬───┘  └──┬───┘  └───┬───┘  └──┬───┘
       │         │          │          │
       │         │          │          │
       │ Uses    │ Uses     │ Uses     │ Uses
       │ (DI)    │ (DI)     │ (DI)     │ (DI)
       │         │          │          │
       ▼         ▼          ▼          ▼
   ┌─────────────────────────────────────┐
   │    EXISTING PACKAGES (Unchanged)     │
   ├─────────────────────────────────────┤
   │                                      │
   │  data/          indicators/          │
   │  regime/        strategy_builder/    │
   │  entry_manager/ trader/              │
   │  clients/       utils/               │
   │                                      │
   └─────────────────────────────────────┘
```

### Service Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                                 │
│                    (New Abstraction)                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌───────────────────┐        ┌───────────────────┐                │
│  │ DataFetching      │ Events │ IndicatorCalc     │                │
│  │ Service           ├───────>│ Service           │                │
│  │                   │        │                   │                │
│  │ Wraps:            │        │ Wraps:            │                │
│  │ • DataSourceMgr   │        │ • IndicatorProc   │                │
│  │   (from data/)    │        │   (from indicators/)│              │
│  │ • Candle detection│        │ • RegimeManager   │                │
│  │                   │        │   (from regime/)  │                │
│  └───────────────────┘        └─────────┬─────────┘                │
│                                          │                           │
│                                          │ Events                    │
│                                          ▼                           │
│  ┌───────────────────┐        ┌───────────────────┐                │
│  │ TradeExecution    │<Events─│ StrategyEval      │                │
│  │ Service           │        │ Service           │                │
│  │                   │        │                   │                │
│  │ Wraps:            │        │ Wraps:            │                │
│  │ • EntryManager    │        │ • StrategyEngine  │                │
│  │   (from entry_mgr)│        │   (from strategy_ │                │
│  │ • TradeExecutor   │        │    builder/)      │                │
│  │   (from trader/)  │        │                   │                │
│  └───────────────────┘        └───────────────────┘                │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
           │                              │
           │                              │
           ▼                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EXISTING PACKAGES                                 │
│                    (Domain Logic - Unchanged)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  These packages remain EXACTLY as they are:                          │
│  • All classes unchanged                                             │
│  • All methods unchanged                                             │
│  • All logic unchanged                                               │
│  • Just used by services instead of main loop directly               │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## How Existing Packages Are Preserved

### Package Usage Matrix

```
┌──────────────────────────────────────────────────────────────────────┐
│ EXISTING PACKAGE → HOW IT'S USED IN NEW ARCHITECTURE                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  1. data/ package                                                     │
│     ┌─────────────────────────────────────────────┐                  │
│     │ DataSourceManager                            │                  │
│     │ • LiveDataSource                            │                  │
│     │ • BacktestDataSource                        │                  │
│     └─────────────────────────────────────────────┘                  │
│                    ▲                                                  │
│                    │ Used by (Dependency Injection)                   │
│                    │                                                  │
│     ┌─────────────────────────────────────────────┐                  │
│     │ DataFetchingService (NEW)                   │                  │
│     │                                              │                  │
│     │ def __init__(self, data_source: DataSourceManager):             │
│     │     self.data_source = data_source          │                  │
│     │                                              │                  │
│     │ def fetch_streaming_data(self, ...):        │                  │
│     │     # Same logic as current _fetch_market_data()               │
│     │     df = self.data_source.get_stream_data(...)                 │
│     │     event_bus.publish(NewCandleEvent(...))  │                  │
│     └─────────────────────────────────────────────┘                  │
│                                                                        │
│     ✓ DataSourceManager unchanged                                    │
│     ✓ Just injected into service                                     │
│     ✓ Service adds event publishing on top                           │
│                                                                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  2. indicators/ package                                               │
│     ┌─────────────────────────────────────────────┐                  │
│     │ IndicatorProcessor                           │                  │
│     │ • process_new_row()                         │                  │
│     │ • get_recent_rows()                         │                  │
│     └─────────────────────────────────────────────┘                  │
│                    ▲                                                  │
│                    │ Used by (Dependency Injection)                   │
│                    │                                                  │
│     ┌─────────────────────────────────────────────┐                  │
│     │ IndicatorCalculationService (NEW)           │                  │
│     │                                              │                  │
│     │ def __init__(self, indicator_processor: IndicatorProcessor):    │
│     │     self.indicators = indicator_processor   │                  │
│     │                                              │                  │
│     │ def on_new_candle(self, event: NewCandleEvent):                │
│     │     # Same logic as current processing      │                  │
│     │     regime_data = self.regime_mgr.update(...)                  │
│     │     enriched = self.indicators.process_new_row(...)            │
│     │     recent_rows = self.indicators.get_recent_rows()            │
│     │     event_bus.publish(IndicatorsCalculatedEvent(...))          │
│     └─────────────────────────────────────────────┘                  │
│                                                                        │
│     ✓ IndicatorProcessor unchanged                                   │
│     ✓ Just injected into service                                     │
│     ✓ Service subscribes to events and publishes results             │
│                                                                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  3. regime/ package                                                   │
│     ┌─────────────────────────────────────────────┐                  │
│     │ RegimeManager                                │                  │
│     │ • setup()                                   │                  │
│     │ • update()                                  │                  │
│     └─────────────────────────────────────────────┘                  │
│                    ▲                                                  │
│                    │ Used by                                          │
│                    │                                                  │
│     ┌─────────────────────────────────────────────┐                  │
│     │ IndicatorCalculationService (NEW)           │                  │
│     │                                              │                  │
│     │ def __init__(self, regime_manager: RegimeManager):              │
│     │     self.regime_mgr = regime_manager        │                  │
│     │                                              │                  │
│     │ def on_new_candle(self, event: NewCandleEvent):                │
│     │     regime_data = self.regime_mgr.update(...)│                 │
│     │     # ... rest of processing                 │                 │
│     └─────────────────────────────────────────────┘                  │
│                                                                        │
│     ✓ RegimeManager unchanged                                        │
│     ✓ Used exactly as before                                         │
│     ✓ Just accessed through service instead of main loop             │
│                                                                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  4. strategy_builder/ package                                         │
│     ┌─────────────────────────────────────────────┐                  │
│     │ StrategyEngine                               │                  │
│     │ • evaluate()                                │                  │
│     │ • get_strategy_info()                       │                  │
│     └─────────────────────────────────────────────┘                  │
│                    ▲                                                  │
│                    │ Used by                                          │
│                    │                                                  │
│     ┌─────────────────────────────────────────────┐                  │
│     │ StrategyEvaluationService (NEW)             │                  │
│     │                                              │                  │
│     │ def __init__(self, strategy_engine: StrategyEngine):            │
│     │     self.strategy_engine = strategy_engine  │                  │
│     │                                              │                  │
│     │ def on_indicators_calculated(self, event):  │                  │
│     │     result = self.strategy_engine.evaluate(event.recent_rows)  │
│     │     # Generate entry/exit signals           │                  │
│     │     event_bus.publish(EntrySignalEvent(...))│                  │
│     └─────────────────────────────────────────────┘                  │
│                                                                        │
│     ✓ StrategyEngine unchanged                                       │
│     ✓ Strategies remain YAML-configured                              │
│     ✓ Service translates evaluation results to events                │
│                                                                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  5. entry_manager/ package                                            │
│     ┌─────────────────────────────────────────────┐                  │
│     │ EntryManager                                 │                  │
│     │ • calculate_entry_decision()                │                  │
│     │ • calculate_exit_decision()                 │                  │
│     │ • manage_trades()                           │                  │
│     └─────────────────────────────────────────────┘                  │
│                    ▲                                                  │
│                    │ Used by                                          │
│                    │                                                  │
│     ┌─────────────────────────────────────────────┐                  │
│     │ TradeExecutionService (NEW)                  │                  │
│     │                                              │                  │
│     │ def __init__(self, entry_manager: EntryManager):                │
│     │     self.entry_manager = entry_manager      │                  │
│     │                                              │                  │
│     │ def on_entry_signal(self, event: EntrySignalEvent):            │
│     │     decision = self.entry_manager.calculate_entry_decision(...)│
│     │     # Execute trade                          │                  │
│     │     event_bus.publish(OrderPlacedEvent(...))│                  │
│     └─────────────────────────────────────────────┘                  │
│                                                                        │
│     ✓ EntryManager unchanged                                         │
│     ✓ All risk management logic preserved                            │
│     ✓ Service orchestrates calls based on events                     │
│                                                                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  6. trader/ package                                                   │
│     ┌─────────────────────────────────────────────┐                  │
│     │ TradeExecutor                                │                  │
│     │ • execute_trading_cycle()                   │                  │
│     │ • Components (ExitManager, RiskMonitor,     │                  │
│     │   DuplicateFilter, OrderExecutor)           │                  │
│     └─────────────────────────────────────────────┘                  │
│                    ▲                                                  │
│                    │ Used by                                          │
│                    │                                                  │
│     ┌─────────────────────────────────────────────┐                  │
│     │ TradeExecutionService (NEW)                  │                  │
│     │                                              │                  │
│     │ def __init__(self, trade_executor: TradeExecutor):              │
│     │     self.trade_executor = trade_executor    │                  │
│     │                                              │                  │
│     │ # Breaks down execute_trading_cycle() into  │                  │
│     │ # separate event handlers                    │                  │
│     │ def on_entry_signal(self, ...): ...         │                  │
│     │ def on_exit_signal(self, ...): ...          │                  │
│     └─────────────────────────────────────────────┘                  │
│                                                                        │
│     ✓ TradeExecutor and components unchanged                         │
│     ✓ Same risk management, duplicate filtering, etc.                │
│     ✓ Service provides event-driven interface                        │
│                                                                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  7. clients/ package (MT5 Client)                                     │
│     ┌─────────────────────────────────────────────┐                  │
│     │ MT5Client                                    │                  │
│     │ • data, positions, orders, account          │                  │
│     └─────────────────────────────────────────────┘                  │
│                    ▲                                                  │
│                    │ Used by multiple services                        │
│                    │                                                  │
│     ┌──────────────┴──────────────┐                                  │
│     │                               │                                 │
│  DataFetchingService        TradeExecutionService                    │
│  (for fetching data)        (for placing orders)                     │
│                                                                        │
│     ✓ MT5Client unchanged                                            │
│     ✓ Shared across services via DI                                  │
│                                                                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  8. utils/ package                                                    │
│     ┌─────────────────────────────────────────────┐                  │
│     │ DateHelper, Config, Logger, Functions       │                  │
│     └─────────────────────────────────────────────┘                  │
│                    ▲                                                  │
│                    │ Used by all services                             │
│                                                                        │
│     ✓ Utils unchanged                                                │
│     ✓ Injected into services as needed                               │
│                                                                        │
└──────────────────────────────────────────────────────────────────────┘
```

### Key Insight: Services Are WRAPPERS

```
┌────────────────────────────────────────────────────────────┐
│ CRITICAL UNDERSTANDING                                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Services DO NOT replace existing packages.               │
│  Services WRAP existing packages to add:                  │
│                                                            │
│  1. Event-driven communication                            │
│  2. Lifecycle management                                  │
│  3. Better error handling                                 │
│  4. Health monitoring                                     │
│  5. Metrics collection                                    │
│                                                            │
│  The CORE LOGIC remains in existing packages:             │
│  • Indicator calculations → indicators/                   │
│  • Regime detection → regime/                             │
│  • Strategy evaluation → strategy_builder/                │
│  • Risk management → entry_manager/                       │
│  • Trade execution → trader/                              │
│                                                            │
│  Services just orchestrate these packages through events. │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## Decoupling Strategy

### Before: Tight Coupling

```
┌──────────────────────────────────────────────────┐
│ main_live_regime.py (LiveTradingManager)         │
│                                                  │
│  def _execute_trading_cycle(self):               │
│                                                  │
│    # Step 1: Direct call to data source         │
│    df = self.data_source.get_stream_data(...)   │
│                                                  │
│    # Step 2: Direct call to regime manager      │
│    regime = self.regime_manager.update(...)     │
│                                                  │
│    # Step 3: Direct call to indicators          │
│    self.indicators.process_new_row(...)         │
│                                                  │
│    # Step 4: Direct call to strategies          │
│    recent_rows = self.indicators.get_recent_rows()│
│    result = self.strategy_engine.evaluate(...)  │
│                                                  │
│    # Step 5: Direct call to entry manager       │
│    trades = self.entry_manager.manage_trades(...)│
│                                                  │
│    # Step 6: Direct call to trade executor      │
│    self.trade_executor.execute_trading_cycle(...)│
│                                                  │
└──────────────────────────────────────────────────┘
              │
              │ Problems:
              │
              ├─> 6 direct dependencies
              ├─> Hard to test (need all components)
              ├─> Hard to mock (deep integration)
              └─> Hard to change (ripple effects)
```

### After: Loose Coupling via Events

```
┌──────────────────────────────────────────────────────────────┐
│ TradingOrchestrator                                           │
│                                                              │
│  • Initializes services                                      │
│  • Starts services (services subscribe to events)           │
│  • Doesn't know about trading logic                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                          │
                          │ Manages
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                       EventBus                                │
│                                                              │
│  subscribe(NewCandleEvent, handler)                          │
│  publish(NewCandleEvent(...))                                │
│                                                              │
└────┬──────────────┬──────────────┬──────────────┬───────────┘
     │              │              │              │
     │ Decoupled    │ Decoupled    │ Decoupled    │ Decoupled
     │ via Events   │ via Events   │ via Events   │ via Events
     │              │              │              │
     ▼              ▼              ▼              ▼
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ Data    │   │Indicator│   │Strategy │   │Trade    │
│Fetching │   │Calc     │   │Eval     │   │Execution│
│Service  │   │Service  │   │Service  │   │Service  │
└─────────┘   └─────────┘   └─────────┘   └─────────┘
     │              │              │              │
     │              │              │              │
     │ Publishes    │ Subscribes   │ Subscribes   │ Subscribes
     │ NewCandle    │ NewCandle    │ Indicators   │ EntrySignal
     │ Event        │ Event        │ Calculated   │ Event
     │              │              │ Event        │
     │              │ Publishes    │              │
     │              │ Indicators   │ Publishes    │ Publishes
     │              │ Calculated   │ EntrySignal  │ OrderPlaced
     │              │ Event        │ Event        │ Event
     │              │              │              │
     └──────────────┴──────────────┴──────────────┘
                          │
                          │ Benefits:
                          │
                          ├─> Services don't know each other
                          ├─> Easy to test (mock EventBus)
                          ├─> Easy to add services
                          └─> Easy to change (no ripple effects)
```

### Event-Driven Communication Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│ HOW SERVICES COMMUNICATE                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Service A                  EventBus              Service B      │
│  ─────────                  ────────              ─────────      │
│                                                                   │
│  1. Initialization Phase:                                        │
│     ┌─────────┐                                  ┌─────────┐    │
│     │Service B│──────register handler───────────>│EventBus │    │
│     └─────────┘   "I want NewCandleEvent"        └─────────┘    │
│                                                                   │
│  2. Runtime Phase:                                               │
│     ┌─────────┐            ┌─────────┐           ┌─────────┐   │
│     │Service A│───publish──>│EventBus │──notify──>│Service B│   │
│     └─────────┘  NewCandle  └─────────┘   calls   └─────────┘   │
│                   Event                   handler                │
│                                                                   │
│  3. Key Points:                                                  │
│     • Service A doesn't know about Service B                     │
│     • Service B doesn't know about Service A                     │
│     • EventBus routes events to registered handlers              │
│     • Services can be added/removed without affecting others     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Event Flow Examples

### Example 1: Complete Trading Cycle

```
TIME: T0 (5-second interval triggers)
─────────────────────────────────────────────────────────────────

1. DataFetchingService.fetch_streaming_data()
   │
   ├─> Calls: data_source.get_stream_data("EURUSD", "1", 3)
   │           (Uses existing DataSourceManager - UNCHANGED)
   │
   ├─> Detects new candle using has_new_candle()
   │           (Uses existing utils function - UNCHANGED)
   │
   └─> Publishes: NewCandleEvent(symbol="EURUSD", timeframe="1", bar=...)

        │
        │ EventBus routes event to subscribers
        │
        ▼

2. IndicatorCalculationService.on_new_candle(event)
   │
   ├─> Calls: regime_manager.update(timeframe, bar)
   │           (Uses existing RegimeManager - UNCHANGED)
   │
   ├─> Calls: indicators.process_new_row(timeframe, bar, regime_data)
   │           (Uses existing IndicatorProcessor - UNCHANGED)
   │
   ├─> Calls: indicators.get_recent_rows()
   │           (Gets recent rows as before - UNCHANGED)
   │
   └─> Publishes: IndicatorsCalculatedEvent(
                     symbol="EURUSD",
                     timeframe="1",
                     enriched_data={...},
                     recent_rows={...}
                  )

        │
        │ EventBus routes event to subscribers
        │
        ▼

3. StrategyEvaluationService.on_indicators_calculated(event)
   │
   ├─> Calls: strategy_engine.evaluate(event.recent_rows)
   │           (Uses existing StrategyEngine - UNCHANGED)
   │
   ├─> Iterates through strategy results
   │
   └─> For each entry signal:
       Publishes: EntrySignalEvent(
                     strategy_name="trend_follower",
                     symbol="EURUSD",
                     direction="long"
                  )

        │
        │ EventBus routes event to subscribers
        │
        ▼

4. TradeExecutionService.on_entry_signal(event)
   │
   ├─> Calls: entry_manager.calculate_entry_decision(...)
   │           (Uses existing EntryManager - UNCHANGED)
   │
   ├─> Checks: Can we trade? (restrictions, risk limits)
   │           (Uses existing TradeExecutor components - UNCHANGED)
   │
   ├─> Calls: trade_executor.execute_entry(...)
   │           (Uses existing TradeExecutor - UNCHANGED)
   │
   └─> Publishes: OrderPlacedEvent(
                     order_id=12345,
                     symbol="EURUSD",
                     direction="long",
                     volume=0.1,
                     ...
                  )

─────────────────────────────────────────────────────────────────
RESULT: Trade executed with exact same logic as before,
        but through event-driven services instead of monolithic loop
```

### Example 2: Error Handling Flow

```
SCENARIO: Indicator calculation fails
─────────────────────────────────────────────────────────────────

1. IndicatorCalculationService.on_new_candle(event)
   │
   ├─> Try: indicators.process_new_row(...)
   │
   ├─> Catch Exception: Indicator calculation error
   │
   ├─> Logs error with full context
   │
   └─> Publishes: IndicatorCalculationErrorEvent(
                     symbol="EURUSD",
                     timeframe="1",
                     error="Division by zero in RSI calculation"
                  )

        │
        │ System continues running
        │ Other services unaffected
        │
        ▼

   StrategyEvaluationService doesn't receive IndicatorsCalculatedEvent
   → Doesn't evaluate strategies this cycle
   → No trades executed

   Next cycle (5 seconds later):
   → System tries again
   → May succeed or fail independently

─────────────────────────────────────────────────────────────────
BENEFIT: Isolated error doesn't crash entire system
         vs. Current: Exception in main loop crashes everything
```

### Example 3: Adding New Feature (Notification Service)

```
SCENARIO: Add email notifications for trades
─────────────────────────────────────────────────────────────────

OLD ARCHITECTURE:
  ✗ Modify main_live_regime.py
  ✗ Add notification logic to _execute_trades()
  ✗ Import notification module
  ✗ Test entire main loop again

NEW ARCHITECTURE:
  ✓ Create NotificationService
  ✓ Subscribe to OrderPlacedEvent
  ✓ Send email in event handler
  ✓ Register service in orchestrator
  ✓ ZERO changes to existing services

Code:
───────────────────────────────────────────────────────────────

class NotificationService(EventDrivenService):
    def start(self):
        # Subscribe to trade events
        self.event_bus.subscribe(
            OrderPlacedEvent,
            self.on_order_placed
        )

    def on_order_placed(self, event: OrderPlacedEvent):
        # Send email notification
        send_email(
            subject=f"Order Placed: {event.symbol}",
            body=f"Placed {event.direction} order..."
        )

# In orchestrator:
orchestrator.register_service(NotificationService(...))

─────────────────────────────────────────────────────────────────
BENEFIT: Add features without touching existing code
```

---

## Migration Path

### Phase-by-Phase Migration

```
┌────────────────────────────────────────────────────────────────┐
│ PHASE 1: Infrastructure (Week 1)                               │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Create:                                                        │
│  ├─ app/events/                                                │
│  │  ├─ base.py            (Event, EventHandler)               │
│  │  ├─ data_events.py     (NewCandleEvent, etc.)              │
│  │  ├─ indicator_events.py                                     │
│  │  ├─ strategy_events.py                                      │
│  │  └─ trade_events.py                                         │
│  │                                                              │
│  ├─ app/infrastructure/                                         │
│  │  └─ event_bus.py       (EventBus implementation)           │
│  │                                                              │
│  ├─ app/services/                                               │
│  │  └─ base.py            (EventDrivenService base class)     │
│  │                                                              │
│  └─ tests/                                                      │
│     ├─ test_event_bus.py                                       │
│     └─ mocks/mock_event_bus.py                                 │
│                                                                 │
│  Status: Existing packages UNTOUCHED                           │
│          main_live_regime.py still running                     │
│                                                                 │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ PHASE 2: Service Implementation (Week 2-3)                     │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Create Services (one at a time):                              │
│  ├─ app/services/data_fetching.py                             │
│  │  └─ Tests: tests/services/test_data_fetching_service.py   │
│  │                                                              │
│  ├─ app/services/indicator_calculation.py                      │
│  │  └─ Tests: tests/services/test_indicator_calculation.py   │
│  │                                                              │
│  ├─ app/services/strategy_evaluation.py                        │
│  │  └─ Tests: tests/services/test_strategy_evaluation.py     │
│  │                                                              │
│  └─ app/services/trade_execution.py                            │
│     └─ Tests: tests/services/test_trade_execution.py          │
│                                                                 │
│  Each service:                                                  │
│  • Wraps existing package functionality                        │
│  • Adds event publishing/subscribing                           │
│  • Has >90% test coverage                                      │
│  • Uses dependency injection                                    │
│                                                                 │
│  Status: Existing packages UNTOUCHED                           │
│          main_live_regime.py still running                     │
│          Services ready but not yet integrated                 │
│                                                                 │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ PHASE 3: Orchestration (Week 4)                                │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Create:                                                        │
│  ├─ app/infrastructure/orchestrator.py                         │
│  │  (TradingOrchestrator)                                     │
│  │                                                              │
│  ├─ app/main_orchestrated.py                                   │
│  │  (New main entry point using services)                     │
│  │                                                              │
│  ├─ config/services.yaml                                       │
│  │  (Service configuration)                                    │
│  │                                                              │
│  └─ tests/integration/                                          │
│     ├─ test_trading_cycle.py                                   │
│     └─ test_event_flow.py                                      │
│                                                                 │
│  Status: Existing packages UNTOUCHED                           │
│          main_live_regime.py still running                     │
│          main_orchestrated.py ready for testing                │
│                                                                 │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ PHASE 4: Parallel Testing (Week 5)                             │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Run Both Systems Side-by-Side:                                │
│  ┌─────────────────────────┐  ┌─────────────────────────┐    │
│  │ main_live_regime.py     │  │ main_orchestrated.py    │    │
│  │ (Old System)            │  │ (New System)            │    │
│  │                         │  │                         │    │
│  │ • Runs on paper account │  │ • Runs on paper account │    │
│  │ • Logs all decisions    │  │ • Logs all decisions    │    │
│  │                         │  │                         │    │
│  └─────────────────────────┘  └─────────────────────────┘    │
│               │                          │                     │
│               └──────────┬───────────────┘                     │
│                          │                                     │
│                          ▼                                     │
│                  ┌───────────────┐                            │
│                  │ Compare Logs  │                            │
│                  │               │                            │
│                  │ Verify:       │                            │
│                  │ • Same signals│                            │
│                  │ • Same orders │                            │
│                  │ • Same timing │                            │
│                  └───────────────┘                            │
│                                                                 │
│  If identical behavior for 1 week:                             │
│  → Switch to main_orchestrated.py                              │
│  → Deprecate main_live_regime.py                               │
│                                                                 │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ PHASE 5: Cleanup (Week 6)                                      │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  • Move main_live_regime.py to deprecated/ folder              │
│  • Update documentation                                         │
│  • Update deployment scripts                                    │
│  • Celebrate! 🎉                                               │
│                                                                 │
│  Status: Existing packages STILL UNTOUCHED                     │
│          Just accessed through services instead of main loop   │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### What Changes vs What Stays

```
┌────────────────────────────────────────────────────────────────┐
│ WHAT CHANGES                                                    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ✓ New: app/events/ (event models)                            │
│  ✓ New: app/services/ (service layer)                         │
│  ✓ New: app/infrastructure/ (EventBus, Orchestrator)          │
│  ✓ New: app/main_orchestrated.py (new entry point)            │
│  ✓ New: config/services.yaml (service configuration)          │
│  ✓ New: tests/services/ (service tests)                       │
│  ✓ New: tests/mocks/ (mock implementations)                   │
│  ✓ Deprecated: app/main_live_regime.py (old entry point)      │
│                                                                 │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ WHAT STAYS THE SAME (UNCHANGED)                                │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ✓ app/clients/ - MT5 client (no changes)                     │
│  ✓ app/data/ - Data sources (no changes)                      │
│  ✓ app/indicators/ - Indicator calculation (no changes)       │
│  ✓ app/regime/ - Regime detection (no changes)                │
│  ✓ app/strategy_builder/ - Strategy evaluation (no changes)   │
│  ✓ app/entry_manager/ - Risk management (no changes)          │
│  ✓ app/trader/ - Trade execution (no changes)                 │
│  ✓ app/utils/ - Utilities (no changes)                        │
│  ✓ config/strategies/ - Strategy YAML files (no changes)      │
│  ✓ config/indicators/ - Indicator configs (no changes)        │
│  ✓ .env - Environment variables (no changes)                  │
│                                                                 │
│  ALL YOUR EXISTING LOGIC, STRATEGIES, CONFIGS WORK AS-IS!      │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Benefits & Trade-offs

### Benefits

```
┌────────────────────────────────────────────────────────────────┐
│ BENEFITS OF EVENT-DRIVEN ARCHITECTURE                          │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. TESTABILITY ⭐⭐⭐⭐⭐                                       │
│     ┌──────────────────────────────────────────────────────┐  │
│     │ Before: Test entire main loop (300+ lines)          │  │
│     │ After:  Test each service independently (<100 lines)│  │
│     │                                                      │  │
│     │ def test_data_fetching_service():                   │  │
│     │     mock_event_bus = MockEventBus()                 │  │
│     │     mock_data_source = Mock()                       │  │
│     │     service = DataFetchingService(...)              │  │
│     │     service.fetch_streaming_data(...)               │  │
│     │     assert mock_event_bus.events_published == 1     │  │
│     └──────────────────────────────────────────────────────┘  │
│                                                                 │
│  2. EXTENSIBILITY ⭐⭐⭐⭐⭐                                     │
│     ┌──────────────────────────────────────────────────────┐  │
│     │ Want to add notifications?                          │  │
│     │ • Create NotificationService                        │  │
│     │ • Subscribe to OrderPlacedEvent                     │  │
│     │ • Done! No other changes needed                     │  │
│     │                                                      │  │
│     │ Want to add logging service?                        │  │
│     │ • Create LoggingService                             │  │
│     │ • Subscribe to ALL events                           │  │
│     │ • Done! No other changes needed                     │  │
│     └──────────────────────────────────────────────────────┘  │
│                                                                 │
│  3. MAINTAINABILITY ⭐⭐⭐⭐⭐                                   │
│     ┌──────────────────────────────────────────────────────┐  │
│     │ Before: Change indicator processing                 │  │
│     │         → Must understand entire main loop          │  │
│     │         → Risk breaking other parts                 │  │
│     │                                                      │  │
│     │ After:  Change indicator processing                 │  │
│     │         → Only modify IndicatorCalculationService   │  │
│     │         → Other services unaffected                 │  │
│     │         → Events remain the same                    │  │
│     └──────────────────────────────────────────────────────┘  │
│                                                                 │
│  4. REUSABILITY ⭐⭐⭐⭐                                         │
│     ┌──────────────────────────────────────────────────────┐  │
│     │ Services can be reused in different contexts:      │  │
│     │ • Live trading                                      │  │
│     │ • Paper trading                                     │  │
│     │ • Backtesting (with different orchestration)       │  │
│     │ • Research/Analysis mode                            │  │
│     └──────────────────────────────────────────────────────┘  │
│                                                                 │
│  5. ISOLATION ⭐⭐⭐⭐⭐                                         │
│     ┌──────────────────────────────────────────────────────┐  │
│     │ Error in one service doesn't crash others:         │  │
│     │ • Indicator calculation fails                       │  │
│     │   → IndicatorCalculationService publishes error    │  │
│     │   → Other services continue running                │  │
│     │   → System tries again next cycle                  │  │
│     │                                                      │  │
│     │ Before: Any error crashes entire main loop          │  │
│     └──────────────────────────────────────────────────────┘  │
│                                                                 │
│  6. MONITORING ⭐⭐⭐⭐                                          │
│     ┌──────────────────────────────────────────────────────┐  │
│     │ Each service reports health independently:         │  │
│     │ • Service uptime                                    │  │
│     │ • Events processed                                  │  │
��     │ • Errors encountered                                │  │
│     │ • Processing time                                   │  │
│     │                                                      │  │
│     │ Easy to identify which component has issues         │  │
│     └──────────────────────────────────────────────────────┘  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Trade-offs

```
┌────────────────────────────────────────────────────────────────┐
│ TRADE-OFFS TO CONSIDER                                         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. COMPLEXITY ⚠️                                              │
│     ┌──────────────────────────────────────────────────────┐  │
│     │ More moving parts:                                  │  │
│     │ • EventBus to understand                            │  │
│     │ • Services to navigate                              │  │
│     │ • Event flow to trace                               │  │
│     │                                                      │  │
│     │ Mitigation:                                         │  │
│     │ • Clear documentation                               │  │
│     │ • Architecture diagrams                             │  │
│     │ • Logging with correlation IDs                     │  │
│     └──────────────────────────────────────────────────────┘  │
│                                                                 │
│  2. INDIRECTION ⚠️                                             │
│     ┌──────────────────────────────────────────────────────┐  │
│     │ Before: Direct call chain (easy to trace)          │  │
│     │ After:  Event-based (need to follow events)        │  │
│     │                                                      │  │
│     │ Mitigation:                                         │  │
│     │ • Event history for debugging                       │  │
│     │ • Clear event naming                               │  │
│     │ • Sequence diagrams in docs                        │  │
│     └──────────────────────────────────────────────────────┘  │
│                                                                 │
│  3. OVERHEAD ⚠️                                                │
│     ┌──────────────────────────────────────────────────────┐  │
│     │ Small performance overhead:                         │  │
│     │ • Event creation/publishing: ~1ms                   │  │
│     │ • Service dispatch: ~1-2ms per service             │  │
│     │ • Total: ~5-10ms per cycle                         │  │
│     │                                                      │  │
│     │ Acceptable for 5-second trading loop                │  │
│     │ Not suitable for microsecond trading                │  │
│     └──────────────────────────────────────────────────────┘  │
│                                                                 │
│  4. MORE CODE ⚠️                                               │
│     ┌──────────────────────────────────────────────────────┐  │
│     │ More files to maintain:                             │  │
│     │ • Event models                                      │  │
│     │ • Service classes                                   │  │
│     │ • Orchestrator                                      │  │
│     │                                                      │  │
│     │ But: Each piece is simpler and focused             │  │
│     │ Net benefit: Easier to maintain overall            │  │
│     └──────────────────────────────────────────────────────┘  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Cost-Benefit Analysis

```
┌────────────────────────────────────────────────────────────────┐
│ IS IT WORTH IT?                                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Investment:                                                    │
│  • 5 weeks development time                                    │
│  • Learning curve for event-driven architecture                │
│  • More code to maintain                                       │
│                                                                 │
│  Return:                                                        │
│  ✓ 10x easier to test                                         │
│  ✓ 5x easier to add features                                  │
│  ✓ 3x easier to debug issues                                  │
│  ✓ Future-proof architecture                                  │
│  ✓ Production-ready error handling                            │
│  ✓ Monitoring and metrics built-in                            │
│                                                                 │
│  Verdict: ✅ YES, WORTH IT                                     │
│                                                                 │
│  Especially for:                                               │
│  • Long-term projects                                          │
│  • Projects that will evolve                                   │
│  • Projects requiring high reliability                         │
│  • Projects with multiple developers                           │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Summary

### Key Takeaways

1. **Existing packages are preserved** - No changes to your battle-tested logic
2. **Services are wrappers** - They add event-driven capabilities on top
3. **EventBus decouples** - Services don't know about each other
4. **Migration is gradual** - Build services alongside existing system
5. **Testing is prioritized** - Each service independently testable
6. **Benefits outweigh costs** - Better architecture pays dividends long-term

### Next Steps

If you're ready to proceed:
1. Review this architecture explanation
2. Ask any clarifying questions
3. Approve the PRD
4. Start Phase 1 (Core Infrastructure)

---

**Questions or concerns? Let's discuss!** 🚀
