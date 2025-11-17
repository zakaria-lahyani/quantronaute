# PRD: Automated Trading Toggle & Manual Trading API

## Document Information
- **Feature Name**: Automated Trading Toggle & Manual Trading API
- **Version**: 1.0
- **Created**: 2025-11-17
- **Author**: Product Requirements Document
- **Target Audience**: Junior Developers

---

## 1. Introduction / Overview

### What We're Building
This PRD defines two related features that will give traders greater control over the Quantronaute trading system:

1. **Phase 1 (This PRD)**: Automated Trading Toggle - A mechanism to enable/disable automated trading at runtime
2. **Phase 2 (Future PRD)**: Manual Trading API - RESTful API for manual trade execution and system monitoring

This document covers **Phase 1 only**: the automated trading toggle feature.

### Problem Statement
Currently, the Quantronaute system operates in a fully automated mode with no runtime control to pause/resume trading. Once the application starts, it continuously evaluates strategies and executes trades. Traders need the ability to:

- Temporarily pause automated trading during high-impact news events
- Stop automated decisions while manually managing existing positions
- Resume automated trading without restarting the entire application
- Maintain safety controls (stop-loss/take-profit) even when automation is disabled

### Context
The Quantronaute system is an event-driven, multi-symbol automated trading platform that:
- Runs 4 main services: DataFetching, IndicatorCalculation, StrategyEvaluation, TradeExecution
- Uses an EventBus for service communication (publish/subscribe pattern)
- Manages risk through EntryManager (position sizing, SL, TP) and account-level limits
- Supports multiple brokers, symbols, and strategies via YAML configuration
- Operates on a 30-second main loop controlled by TradingOrchestrator

---

## 2. Goals

### Primary Goals
1. **Enable runtime control** of automated trading without application restart
2. **Prevent new positions** from being opened when automated trading is disabled
3. **Prevent automated position management** (partial exits, trailing stops, automated exits) when disabled
4. **Maintain critical safety controls** (stop-loss, take-profit) even when automated trading is disabled
5. **Provide clear visibility** into the current automation state (enabled/disabled)
6. **Ensure state persistence** so the automation state survives application restarts

### Success Criteria
- Traders can toggle automated trading on/off while the application is running
- When disabled, no new positions are opened by the system
- When disabled, existing positions retain their SL/TP protection but are not automatically managed
- The automation state is visible in application logs and metrics
- The automation state persists across application restarts
- The toggle mechanism integrates seamlessly with the existing event-driven architecture

---

## 3. User Stories

### As a Trader
1. **US-1**: As a trader, I want to disable automated trading before a major news event so that the system doesn't open new positions during volatile conditions, while my existing positions remain protected by their stop-loss and take-profit levels.

2. **US-2**: As a trader, I want to re-enable automated trading after the news event passes so that the system resumes normal strategy evaluation and trade execution without requiring an application restart.

3. **US-3**: As a trader, I want the system to remember the automation state (enabled/disabled) when I restart the application so that I don't accidentally re-enable automation after a manual shutdown.

4. **US-4**: As a trader, I want to see clear log messages when automation is toggled so that I can verify the system responded to my command.

5. **US-5**: As a trader, I want existing positions to keep their stop-loss and take-profit orders active even when automated trading is disabled so that I'm protected from catastrophic losses.

### As a System Administrator
6. **US-6**: As an admin, I want to configure the default automation state (enabled/disabled) in the environment variables so that I can control the startup behavior per broker/account.

7. **US-7**: As an admin, I want to monitor the automation state through system metrics so that I can track when and why automation was toggled in production environments.

---

## 4. Functional Requirements

### FR-1: Automation State Management
**Description**: The system must maintain a persistent automation state (enabled/disabled).

**Requirements**:
- FR-1.1: Create a new `AutomationStateManager` component responsible for managing the automation state
- FR-1.2: Support two states: `ENABLED` (automated trading active) and `DISABLED` (automated trading paused)
- FR-1.3: Store the state in a persistent file (`automation_state.json`) in the configuration directory
- FR-1.4: Load the state from the persistent file on application startup
- FR-1.5: Default to `ENABLED` if no persistent state file exists and no environment variable is set
- FR-1.6: Support environment variable `AUTOMATION_ENABLED` (true/false) to override the default state on first startup
- FR-1.7: The persistent file state always takes precedence over the environment variable after first startup

**File Format** (`automation_state.json`):
```json
{
  "enabled": true,
  "last_updated": "2025-11-17T10:30:00Z",
  "updated_by": "system|user|api"
}
```

---

### FR-2: Event-Driven Toggle Mechanism
**Description**: The automation state must be controllable through the EventBus to maintain architectural consistency.

**Requirements**:
- FR-2.1: Create a new event type `ToggleAutomationEvent` with fields:
  - `action`: Enum of `ENABLE`, `DISABLE`, or `QUERY`
  - `reason`: Optional string describing why the toggle occurred
  - `requested_by`: String identifying the source (e.g., "user", "schedule", "risk_limit")

- FR-2.2: Create a new event type `AutomationStateChangedEvent` published when state changes, with fields:
  - `enabled`: Boolean indicating new state
  - `previous_state`: Boolean indicating old state
  - `reason`: String explaining the change
  - `timestamp`: DateTime of the change

- FR-2.3: `AutomationStateManager` must subscribe to `ToggleAutomationEvent`
- FR-2.4: When receiving `ENABLE` or `DISABLE` action, update state and publish `AutomationStateChangedEvent`
- FR-2.5: When receiving `QUERY` action, publish current state without modification
- FR-2.6: All state changes must be logged at INFO level with timestamps

**Event Schema**:
```python
@dataclass(frozen=True, kw_only=True)
class ToggleAutomationEvent(Event):
    action: AutomationAction  # Enum: ENABLE, DISABLE, QUERY
    reason: Optional[str] = None
    requested_by: str = "system"

@dataclass(frozen=True, kw_only=True)
class AutomationStateChangedEvent(Event):
    enabled: bool
    previous_state: bool
    reason: str
    changed_at: datetime
```

---

### FR-3: Strategy Evaluation Service Integration
**Description**: The StrategyEvaluationService must respect the automation state when generating entry signals.

**Requirements**:
- FR-3.1: StrategyEvaluationService must subscribe to `AutomationStateChangedEvent`
- FR-3.2: Maintain an internal `_automation_enabled` flag initialized from `AutomationStateManager` on startup
- FR-3.3: When `_automation_enabled = False`, do NOT publish `EntrySignalEvent` (skip entry signal generation entirely)
- FR-3.4: When `_automation_enabled = False`, CONTINUE to publish `ExitSignalEvent` for existing positions
- FR-3.5: Log at WARNING level when entry signals are suppressed due to disabled automation
- FR-3.6: Continue normal indicator calculation and strategy evaluation (only suppress signal publication)

**Implementation Note**: StrategyEvaluationService already evaluates strategies - we only add a gate before publishing entry signals.

---

### FR-4: Trade Execution Service Integration
**Description**: The TradeExecutionService must respect the automation state when executing trades and managing positions.

**Requirements**:
- FR-4.1: TradeExecutionService must subscribe to `AutomationStateChangedEvent`
- FR-4.2: Maintain an internal `_automation_enabled` flag initialized from `AutomationStateManager` on startup
- FR-4.3: When `_automation_enabled = False`, reject all incoming `EntrySignalEvent` without executing orders
- FR-4.4: When `_automation_enabled = False`, STOP automated position management:
  - Do NOT move stop-loss to breakeven
  - Do NOT execute trailing stop adjustments
  - Do NOT execute partial take-profit exits from multi-target strategies
  - Do NOT execute automated exit signals

- FR-4.5: When `_automation_enabled = False`, PRESERVE existing stop-loss and take-profit orders:
  - Do NOT cancel existing SL/TP orders placed by the broker
  - Do NOT modify existing SL/TP levels
  - Broker-side SL/TP will still execute automatically (this is desired behavior)

- FR-4.6: Log at WARNING level when entry signals or automated management actions are suppressed
- FR-4.7: Publish `OrderRejectedEvent` when entry signals are rejected due to disabled automation, with reason "Automated trading disabled"

**Clarification**: The broker (MT5) will still execute stop-loss and take-profit orders that were already placed. This is a safety feature - we want positions to be protected even when automation is off.

---

### FR-5: Orchestrator Integration
**Description**: The TradingOrchestrator must initialize and manage the AutomationStateManager.

**Requirements**:
- FR-5.1: Create `AutomationStateManager` during orchestrator initialization
- FR-5.2: Register `AutomationStateManager` with the EventBus
- FR-5.3: Initialize the automation state before starting any trading services
- FR-5.4: Include automation state in the orchestrator's health check response
- FR-5.5: Include automation state in the orchestrator's metrics output
- FR-5.6: On orchestrator shutdown, ensure the current state is persisted to disk

**Metrics Format**:
```python
{
  "orchestrator": {
    "automation_enabled": true,
    "automation_last_changed": "2025-11-17T10:30:00Z",
    # ... existing metrics
  }
}
```

---

### FR-6: File-Based Toggle Interface (Temporary Solution)
**Description**: Until the API is built (Phase 2), provide a simple file-based mechanism to toggle automation.

**Requirements**:
- FR-6.1: Create a file watcher that monitors `config/toggle_automation.txt`
- FR-6.2: File format: Single line containing "ENABLE", "DISABLE", or "QUERY"
- FR-6.3: When file is modified, read the command and publish `ToggleAutomationEvent`
- FR-6.4: After processing, append the result and timestamp to `config/automation_log.txt`
- FR-6.5: The watcher must poll the file every 5 seconds
- FR-6.6: Log any file read errors at ERROR level

**File Locations**:
- Input: `{CONF_FOLDER_PATH}/toggle_automation.txt`
- Log: `{CONF_FOLDER_PATH}/automation_log.txt`

**Example Workflow**:
```bash
# Trader disables automation
echo "DISABLE" > config/toggle_automation.txt

# System processes and logs
# automation_log.txt appends:
# 2025-11-17 10:30:15 - DISABLE - Success - Automation disabled by user
```

**Note**: This is a temporary interface. Phase 2 will replace this with a proper REST API.

---

### FR-7: Logging and Observability
**Description**: All automation state changes and related actions must be logged for audit and debugging.

**Requirements**:
- FR-7.1: Log automation state changes at INFO level with format:
  ```
  [AutomationStateManager] Automation {ENABLED|DISABLED} - Reason: {reason} - By: {requested_by}
  ```

- FR-7.2: Log suppressed entry signals at WARNING level:
  ```
  [StrategyEvaluationService] Entry signal suppressed - Automation disabled - Strategy: {name} - Symbol: {symbol}
  ```

- FR-7.3: Log suppressed trade executions at WARNING level:
  ```
  [TradeExecutionService] Trade execution rejected - Automation disabled - Signal: {signal_id}
  ```

- FR-7.4: Log suppressed position management actions at INFO level:
  ```
  [TradeExecutionService] Automated position management skipped - Automation disabled - Position: {position_id}
  ```

- FR-7.5: Include automation state in all orchestrator health check logs
- FR-7.6: Include state change count in daily summary metrics

---

### FR-8: Configuration Schema
**Description**: Define environment variables and configuration files for automation control.

**Requirements**:
- FR-8.1: Add new environment variable `AUTOMATION_ENABLED` (default: `true`)
- FR-8.2: Add new environment variable `AUTOMATION_STATE_FILE` (default: `{CONF_FOLDER_PATH}/automation_state.json`)
- FR-8.3: Add new environment variable `AUTOMATION_TOGGLE_FILE` (default: `{CONF_FOLDER_PATH}/toggle_automation.txt`)
- FR-8.4: Update `.env.broker` template with these variables and documentation
- FR-8.5: Validate boolean values (true/false, 1/0, yes/no) for `AUTOMATION_ENABLED`

**Example `.env.broker` additions**:
```bash
# ============================================================================
# AUTOMATION CONTROL
# ============================================================================
# Enable/disable automated trading on startup (true/false)
AUTOMATION_ENABLED=true

# Path to automation state persistence file
AUTOMATION_STATE_FILE=/app/config/automation_state.json

# Path to file-based toggle interface (temporary, until API is available)
AUTOMATION_TOGGLE_FILE=/app/config/toggle_automation.txt
```

---

## 5. Non-Goals (Out of Scope)

### Explicitly Out of Scope for Phase 1

1. **REST API Implementation**: Phase 1 uses file-based toggle only. REST API is Phase 2.

2. **Manual Trade Execution**: Phase 1 only controls automated trading. Manual order placement via API is Phase 2.

3. **Indicator Configuration API**: Phase 1 doesn't expose indicator values or configuration. This is Phase 2.

4. **Risk Manager Manual Override**: Phase 1 doesn't allow bypassing risk rules. All trades (if automation re-enabled) still respect risk limits. Phase 2 will add manual risk configuration.

5. **Per-Symbol Automation Control**: Phase 1 toggles ALL symbols at once. Per-symbol control is a future enhancement.

6. **Per-Strategy Automation Control**: Phase 1 toggles ALL strategies at once. Per-strategy control is a future enhancement.

7. **Scheduled Automation Toggles**: Phase 1 doesn't support time-based automation (e.g., "disable at 9:30 AM"). This could be Phase 3.

8. **Partial Automation Modes**: Phase 1 only supports full enable/disable. "Entry-only mode" or "exit-only mode" is out of scope.

9. **UI/Dashboard**: Phase 1 has no graphical interface. File-based and logs only.

10. **Mobile Notifications**: Phase 1 doesn't send alerts when automation state changes. Future enhancement.

11. **Multi-User Access Control**: Phase 1 assumes single trader. User authentication/authorization is Phase 2+.

12. **Automation History/Analytics**: Phase 1 logs state changes but doesn't provide analytics on automation uptime, toggle frequency, etc.

---

## 6. Technical Considerations

### Architecture Integration

**Event-Driven Design**:
- The toggle mechanism uses the existing EventBus, maintaining architectural consistency
- No direct coupling between components - all communication via events
- Easy to extend in Phase 2 (API can simply publish `ToggleAutomationEvent`)

**Service Startup Order**:
```
1. EventBus initialization
2. AutomationStateManager initialization (loads state from file)
3. DataFetchingService, IndicatorCalculationService (no changes needed)
4. StrategyEvaluationService (subscribes to AutomationStateChangedEvent)
5. TradeExecutionService (subscribes to AutomationStateChangedEvent)
6. FileWatcher for toggle_automation.txt (temporary interface)
```

### File System Requirements

**Required Files**:
- `{CONF_FOLDER_PATH}/automation_state.json` - Persistent state storage
- `{CONF_FOLDER_PATH}/toggle_automation.txt` - Temporary input file for toggles
- `{CONF_FOLDER_PATH}/automation_log.txt` - Human-readable audit log

**File Permissions**:
- Application must have read/write access to configuration folder
- Files must be created automatically if they don't exist
- Use file locking to prevent race conditions (especially in multi-symbol mode)

### Thread Safety

**Concurrent Access**:
- AutomationStateManager must use threading locks when updating state
- File writes must be atomic (write to temp file, then rename)
- EventBus already handles concurrent event publishing safely

**State Consistency**:
- All services must receive `AutomationStateChangedEvent` before processing new trading events
- Use EventBus synchronous delivery for state change events (if supported)

### Error Handling

**State File Corruption**:
- If `automation_state.json` is corrupted, log ERROR and fall back to environment variable default
- Create a backup of the state file before each write
- Maximum 5 backup files, rotate oldest out

**File Watcher Failures**:
- If `toggle_automation.txt` can't be read, log ERROR but don't crash
- Retry file read up to 3 times with 1-second delay
- Continue normal operations even if file watcher fails

**Event Delivery Failures**:
- If `AutomationStateChangedEvent` fails to publish, log CRITICAL error
- Revert state change and retry once
- If retry fails, require application restart (fail-safe mode)

### Performance Considerations

**Minimal Overhead**:
- State check is a simple boolean flag lookup (negligible performance impact)
- File I/O only occurs on state changes (rare), not on every trading loop
- File watcher polls every 5 seconds (low impact)

**No Impact on Indicator Calculation**:
- Indicators continue to calculate even when automation is disabled
- This ensures smooth re-enablement without waiting for indicator warmup

### Docker/Multi-Broker Support

**Per-Broker State**:
- Each broker container has its own `automation_state.json` file
- Broker A can be automated while Broker B is manual
- Environment variables can set different defaults per broker

**Volume Mounting**:
- Ensure `config/` folder is mounted as a persistent volume
- State must survive container restarts

### Migration Path

**Backwards Compatibility**:
- Existing deployments without automation files will default to ENABLED (current behavior)
- No breaking changes to existing services or configuration

**Phase 2 Transition**:
- File-based toggle interface can coexist with REST API during transition
- Eventually deprecate file watcher once API is stable

---

## 7. Design Considerations

### Option A: Pause Services vs. Gate Signals (CHOSEN)
**Decision**: Gate signals at the service level rather than pausing entire services.

**Rationale**:
- Services continue running and calculating indicators (needed for quick re-enablement)
- Simpler state management (no service stop/start complexity)
- Maintains system health checks and metrics during disabled state
- Easier to debug (all services still logging and operational)

**Alternative Rejected**: Stopping StrategyEvaluationService and TradeExecutionService entirely would create complex startup/shutdown logic and delay re-enablement.

---

### Option B: Single Global State vs. Per-Symbol State
**Decision**: Single global automation state for all symbols (Phase 1).

**Rationale**:
- Simpler implementation and user mental model
- Most use cases involve stopping ALL trading (e.g., major news events)
- Per-symbol control can be added in Phase 2 if needed

**Future Enhancement**: Add per-symbol state in Phase 2 if user feedback demands it.

---

### Option C: File-Based vs. Signal-Based Toggle
**Decision**: Use file-based interface for Phase 1, replace with API in Phase 2.

**Rationale**:
- File-based is simple to implement and test
- No need to build full REST API infrastructure for Phase 1
- Traders can easily script file writes (bash, Python, etc.)
- Provides immediate value while API is being designed

**Note**: File watcher is explicitly temporary and will be removed in Phase 2.

---

### Option D: Stop-Loss/Take-Profit Behavior When Disabled
**Decision**: Preserve existing SL/TP orders; do NOT cancel or modify them.

**Rationale**:
- Safety-first approach protects traders from catastrophic losses
- Broker-side SL/TP execution is independent of our application state
- Traders expect protection to remain active even when they pause automation
- Aligns with user requirement: "keep stop-loss/take-profit active"

**Alternative Rejected**: Canceling SL/TP would be extremely dangerous and violates risk management principles.

---

## 8. Success Metrics

### Functional Metrics

**FM-1: Toggle Response Time**
- Metric: Time from file write to state change event published
- Target: < 6 seconds (one file watcher poll cycle)
- Measurement: Log timestamps

**FM-2: Signal Suppression Accuracy**
- Metric: Zero entry signals published when automation disabled
- Target: 100% suppression accuracy
- Measurement: Audit logs for any `EntrySignalEvent` when state = DISABLED

**FM-3: State Persistence Reliability**
- Metric: Automation state matches expected state after restart
- Target: 100% persistence across restarts
- Measurement: Integration test with restart cycles

**FM-4: SL/TP Preservation**
- Metric: Zero SL/TP cancellations when automation disabled
- Target: 100% preservation
- Measurement: Broker API logs

### Operational Metrics

**OM-1: Toggle Frequency**
- Metric: Number of automation toggles per day
- Target: N/A (baseline measurement for Phase 2 API design)
- Measurement: Count of `AutomationStateChangedEvent`

**OM-2: Uptime by Automation State**
- Metric: Percentage of time in ENABLED vs. DISABLED state
- Target: N/A (informational only)
- Measurement: Time-weighted state tracking

**OM-3: Error Rate**
- Metric: File I/O errors, event delivery failures
- Target: < 0.1% of toggle operations
- Measurement: Error logs

### User Acceptance Criteria

**UAC-1**: Trader can disable automation by writing "DISABLE" to toggle file, and system stops opening new positions within 10 seconds.

**UAC-2**: Trader can re-enable automation by writing "ENABLE" to toggle file, and system resumes normal trading within 10 seconds.

**UAC-3**: After application restart, automation state matches the state before shutdown (tested with both ENABLED and DISABLED states).

**UAC-4**: When automation is disabled, existing positions retain their stop-loss and take-profit orders (verified via broker API).

**UAC-5**: All automation state changes are logged with timestamps and reasons (100% coverage in audit logs).

---

## 9. Open Questions

### Questions Requiring PM/Stakeholder Input

**OQ-1: File Watcher Polling Interval**
- Question: Is 5-second polling acceptable, or do we need sub-second response times?
- Impact: Faster polling = higher CPU usage; slower polling = delayed response
- Recommendation: Start with 5 seconds, make configurable via environment variable

**OQ-2: Default State on First Startup**
- Question: Should the system default to ENABLED or DISABLED when no state file exists?
- Impact: Affects safety vs. convenience tradeoff
- Recommendation: Default to ENABLED (current behavior), require explicit disable

**OQ-3: Behavior During Network/Broker Disconnection**
- Question: Should automation auto-disable if broker connection is lost?
- Impact: Could prevent trades during temporary network blips
- Recommendation: Out of scope for Phase 1; existing connection error handling is sufficient

**OQ-4: State Change Confirmation**
- Question: Should the system require confirmation before enabling automation (two-step process)?
- Impact: Adds safety but increases friction
- Recommendation: Not needed for Phase 1; single-step toggle is sufficient

**OQ-5: Partial Position Management**
- Question: When automation is disabled, should trailing stops CONTINUE to trail, or FREEZE at current levels?
- Current Decision: FREEZE (stop all automated management)
- Needs Validation: Confirm with traders this matches their mental model

### Questions for Technical Team

**TQ-1: EventBus Synchronous Delivery**
- Question: Does EventBus support synchronous event delivery to guarantee order?
- Impact: Ensures services receive state change before processing next trading event
- Action: Review EventBus implementation, add synchronous mode if needed

**TQ-2: File Locking Strategy**
- Question: What file locking mechanism works across Docker containers and Windows/Linux?
- Impact: Prevents race conditions in multi-container setups
- Action: Research cross-platform file locking libraries (e.g., `portalocker`)

**TQ-3: State File Backup Rotation**
- Question: Should we use time-based or count-based backup rotation?
- Recommendation: Count-based (keep last 5 versions), simpler to implement

**TQ-4: Multi-Symbol Orchestrator Compatibility**
- Question: Does MultiSymbolTradingOrchestrator need separate automation state per symbol, or shared state?
- Current Decision: Shared state across all symbols
- Action: Verify this works with existing MultiSymbolTradingOrchestrator implementation

---

## 10. Implementation Notes for Junior Developers

### Step-by-Step Implementation Guide

**Step 1: Create AutomationStateManager Component**
- File: `app/infrastructure/automation_state_manager.py`
- Responsibilities:
  - Load state from JSON file on initialization
  - Subscribe to `ToggleAutomationEvent` via EventBus
  - Update state and publish `AutomationStateChangedEvent`
  - Persist state to JSON file on every change
- Dependencies: EventBus, file system access
- Testing: Unit tests for state load/save, event handling

**Step 2: Define New Event Types**
- File: `app/infrastructure/events.py` (or create new file)
- Define: `ToggleAutomationEvent`, `AutomationStateChangedEvent`
- Use `@dataclass(frozen=True, kw_only=True)` pattern matching existing events
- Testing: Validate event immutability and serialization

**Step 3: Update StrategyEvaluationService**
- File: `app/services/strategy_evaluation.py`
- Changes:
  - Add `_automation_enabled` instance variable
  - Subscribe to `AutomationStateChangedEvent` in `start()` method
  - Add gate before publishing `EntrySignalEvent`
  - Add logging for suppressed signals
- Testing: Unit tests with mocked EventBus, verify signal suppression

**Step 4: Update TradeExecutionService**
- File: `app/services/trade_execution.py`
- Changes:
  - Add `_automation_enabled` instance variable
  - Subscribe to `AutomationStateChangedEvent` in `start()` method
  - Add gate for entry signal execution
  - Add gate for automated position management (trailing stops, partial exits)
  - Preserve existing SL/TP orders (no cancellation logic)
  - Publish `OrderRejectedEvent` when rejecting due to disabled automation
- Testing: Unit tests with mocked broker client, verify execution blocking

**Step 5: Update TradingOrchestrator**
- File: `app/infrastructure/orchestrator.py`
- Changes:
  - Instantiate `AutomationStateManager` in `__init__`
  - Initialize automation state before starting services
  - Add automation state to `get_metrics()` output
  - Add automation state to health check
- Testing: Integration test with full orchestrator startup

**Step 6: Create File Watcher**
- File: `app/infrastructure/automation_file_watcher.py`
- Responsibilities:
  - Poll `toggle_automation.txt` every 5 seconds
  - Parse command (ENABLE/DISABLE/QUERY)
  - Publish `ToggleAutomationEvent` to EventBus
  - Append result to `automation_log.txt`
- Dependencies: File system access, EventBus
- Testing: Unit tests with temp files, verify polling and parsing

**Step 7: Update Configuration**
- Files: `.env.broker` template, `app/infrastructure/config.py`
- Add environment variables: `AUTOMATION_ENABLED`, `AUTOMATION_STATE_FILE`, `AUTOMATION_TOGGLE_FILE`
- Add validation for boolean parsing
- Update documentation in `.env.broker` comments

**Step 8: Integration Testing**
- Create end-to-end tests:
  - Test toggle via file write
  - Test state persistence across restarts
  - Test signal suppression when disabled
  - Test SL/TP preservation
  - Test metrics reporting
- Run in Docker environment to verify volume mounting

**Step 9: Documentation**
- Update `README.md` with automation toggle instructions
- Add troubleshooting guide for common issues
- Document file formats and locations
- Add examples of scripting toggle operations

**Step 10: Deployment**
- Update Docker Compose files to mount config folder as persistent volume
- Add automation state file to `.gitignore`
- Deploy to staging environment for user acceptance testing

---

### Code Structure Reference

```
app/
├── infrastructure/
│   ├── automation_state_manager.py       # NEW - State management
│   ├── automation_file_watcher.py        # NEW - Temporary file interface
│   ├── events.py                         # UPDATED - Add new event types
│   ├── orchestrator.py                   # UPDATED - Initialize automation manager
│   └── config.py                         # UPDATED - Add env vars
├── services/
│   ├── strategy_evaluation.py            # UPDATED - Gate entry signals
│   └── trade_execution.py                # UPDATED - Gate trade execution
└── main_multi_symbol.py                  # UPDATED - Wire up file watcher

configs/
└── {broker}/
    ├── .env.broker                       # UPDATED - Add automation env vars
    ├── automation_state.json             # NEW - Persistent state
    ├── toggle_automation.txt             # NEW - Input file
    └── automation_log.txt                # NEW - Audit log
```

---

### Testing Checklist

**Unit Tests**:
- [ ] AutomationStateManager: state load, save, update, event handling
- [ ] ToggleAutomationEvent: validation, serialization
- [ ] AutomationStateChangedEvent: validation, serialization
- [ ] StrategyEvaluationService: signal gating logic
- [ ] TradeExecutionService: execution gating logic
- [ ] FileWatcher: file parsing, error handling

**Integration Tests**:
- [ ] Full orchestrator startup with automation manager
- [ ] Event flow: file write → state change → signal suppression
- [ ] State persistence across application restart
- [ ] Multi-symbol orchestrator compatibility
- [ ] Docker volume mounting

**User Acceptance Tests**:
- [ ] UAC-1: Disable automation via file, verify no new positions
- [ ] UAC-2: Enable automation via file, verify trading resumes
- [ ] UAC-3: Restart application, verify state persists
- [ ] UAC-4: Verify SL/TP orders remain active when disabled
- [ ] UAC-5: Verify all state changes logged

**Performance Tests**:
- [ ] Toggle response time < 6 seconds
- [ ] No impact on indicator calculation performance
- [ ] File watcher CPU usage < 1%

---

## 11. Dependencies

### Internal Dependencies
- EventBus (existing) - Required for event-driven toggle
- TradingOrchestrator (existing) - Manages automation state manager
- StrategyEvaluationService (existing) - Modified to gate signals
- TradeExecutionService (existing) - Modified to gate execution
- Configuration system (existing) - Extended with new env vars

### External Dependencies
- File system with read/write access to config folder
- Python `threading` module for thread-safe state updates
- Python `watchdog` library (optional, for more efficient file watching than polling)
- Python `portalocker` library (optional, for cross-platform file locking)

### Phase 2 Dependencies (Not Required for Phase 1)
- REST API framework (FastAPI, Flask, etc.)
- Authentication/authorization system
- API documentation (Swagger/OpenAPI)

---

## 12. Risks and Mitigations

### Risk 1: State File Corruption
**Likelihood**: Low
**Impact**: Medium (automation state lost, falls back to default)
**Mitigation**:
- Implement backup rotation (keep last 5 versions)
- Use atomic file writes (write to temp, then rename)
- Add file integrity checks (JSON schema validation)

### Risk 2: Race Condition in Multi-Symbol Mode
**Likelihood**: Medium
**Impact**: High (inconsistent automation state across symbols)
**Mitigation**:
- Use thread-safe state manager with locks
- Use file locking for state file writes
- Test extensively in multi-symbol environment

### Risk 3: Delayed Toggle Response (> 6 seconds)
**Likelihood**: Low
**Impact**: Low (minor user frustration)
**Mitigation**:
- Make polling interval configurable
- Consider `watchdog` library for event-driven file watching
- Document expected response time clearly

### Risk 4: File Watcher Crashes Entire Application
**Likelihood**: Low
**Impact**: High (full system outage)
**Mitigation**:
- Isolate file watcher in separate thread with exception handling
- Continue operation even if file watcher fails
- Log errors but don't propagate to main orchestrator

### Risk 5: User Confusion About SL/TP Behavior
**Likelihood**: Medium
**Impact**: Medium (unexpected position exits while automation disabled)
**Mitigation**:
- Document SL/TP preservation clearly in README
- Add explicit log message when automation disabled: "Note: Existing SL/TP orders remain active"
- Consider adding this info to automation_log.txt output

### Risk 6: Incompatibility with Future API (Phase 2)
**Likelihood**: Low
**Impact**: Medium (rework required in Phase 2)
**Mitigation**:
- Design event structure to be API-compatible (already done)
- Use file watcher as temporary interface only (clearly documented)
- Plan for file watcher deprecation in Phase 2

---

## 13. Future Enhancements (Post-Phase 1)

### Phase 2: Manual Trading API
- RESTful API for all operations (replace file-based toggle)
- Endpoints for position management, indicator monitoring, risk configuration
- Real-time WebSocket updates for state changes
- Authentication and authorization

### Phase 3: Advanced Automation Control
- Per-symbol automation toggle
- Per-strategy automation toggle
- Scheduled automation (time-based enable/disable)
- Conditional automation (e.g., "disable if daily loss > $500")

### Phase 4: Enhanced Safety Features
- Confirmation prompts for enabling automation
- Gradual re-enablement (start with reduced position sizes)
- Automation "safe mode" (reduced risk parameters)
- Emergency stop with one-click position liquidation

### Phase 5: Analytics and Reporting
- Automation uptime tracking
- Toggle frequency analysis
- Performance comparison (automated vs. manual periods)
- Notification system for state changes (email, Telegram, etc.)

---

## Appendix A: Example Usage Scenarios

### Scenario 1: Disable Before News Event
```bash
# 5 minutes before NFP announcement
echo "DISABLE" > /app/config/toggle_automation.txt

# Wait for event to pass (30 minutes)

# Re-enable after volatility settles
echo "ENABLE" > /app/config/toggle_automation.txt
```

**Expected Behavior**:
- Within 6 seconds, system stops evaluating entry signals
- Existing positions remain protected by SL/TP
- Indicators continue calculating (ready for quick restart)
- After ENABLE, system resumes normal trading immediately

---

### Scenario 2: Manual Position Management
```bash
# Disable automation to manage positions manually
echo "DISABLE" > /app/config/toggle_automation.txt

# Trader manually adjusts SL/TP via MT5 platform
# Trader manually closes positions based on price action

# Re-enable automation once manual management complete
echo "ENABLE" > /app/config/toggle_automation.txt
```

**Expected Behavior**:
- No new automated positions opened
- No automated trailing stops or partial exits
- Trader has full manual control via MT5 platform
- Automation resumes without conflicts

---

### Scenario 3: Scripted Toggle
```python
# Python script for automated news-based toggling
import datetime
import pytz

def disable_before_news(news_time, buffer_minutes=5):
    disable_time = news_time - datetime.timedelta(minutes=buffer_minutes)
    enable_time = news_time + datetime.timedelta(minutes=30)

    # Schedule disable
    if datetime.datetime.now(pytz.UTC) >= disable_time:
        with open('/app/config/toggle_automation.txt', 'w') as f:
            f.write('DISABLE')
        print(f"Automation disabled at {datetime.datetime.now()}")

    # Schedule re-enable
    time.sleep((enable_time - datetime.datetime.now(pytz.UTC)).total_seconds())
    with open('/app/config/toggle_automation.txt', 'w') as f:
        f.write('ENABLE')
    print(f"Automation re-enabled at {datetime.datetime.now()}")

# Disable 5 min before NFP, enable 30 min after
nfp_time = datetime.datetime(2025, 11, 17, 13, 30, tzinfo=pytz.UTC)
disable_before_news(nfp_time)
```

---

## Appendix B: Configuration Examples

### Example 1: Conservative Broker (Default Disabled)
```bash
# .env.broker for broker-conservative
AUTOMATION_ENABLED=false  # Start disabled, require manual enable
SYMBOLS=EURUSD
RISK_PER_GROUP=500
DAILY_LOSS_LIMIT=1000
```

### Example 2: Aggressive Broker (Always Enabled)
```bash
# .env.broker for broker-aggressive
AUTOMATION_ENABLED=true  # Always start enabled
SYMBOLS=XAUUSD,BTCUSD,EURUSD
RISK_PER_GROUP=2000
DAILY_LOSS_LIMIT=5000
```

### Example 3: Multi-Symbol with Shared State
```bash
# .env.broker for broker-multi
AUTOMATION_ENABLED=true
SYMBOLS=XAUUSD,BTCUSD,EURUSD,GBPUSD
# Single automation_state.json controls all symbols
```

---

## Appendix C: Troubleshooting Guide

### Problem: State Changes Not Persisting
**Symptoms**: Automation resets to default after restart
**Diagnosis**:
1. Check if `automation_state.json` exists in config folder
2. Check file permissions (read/write access)
3. Check Docker volume mounting (config folder must be persistent)

**Solution**:
```bash
# Verify file exists
ls -la /app/config/automation_state.json

# Check permissions
chmod 666 /app/config/automation_state.json

# Check Docker volume
docker inspect <container_id> | grep Mounts
```

---

### Problem: Toggle File Not Responding
**Symptoms**: Writing to toggle_automation.txt has no effect
**Diagnosis**:
1. Check if file watcher is running (search logs for "FileWatcher")
2. Check file path matches `AUTOMATION_TOGGLE_FILE` env var
3. Check file format (must be exactly "ENABLE" or "DISABLE")

**Solution**:
```bash
# Verify file path
echo $AUTOMATION_TOGGLE_FILE

# Write command correctly (uppercase, no extra spaces)
echo "DISABLE" > /app/config/toggle_automation.txt

# Check logs
tail -f /app/logs/application.log | grep -i automation
```

---

### Problem: New Positions Still Opening When Disabled
**Symptoms**: Trades execute despite automation being disabled
**Diagnosis**:
1. Check automation state in logs
2. Check if `AutomationStateChangedEvent` was published
3. Check if StrategyEvaluationService received the event

**Solution**:
```bash
# Check current state
cat /app/config/automation_state.json

# Check recent state changes
cat /app/config/automation_log.txt

# Verify event delivery in logs
grep "AutomationStateChangedEvent" /app/logs/application.log
```

---

### Problem: SL/TP Orders Cancelled When Disabled
**Symptoms**: Stop-loss/take-profit removed after disabling automation
**This Should Never Happen**: File a bug report immediately
**Workaround**: Re-enable automation to restore automated management

---

## Document Revision History

| Version | Date       | Changes                          | Author |
|---------|------------|----------------------------------|--------|
| 1.0     | 2025-11-17 | Initial PRD created              | PRD Generator |

---

**END OF DOCUMENT**
