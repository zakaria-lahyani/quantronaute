# Entry Manager Tests

This directory contains comprehensive tests for the entry manager (risk manager) package.

## Test Structure

```
tests/entry_manager/
├── fixtures/              # Test fixtures and mock data
│   ├── mock_strategies.py  # Mock strategy configurations
│   └── mock_data.py       # Mock market data
├── unit/                  # Unit tests
│   ├── test_manager.py    # RiskManager tests
│   ├── test_position_sizing.py # Position sizing tests
│   ├── test_stop_loss.py  # Stop loss tests
│   └── test_take_profit.py # Take profit tests
├── integration/           # Integration tests
│   └── test_end_to_end.py # End-to-end scenarios
├── conftest.py           # Pytest configuration
├── run_tests.py          # Test runner script
└── README.md            # This file
```

## Running Tests

### Prerequisites

Install pytest and dependencies:
```bash
pip install pytest>=7.0.0 pytest-cov>=4.0.0 pytest-mock>=3.10.0
```

Or use the test runner to install automatically:
```bash
python tests/entry_manager/run_tests.py install
```

### Test Commands

#### Quick Smoke Test
```bash
python tests/entry_manager/run_tests.py smoke
```
Runs basic functionality checks to ensure the package works.

#### Unit Tests
```bash
python tests/entry_manager/run_tests.py unit
```
Runs all unit tests for individual components.

#### Integration Tests
```bash
python tests/entry_manager/run_tests.py integration
```
Runs end-to-end integration tests.

#### All Tests
```bash
python tests/entry_manager/run_tests.py all
```
Runs the complete test suite.

#### Coverage Report
```bash
python tests/entry_manager/run_tests.py coverage
```
Runs tests with coverage reporting (HTML report in `htmlcov/`).

#### Performance Tests
```bash
python tests/entry_manager/run_tests.py performance
```
Runs performance benchmarks.

#### Specific Test
```bash
python tests/entry_manager/run_tests.py specific --test-path tests/entry_manager/unit/test_manager.py::TestRiskManagerInit::test_valid_initialization
```

### Using pytest directly

```bash
# Run all tests
pytest tests/entry_manager/ -v

# Run specific test file
pytest tests/entry_manager/unit/test_manager.py -v

# Run with coverage
pytest tests/entry_manager/ --cov=app.entry_manager --cov-report=html

# Run only unit tests
pytest tests/entry_manager/unit/ -v

# Run only integration tests
pytest tests/entry_manager/integration/ -v

# Run tests matching a pattern
pytest tests/entry_manager/ -k "position_sizing" -v

# Run with specific markers
pytest tests/entry_manager/ -m "unit" -v
```

## Test Categories

### Unit Tests

- **test_manager.py**: Tests for the main RiskManager class
  - Initialization and validation
  - Entry decision calculation
  - Exit decision calculation
  - Trade management
  - Error handling

- **test_position_sizing.py**: Tests for position sizing implementations
  - FixedPositionSizer
  - PercentagePositionSizer
  - VolatilityPositionSizer
  - Factory functions

- **test_stop_loss.py**: Tests for stop loss implementations
  - FixedStopLossCalculator
  - IndicatorStopLossCalculator
  - TrailingStopLossCalculator
  - Factory functions

- **test_take_profit.py**: Tests for take profit implementations
  - FixedTakeProfitCalculator
  - MultiTargetTakeProfitCalculator
  - Factory functions

### Integration Tests

- **test_end_to_end.py**: Complete workflow tests
  - End-to-end trading scenarios
  - Complex market conditions
  - Multi-strategy management
  - Performance scenarios
  - Error handling scenarios

## Test Fixtures

### Mock Strategies (`fixtures/mock_strategies.py`)

- `create_basic_strategy()`: Simple fixed-size strategy
- `create_percentage_strategy()`: Percentage-based position sizing
- `create_volatility_strategy()`: ATR-based position sizing
- `create_trailing_stop_strategy()`: Trailing stop loss
- `create_multi_target_strategy()`: Multiple take profit targets
- `create_multiple_strategies()`: Collection of different strategies

### Mock Data (`fixtures/mock_data.py`)

- `create_market_data_simple()`: Basic OHLC data
- `create_market_data_trending()`: Trending market data
- `create_market_data_volatile()`: High volatility data
- `create_market_data_with_indicators()`: Data with technical indicators
- `create_multi_timeframe_data()`: Multiple timeframe data

## Configuration

### conftest.py

Provides shared fixtures and pytest configuration:

- Logger fixtures for testing
- Strategy fixtures
- Market data fixtures
- Test markers (unit, integration, performance, slow)
- Parametrized fixtures for comprehensive testing

### Test Markers

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Long-running tests
- `@pytest.mark.performance`: Performance-related tests

## Coverage Goals

The test suite aims for:
- **>90% code coverage** for critical components
- **>80% overall coverage** for the entry manager package
- **100% coverage** for public APIs

## Performance Testing

Performance tests verify:
- Entry decision calculation time < 100ms
- Multiple strategy handling < 1s for 10 strategies
- Memory usage remains stable
- No memory leaks in long-running scenarios

## Common Test Patterns

### Testing Calculations
```python
def test_calculation(self):
    # Arrange
    config = create_config()
    calculator = Calculator(config)
    
    # Act
    result = calculator.calculate(input_data)
    
    # Assert
    assert result.value == expected_value
    assert result.type == expected_type
```

### Testing Error Conditions
```python
def test_error_condition(self):
    calculator = Calculator(config)
    
    with pytest.raises(ValidationError) as exc_info:
        calculator.calculate(invalid_input)
    
    assert "expected error message" in str(exc_info.value)
```

### Testing with Fixtures
```python
def test_with_fixture(self, basic_strategy, simple_market_data):
    manager = RiskManager({"test": basic_strategy}, "EURUSD", 10000.0)
    
    entry = manager.calculate_entry_decision(
        strategy_name="test",
        symbol="EURUSD",
        direction="long",
        entry_price=1.1000,
        decision_time=datetime.now(),
        market_data=simple_market_data
    )
    
    assert entry is not None
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the project root is in PYTHONPATH
2. **Missing Dependencies**: Run `pip install pytest pytest-cov pytest-mock`
3. **Test Failures**: Check that all required mock data is properly structured

### Debugging Tests

```bash
# Run with detailed output
pytest tests/entry_manager/ -v -s

# Run with pdb on failure
pytest tests/entry_manager/ --pdb

# Run with coverage and show missing lines
pytest tests/entry_manager/ --cov=app.entry_manager --cov-report=term-missing
```

## Contributing

When adding new tests:

1. Follow existing naming conventions
2. Use appropriate fixtures from `conftest.py`
3. Add new mock data to `fixtures/` if needed
4. Ensure tests are properly categorized with markers
5. Update this README if adding new test categories