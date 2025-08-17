# Data Package Tests

This directory contains comprehensive tests for the data package, which handles Data Transfer Objects (DTOs) and data structures for the trading system.

## Test Structure

### Unit Tests (`tests/data/unit/`)

1. **test_dtos.py** (34 tests)
   - Tests all DTO classes: `SignalResult`, `StrategyEvaluationResult`, `TPLevel`, `TakeProfitResult`, `StopLossResult`, `EntryDecision`, `ExitDecision`, `Trades`
   - Validates initialization, equality, and dataclass conversion
   - Tests nested dataclass relationships
   - Verifies literal type constraints

2. **test_validation_serialization.py** (18 tests)
   - Data validation tests for required fields and logical constraints
   - JSON serialization/deserialization with datetime handling
   - Deep copy functionality
   - Data integrity checks (stop loss vs entry price logic)
   - Multi-target take profit validation

### Integration Tests (`tests/data/integration/`)

1. **test_data_flow.py** (8 tests)
   - End-to-end data flow scenarios
   - Signal → Strategy → Entry Decision workflows
   - Multi-symbol, multi-strategy processing
   - Data transformation pipelines
   - Error handling and data aggregation
   - Performance with large datasets

## Running Tests

### Quick Commands

```bash
# Run all tests
python tests/data/run_tests.py

# Run specific test types
python tests/data/run_tests.py --mode unit
python tests/data/run_tests.py --mode integration
python tests/data/run_tests.py --mode validation
python tests/data/run_tests.py --mode dto

# Run with coverage
python tests/data/run_tests.py --mode coverage

# Run specific test
python tests/data/run_tests.py --test tests/data/unit/test_dtos.py::TestEntryDecision

# Quick run (minimal output)
python tests/data/run_tests.py --mode quick

# Verbose output
python tests/data/run_tests.py --mode verbose
```

### Test Runner Features

- **Coverage reporting**: Generates HTML coverage reports
- **Performance testing**: Tests with large datasets
- **Parallel execution**: Runs tests in parallel (if pytest-xdist installed)
- **Profiling**: Performance profiling (if pytest-profiling installed)
- **Flexible filtering**: Run specific test categories or individual tests

## Test Coverage

The tests cover:

- ✅ **DTO Initialization**: All required and optional fields
- ✅ **Type Safety**: Literal types and field validation
- ✅ **Serialization**: JSON encoding/decoding with datetime support
- ✅ **Data Integrity**: Logical consistency checks
- ✅ **Nested Structures**: Complex nested dataclass relationships
- ✅ **Error Handling**: Missing fields and invalid data
- ✅ **Performance**: Large dataset processing
- ✅ **Integration Flows**: Complete data transformation pipelines

## Key Test Fixtures

Located in `conftest.py`:

- **Sample DTOs**: Pre-configured entry/exit decisions, take profits, stop losses
- **Data Scenarios**: Market scenarios, symbol configurations
- **Validation Utilities**: Data integrity checkers
- **Performance Data**: Large datasets for load testing
- **JSON Utilities**: Serialization helpers with datetime support

## Data Validation Tests

The tests validate:

1. **Trading Logic**:
   - Long positions: stop loss below entry, take profit above entry
   - Short positions: stop loss above entry, take profit below entry
   - Multi-target percentages sum to 100%

2. **Required Fields**:
   - All DTOs have required fields properly enforced
   - Nested objects are properly validated

3. **Data Consistency**:
   - Entry/exit decisions match on symbol, strategy, magic number
   - Time ordering (exit after entry)
   - Position size positivity

## Common Test Patterns

```python
# Testing DTO initialization
def test_entry_decision_creation():
    entry = EntryDecision(
        symbol='XAUUSD',
        strategy_name='test',
        magic=12345,
        direction='long',
        entry_signals='BUY',
        entry_price=3000.0,
        position_size=1.0,
        stop_loss=StopLossResult(type='fixed', level=2995.0),
        take_profit=TakeProfitResult(type='fixed', level=3010.0),
        decision_time=datetime.now()
    )
    assert entry.symbol == 'XAUUSD'

# Testing serialization
def test_json_roundtrip():
    data = asdict(entry_decision)
    json_str = json.dumps(data, default=datetime_handler)
    loaded = json.loads(json_str)
    # Reconstruct with type conversion...

# Testing data flow
def test_signal_to_entry_flow():
    signal = SignalResult(long=True, short=False)
    strategy = StrategyEvaluationResult(
        strategy_name="test",
        entry=signal,
        exit=SignalResult()
    )
    # Create entry decision based on strategy...
```

## Notes

- Tests use `pytest` framework with fixtures and parameterization
- All tests are independent and can run in any order
- Fixtures provide consistent test data across test modules
- Performance tests use large datasets to verify scalability
- Integration tests validate complete workflows end-to-end