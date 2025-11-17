# Tasks: Automated Trading Toggle (Phase 1)

## Relevant Files

### Core Infrastructure
- `app/infrastructure/automation_state_manager.py` - NEW - Manages automation state with file persistence and event publishing
- `app/infrastructure/automation_file_watcher.py` - NEW - Monitors toggle file for manual control (temporary interface)
- `app/infrastructure/events.py` - UPDATED - Add new event types for automation control
- `app/infrastructure/orchestrator.py` - UPDATED - Initialize and manage AutomationStateManager

### Services
- `app/services/strategy_evaluation.py` - UPDATED - Gate entry signals based on automation state
- `app/services/trade_execution.py` - UPDATED - Gate trade execution and position management based on automation state

### Configuration
- `configs/ftmo-swing/.env.broker` - UPDATED - Add automation-related environment variables
- `configs/broker-template/README.md` - UPDATED - Document new environment variables
- `app/infrastructure/config.py` - UPDATED - Add automation config validation

### Entry Point
- `app/main_multi_symbol.py` - UPDATED - Wire up AutomationStateManager and FileWatcher

### Tests
- `tests/infrastructure/test_automation_state_manager.py` - NEW - Unit tests for state management
- `tests/infrastructure/test_automation_file_watcher.py` - NEW - Unit tests for file watcher
- `tests/services/test_strategy_evaluation_automation.py` - NEW - Integration tests for signal gating
- `tests/services/test_trade_execution_automation.py` - NEW - Integration tests for execution gating
- `tests/integration/test_automation_toggle_e2e.py` - NEW - End-to-end automation toggle scenarios

### Documentation
- `README.md` - UPDATED - Add automation toggle usage instructions
- `docs/automation-control.md` - NEW - Detailed guide for automation control feature

### Notes

- All state changes must be logged at INFO level for audit trail
- File-based toggle is temporary (Phase 1 only) - will be replaced by API in Phase 2
- Maintain thread safety for state manager (use locks for concurrent access)
- Follow existing event-driven architecture patterns (all communication via EventBus)
- Test in both Docker and local environments to verify volume mounting

---

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:
- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

---

## Tasks

- [x] **0.0 Create feature branch**
  - [x] 0.1 Create and checkout a new branch `feature/automated-trading-toggle`
  - [x] 0.2 Verify current branch is `main` before creating feature branch
  - [x] 0.3 Push feature branch to remote for backup

- [ ] **1.0 Create core automation infrastructure**
  - [x] 1.1 Create `app/events/automation_events.py` automation event types
    - [x] 1.1.1 Define `AutomationAction` enum (ENABLE, DISABLE, QUERY)
    - [x] 1.1.2 Create `ToggleAutomationEvent` dataclass with action, reason, requested_by fields
    - [x] 1.1.3 Create `AutomationStateChangedEvent` dataclass with enabled, previous_state, reason, changed_at fields
    - [x] 1.1.4 Ensure events are frozen and immutable (use `@dataclass(frozen=True, kw_only=True)`)
    - [x] 1.1.5 Add event_id and timestamp fields (inherited from base Event class)
  - [x] 1.2 Create `app/infrastructure/automation_state_manager.py`
    - [x] 1.2.1 Define `AutomationStateManager` class with EventBus integration
    - [x] 1.2.2 Implement `__init__` method - load state from JSON file, initialize EventBus subscription
    - [x] 1.2.3 Implement `_load_state()` method - read from automation_state.json with error handling
    - [x] 1.2.4 Implement `_save_state()` method - atomic write (temp file + rename), backup rotation
    - [x] 1.2.5 Implement `_handle_toggle_event()` handler - subscribe to ToggleAutomationEvent
    - [x] 1.2.6 Implement state update logic - validate action, update state, persist to file
    - [x] 1.2.7 Implement `_publish_state_change()` method - publish AutomationStateChangedEvent
    - [x] 1.2.8 Add thread safety - use threading.Lock for state updates
    - [x] 1.2.9 Add logging - INFO for state changes, ERROR for file I/O failures
    - [x] 1.2.10 Implement backup rotation - keep last 5 state file versions
  - [x] 1.3 Add automation configuration to `app/infrastructure/config.py`
    - [x] 1.3.1 Add `AUTOMATION_ENABLED` environment variable (default: true)
    - [x] 1.3.2 Add `AUTOMATION_STATE_FILE` environment variable (default: config/automation_state.json)
    - [x] 1.3.3 Add `AUTOMATION_TOGGLE_FILE` environment variable (default: config/toggle_automation.txt)
    - [x] 1.3.4 Add Pydantic validation for boolean parsing (true/false, 1/0, yes/no)
    - [x] 1.3.5 Update SystemConfig model with automation fields
  - [x] 1.4 Update `.env.broker` template files
    - [x] 1.4.1 Add automation section to `configs/ftmo-swing/.env.broker`
    - [x] 1.4.2 Add automation section to `configs/broker-template/.env.broker`
    - [x] 1.4.3 Document each environment variable with comments
    - [x] 1.4.4 Add example values and usage notes

- [ ] **2.0 Integrate automation control with trading services**
  - [ ] 2.1 Update `app/services/strategy_evaluation.py`
    - [ ] 2.1.1 Add `_automation_enabled` instance variable (default: True)
    - [ ] 2.1.2 Subscribe to `AutomationStateChangedEvent` in `start()` method
    - [ ] 2.1.3 Implement event handler to update `_automation_enabled` flag
    - [ ] 2.1.4 Add gate before publishing `EntrySignalEvent` - check `_automation_enabled`
    - [ ] 2.1.5 Continue publishing `ExitSignalEvent` regardless of automation state
    - [ ] 2.1.6 Add WARNING logging when entry signals are suppressed
    - [ ] 2.1.7 Include automation state in service metrics
  - [ ] 2.2 Update `app/services/trade_execution.py`
    - [ ] 2.2.1 Add `_automation_enabled` instance variable (default: True)
    - [ ] 2.2.2 Subscribe to `AutomationStateChangedEvent` in `start()` method
    - [ ] 2.2.3 Implement event handler to update `_automation_enabled` flag
    - [ ] 2.2.4 Add gate for entry signal execution - reject if automation disabled
    - [ ] 2.2.5 Add gate for automated position management (trailing stops, partial exits)
    - [ ] 2.2.6 Preserve existing SL/TP orders (do NOT cancel when automation disabled)
    - [ ] 2.2.7 Publish `OrderRejectedEvent` with reason "Automated trading disabled"
    - [ ] 2.2.8 Add WARNING logging for suppressed executions
    - [ ] 2.2.9 Add INFO logging for suppressed position management actions
    - [ ] 2.2.10 Include automation state in service metrics

- [ ] **3.0 Implement file-based toggle interface**
  - [ ] 3.1 Create `app/infrastructure/automation_file_watcher.py`
    - [ ] 3.1.1 Define `AutomationFileWatcher` class with EventBus and config paths
    - [ ] 3.1.2 Implement `__init__` method - accept toggle_file path and EventBus reference
    - [ ] 3.1.3 Implement `start()` method - start polling thread (5-second interval)
    - [ ] 3.1.4 Implement `stop()` method - gracefully stop polling thread
    - [ ] 3.1.5 Implement `_poll_file()` method - read toggle file, parse command
    - [ ] 3.1.6 Parse commands: "ENABLE", "DISABLE", "QUERY" (case-insensitive, strip whitespace)
    - [ ] 3.1.7 Publish `ToggleAutomationEvent` with parsed action
    - [ ] 3.1.8 Append result to `automation_log.txt` with timestamp
    - [ ] 3.1.9 Add error handling for file read failures (retry 3 times, log ERROR)
    - [ ] 3.1.10 Add thread safety - ensure polling thread is daemon thread
    - [ ] 3.1.11 Make polling interval configurable (default 5 seconds)
  - [ ] 3.2 Create automation log file structure
    - [ ] 3.2.1 Define log entry format: "YYYY-MM-DD HH:MM:SS - ACTION - Status - Message"
    - [ ] 3.2.2 Implement log rotation (max 10MB, keep last 5 files)
    - [ ] 3.2.3 Add log sanitization (no sensitive data)

- [ ] **4.0 Update orchestrator and configuration**
  - [ ] 4.1 Update `app/infrastructure/orchestrator.py`
    - [ ] 4.1.1 Import `AutomationStateManager` and `AutomationFileWatcher`
    - [ ] 4.1.2 Instantiate `AutomationStateManager` in `__init__` before services
    - [ ] 4.1.3 Initialize automation state from file during orchestrator startup
    - [ ] 4.1.4 Register `AutomationStateManager` with EventBus
    - [ ] 4.1.5 Instantiate `AutomationFileWatcher` (if enabled via config)
    - [ ] 4.1.6 Start file watcher after all services are initialized
    - [ ] 4.1.7 Add automation state to `get_metrics()` output
    - [ ] 4.1.8 Add automation state to `health_check()` response
    - [ ] 4.1.9 Ensure state persistence on orchestrator shutdown
    - [ ] 4.1.10 Stop file watcher during orchestrator shutdown
  - [ ] 4.2 Update `app/main_multi_symbol.py`
    - [ ] 4.2.1 Verify orchestrator initialization includes automation components
    - [ ] 4.2.2 Add logging for automation initialization status
    - [ ] 4.2.3 Handle automation startup errors gracefully

- [ ] **5.0 Testing and validation**
  - [ ] 5.1 Create unit tests for `AutomationStateManager`
    - [ ] 5.1.1 Create `tests/infrastructure/test_automation_state_manager.py`
    - [ ] 5.1.2 Test state loading from file (new file, existing file, corrupted file)
    - [ ] 5.1.3 Test state saving (atomic write, backup creation, rotation)
    - [ ] 5.1.4 Test event handling (ENABLE, DISABLE, QUERY actions)
    - [ ] 5.1.5 Test state change event publishing
    - [ ] 5.1.6 Test thread safety (concurrent state updates)
    - [ ] 5.1.7 Test error handling (file I/O errors, invalid JSON)
    - [ ] 5.1.8 Test default state behavior (no file + no env var)
  - [ ] 5.2 Create unit tests for `AutomationFileWatcher`
    - [ ] 5.2.1 Create `tests/infrastructure/test_automation_file_watcher.py`
    - [ ] 5.2.2 Test file parsing (ENABLE, DISABLE, QUERY commands)
    - [ ] 5.2.3 Test case-insensitive parsing and whitespace handling
    - [ ] 5.2.4 Test event publishing after file change
    - [ ] 5.2.5 Test log file creation and appending
    - [ ] 5.2.6 Test polling interval behavior
    - [ ] 5.2.7 Test error handling (missing file, read errors, invalid commands)
    - [ ] 5.2.8 Test start/stop lifecycle
  - [ ] 5.3 Create integration tests for service automation gating
    - [ ] 5.3.1 Create `tests/services/test_strategy_evaluation_automation.py`
    - [ ] 5.3.2 Test entry signal suppression when automation disabled
    - [ ] 5.3.3 Test exit signal continuation when automation disabled
    - [ ] 5.3.4 Test signal resumption when automation re-enabled
    - [ ] 5.3.5 Create `tests/services/test_trade_execution_automation.py`
    - [ ] 5.3.6 Test trade execution rejection when automation disabled
    - [ ] 5.3.7 Test SL/TP preservation when automation disabled
    - [ ] 5.3.8 Test automated position management suppression
    - [ ] 5.3.9 Test trade execution resumption when re-enabled
  - [ ] 5.4 Create end-to-end integration tests
    - [ ] 5.4.1 Create `tests/integration/test_automation_toggle_e2e.py`
    - [ ] 5.4.2 Test UAC-1: Disable via file → verify no new positions within 10 seconds
    - [ ] 5.4.3 Test UAC-2: Enable via file → verify trading resumes within 10 seconds
    - [ ] 5.4.4 Test UAC-3: Restart application → verify state persists
    - [ ] 5.4.5 Test UAC-4: Existing positions retain SL/TP when disabled
    - [ ] 5.4.6 Test UAC-5: All state changes logged with timestamps
    - [ ] 5.4.7 Test full orchestrator startup with automation disabled
    - [ ] 5.4.8 Test full orchestrator startup with automation enabled
  - [ ] 5.5 Run existing tests to ensure no regressions
    - [ ] 5.5.1 Run all unit tests: `pytest tests/`
    - [ ] 5.5.2 Verify no breaking changes in services
    - [ ] 5.5.3 Check EventBus behavior with new events
    - [ ] 5.5.4 Verify orchestrator initialization still works

- [ ] **6.0 Documentation and deployment preparation**
  - [ ] 6.1 Update main README
    - [ ] 6.1.1 Add "Automation Control" section to README.md
    - [ ] 6.1.2 Document file-based toggle usage with examples
    - [ ] 6.1.3 Add expected behavior explanations (what happens when disabled)
    - [ ] 6.1.4 Include troubleshooting section
  - [ ] 6.2 Create detailed automation control documentation
    - [ ] 6.2.1 Create `docs/automation-control.md`
    - [ ] 6.2.2 Document all environment variables
    - [ ] 6.2.3 Provide file-based toggle examples (bash, Python scripts)
    - [ ] 6.2.4 Explain state persistence behavior
    - [ ] 6.2.5 Document SL/TP preservation when disabled
    - [ ] 6.2.6 Add FAQ section
  - [ ] 6.3 Update Docker configuration
    - [ ] 6.3.1 Verify `config/` folder is mounted as persistent volume
    - [ ] 6.3.2 Add automation_state.json to .gitignore
    - [ ] 6.3.3 Add toggle_automation.txt to .gitignore
    - [ ] 6.3.4 Add automation_log.txt to .gitignore
    - [ ] 6.3.5 Update docker-compose.yml with volume mappings
    - [ ] 6.3.6 Test Docker deployment with automation toggle
  - [ ] 6.4 Create deployment checklist
    - [ ] 6.4.1 Verify all environment variables are set
    - [ ] 6.4.2 Test state persistence across container restarts
    - [ ] 6.4.3 Verify file permissions (read/write for config folder)
    - [ ] 6.4.4 Test multi-symbol orchestrator compatibility
    - [ ] 6.4.5 Verify logging works correctly
  - [ ] 6.5 Prepare for code review and merge
    - [ ] 6.5.1 Review all code changes for consistency
    - [ ] 6.5.2 Ensure all tests pass
    - [ ] 6.5.3 Update CHANGELOG.md with Phase 1 features
    - [ ] 6.5.4 Create pull request with comprehensive description
    - [ ] 6.5.5 Link PR to Phase 1 PRD document

---

## Testing Commands

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/infrastructure/test_automation_state_manager.py

# Run integration tests only
pytest tests/integration/

# Run with coverage
pytest --cov=app tests/

# Test file-based toggle (manual)
echo "DISABLE" > config/toggle_automation.txt
# Wait 5 seconds, check logs
cat config/automation_log.txt
```

---

## Validation Checklist

Before marking Phase 1 complete:

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] User acceptance criteria (UAC-1 through UAC-5) validated
- [ ] State persists across application restarts
- [ ] SL/TP orders remain active when automation disabled
- [ ] Logging includes all state changes with timestamps
- [ ] Docker deployment works with volume mounting
- [ ] File-based toggle responds within 10 seconds
- [ ] No new positions opened when automation disabled
- [ ] Trading resumes immediately when automation re-enabled
- [ ] Documentation is complete and accurate
- [ ] Code review completed
- [ ] Pull request approved and ready to merge

---

## Notes

- **Phase 1 Focus**: This task list covers ONLY Phase 1 (Automated Trading Toggle). Phase 2 (Manual Trading API) will be a separate task list.
- **File-Based Toggle**: The file watcher is explicitly temporary and will be deprecated in Phase 2 when the REST API is implemented.
- **Thread Safety**: All state updates must use locks to prevent race conditions in multi-symbol mode.
- **Event-Driven**: All components communicate via EventBus - no direct service coupling.
- **Backwards Compatibility**: Existing deployments without automation files should default to ENABLED (current behavior).
- **Testing Priority**: Focus on integration tests to ensure services correctly respect automation state.

---

## Risk Mitigation

- **Risk**: State file corruption → **Mitigation**: Backup rotation (5 versions) + JSON validation
- **Risk**: File watcher crashes → **Mitigation**: Isolate in separate thread, log errors but continue operation
- **Risk**: Race conditions → **Mitigation**: Thread locks on state manager, file locking for writes
- **Risk**: Delayed toggle response → **Mitigation**: 5-second polling (configurable), document expected delay
- **Risk**: SL/TP accidentally cancelled → **Mitigation**: Explicit preservation logic, integration tests verify

---

**END OF TASK LIST**
